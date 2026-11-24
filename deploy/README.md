# Deploying to AWS (EC2 + GitHub Actions)

Push to `main` -> CI passes -> the **Deploy** workflow builds the backend and frontend images,
pushes them to ECR, and tells one EC2 host (over SSM, no SSH) to pull and restart the stack.
Caddy on the host serves HTTPS with a free Let's Encrypt certificate.

```
GitHub Actions --OIDC--> AWS role --> ECR (images)
                                  \-> SSM Run Command --> EC2: docker compose up
                                                              caddy -> frontend -> backend -> qdrant
```

Rough cost in us-east-1: `t3.medium` ~$30/mo + 30 GB disk ~$2.4 + Elastic IP ~$3.7 = **~$37/mo**
(plus Rekognition/S3 usage). Set a budget alert first.

Replace `<ACCOUNT_ID>`, `<REGION>` and `<INSTANCE_ID>` below with your own values. Use the same
region as your S3 bucket.

## 1. ECR repositories
ECR -> Repositories -> Create, **private**, two of them: `face-search-backend` and
`face-search-frontend`. On each, add a lifecycle rule "keep last 5 images" to avoid storage costs.

## 2. EC2 instance role
IAM -> Roles -> Create role -> AWS service **EC2**. Attach `AmazonSSMManagedInstanceCore` and
`AmazonEC2ContainerRegistryReadOnly`. Name it `face-search-ec2-role`.

## 3. Launch the instance
- AMI: Amazon Linux 2023 (x86_64), type `t3.medium`, 30 GB gp3 disk
- IAM instance profile: `face-search-ec2-role`
- Key pair: **proceed without** (you will use SSM, not SSH)
- Security group: inbound **80** and **443** from anywhere, nothing else (no port 22)
- Then EC2 -> Elastic IPs -> allocate one and **associate it with the instance**

## 4. Bootstrap the host
EC2 -> select the instance -> Connect -> **Session Manager**. Then:
```bash
sudo -i
curl -fsSL https://raw.githubusercontent.com/laavanjan/face-search-app/main/deploy/bootstrap-ec2.sh -o bootstrap-ec2.sh
bash bootstrap-ec2.sh
```
(For a private repo, paste the script contents instead.) It prints your HTTPS address, for example
`3-91-10-20.sslip.io`.

## 5. Production secrets on the host
Still in the Session Manager shell, create `/opt/face-search/backend.env`. Generate each secret
there and do not paste them into chat or GitHub:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"      # run once per API token and once for DATA_ENCRYPTION_KEY
printf '%s' 'THE-RAW-TOKEN' | sha256sum                            # the hex digest goes in API_KEYS
```
```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=face-search-app-laavanjan
API_KEYS=you:admin:sha256:<hex digest>,rita:reviewer:sha256:<hex digest>
DATA_ENCRYPTION_KEY=<generated secret>
```
Keep the raw tokens in your password manager; you sign in to the app with them. Any other settings
from `backend/.env.example` can be added too. `ENVIRONMENT=production` is set by the compose file.
Then `chmod 600 /opt/face-search/backend.env`.

## 6. GitHub OIDC role for the workflow
IAM -> Identity providers -> Add provider: type **OpenID Connect**, URL
`https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`.

IAM -> Roles -> Create role -> **Web identity** -> that provider. Edit the trust policy to:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:laavanjan/face-search-app:environment:production"
      }
    }
  }]
}
```
Name it `face-search-github-deploy` and attach this inline policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": [
        "arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/face-search-backend",
        "arn:aws:ecr:<REGION>:<ACCOUNT_ID>:repository/face-search-frontend"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:<REGION>:<ACCOUNT_ID>:instance/<INSTANCE_ID>",
        "arn:aws:ssm:<REGION>::document/AWS-RunShellScript"
      ]
    },
    { "Effect": "Allow", "Action": "ssm:GetCommandInvocation", "Resource": "*" }
  ]
}
```

## 7. GitHub settings
Repo -> Settings:
- **Environments** -> New environment `production`. Add yourself as a **required reviewer** so
  every deploy needs your approval (recommended for a face-search system).
- **Secrets and variables -> Actions -> Variables** (these are not secrets): `AWS_REGION`,
  `AWS_DEPLOY_ROLE_ARN` (the role ARN from step 6), `EC2_INSTANCE_ID`.

## 8. Deploy
Merge to `main` (the `workflow_run` trigger only fires from the default branch). Or run
Actions -> Deploy -> **Run workflow**. Open `https://<your-address>.sslip.io`.

First deploy notes:
- The first search/upload downloads ~200 MB of InsightFace weights (kept on disk afterwards).
- The app pauses indexing and search until an admin approves the configuration
  (`POST /admin/config/approve`, see `docs/governance/change-management.md`). `/health` shows
  `config_approved`.
- Certificate errors: check ports 80/443 in the security group. If Let's Encrypt rate-limits
  `sslip.io`, point your own domain at the Elastic IP and set `SITE_ADDRESS` in
  `/opt/face-search/stack.env`.

## Operations
- **Roll back:** Actions -> Deploy -> run it on an older commit's CI run, or on the host set the
  image tags in `/opt/face-search/stack.env` to an older SHA and run
  `docker compose --project-name face-search --env-file /opt/face-search/stack.env -f docker-compose.prod.yml up -d`
  from `/opt/face-search/repo`.
- **Logs:** same directory, `docker compose ... logs -f backend`.
- **Backups:** `/opt/face-search/data` holds photos (if not in S3), the governance/audit DB and the
  vector index. Take regular EBS snapshots (Data Lifecycle Manager).
- **Cost:** stop the instance when idle (you keep paying for the disk and Elastic IP), or delete
  everything when the credit runs out.
- The deploy job passes its short-lived `GITHUB_TOKEN` to the host so it can fetch the commit.
  It expires when the job ends, and it also appears in the SSM command history.
