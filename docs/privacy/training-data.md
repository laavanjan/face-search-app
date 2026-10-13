# Model provenance, training data and licences

| | |
|---|---|
| Owner | System Owner (@laavanjan) |
| Reviewed | 2026-10-14 against `insightface==0.7.3` (pinned in `backend/requirements.txt`) |
| Next review | 2027-01-14, and on any model change ([change-management.md](../governance/change-management.md)) |

**This repository does not train or fine-tune any model.** All ML components are third-party and
pretrained. Uploaded photos are application input data, not training data.

## 1. Components

| Component | What it is | Where it comes from | Used for |
|---|---|---|---|
| `insightface` Python package 0.7.3 | Inference library | PyPI, `deepinsight/insightface` | Loading/running models |
| `buffalo_l` model pack | Pretrained ONNX models, downloaded by InsightFace into `~/.insightface/models/buffalo_l` on first use (`FACE_MODEL_NAME`) | InsightFace model zoo (GitHub releases of `deepinsight/insightface`) | Detection + embedding |
| └ detection model (SCRFD, 10 GF) | Face detector | Trained by the InsightFace authors on the WIDER FACE dataset (per the model-zoo documentation) | Finding faces and 5-point keypoints |
| └ recognition model (ResNet-50 ArcFace) | 512-d face embedder | Trained by the InsightFace authors on WebFace600K, a subset of WebFace260M (per the model-zoo documentation) | Producing embeddings |
| └ age/gender, 2D/3D landmark models | Included in the pack | - | **Not loaded** (`allowed_modules=["detection","recognition"]`) |
| `onnxruntime` 1.19.2 | Runtime | PyPI (Microsoft) | Executing ONNX models (CPU provider) |
| Amazon Rekognition `DetectFaces` (optional) | Managed AWS service | AWS | Face quality score only; never identity |

Sources to verify against on each review:
- InsightFace repository and licence: https://github.com/deepinsight/insightface
- Model zoo / `buffalo_l` notes: https://github.com/deepinsight/insightface/tree/master/model_zoo and `python-package/README.md`
- AWS Service Terms (Rekognition section): https://aws.amazon.com/service-terms/

The training datasets were assembled by third parties from web images; their subjects did not consent
to this application. That is an inherited limitation, and part of why the system never claims accuracy
or fairness without its own evaluation (risk R-03).

## 2. Licences

| Item | Licence / terms (as reviewed 2026-10-14) | Effect on this project |
|---|---|---|
| InsightFace **code** | MIT | Free for academic and commercial use |
| InsightFace **pretrained models** incl. `buffalo_l`, and their training data annotations | **Non-commercial research use only**, per the InsightFace README; commercial use needs a separate licence from the InsightFace authors | This deployment is a non-commercial portfolio project. **Any commercial deployment must first obtain a commercial licence or replace `buffalo_l`** (risk R-06) |
| WIDER FACE / WebFace260M datasets | Research-use terms set by their creators | Not redistributed or used here; inherited via the weights |
| AWS Rekognition | AWS Customer Agreement + Service Terms; content may be used to improve AWS services unless the AWS Organizations AI-services opt-out is set | Opt-out required before enabling ([cross-border-transfer-assessment.md](cross-border-transfer-assessment.md)) |

Weights are downloaded at runtime and are **not** committed or redistributed (`.gitignore` excludes
`*.onnx`, `models/`, `.insightface/`).

## 3. Permitted and prohibited uses of the data

Permitted:
- Running the pretrained models for inference on photos inside an authorised, consented collection, for non-commercial use.

Prohibited:
- Commercial deployment with `buffalo_l` without a commercial licence.
- Redistributing the `buffalo_l` weights.
- Using uploaded photos or stored embeddings (`pipeline.ingest`, `vector_store.upsert`) to train, fine-tune, benchmark, or build a separate biometric dataset - unless documented consent and legal approval exist, recorded as a major change.
- Using the models for attribute inference (age, gender, ethnicity, emotion), surveillance or the other uses in [GOVERNANCE.md §3](../../GOVERNANCE.md).

If upstream terms change so the intended use is no longer permitted, replace the model and update
`FACE_MODEL_NAME` and this document together (the config gate forces an approval when you do).
