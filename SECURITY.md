# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub's private vulnerability reporting:
**Security tab → Report a vulnerability** on `laavanjan/face-search-app`.
Fallback contact: `security@face-search.example` *(placeholder — replace before production)*.

Do not open public issues for vulnerabilities, and do not access or keep other people's photos or data.

| Step | Target |
|---|---|
| Acknowledgement | within 3 days |
| Status updates | every 7 days |
| Fix — critical / high / medium / low | 3 / 7 / 30 / 90 days |
| Coordinated public disclosure | within 90 days, via GitHub Security Advisory (CVE requested when applicable) |

Good-faith research within scope (backend API, frontend, CI workflows) will not be pursued legally.
Reporters are credited unless they prefer otherwise.

## Supported versions

Only the latest release (see `CHANGELOG.md`) receives security fixes.

## How we manage vulnerabilities

See `governance/vulnerability-management.yaml`: Dependabot, pip-audit/npm audit, gitleaks secret scanning and an SBOM on every build (`.github/workflows/security.yml`).
