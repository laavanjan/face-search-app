# De-identification and data minimisation

| | |
|---|---|
| Owner | Privacy & Incident Owner |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

## 1. Privacy guarantee - stated plainly

**This system provides no anonymisation guarantee.** It processes **biometric personal data**.

- Stored photos show identifiable faces.
- 512-d embeddings are linkable biometric identifiers: by design, `vector_store.search` re-identifies a person from a new photo.
- No k-anonymity, l-diversity or differential-privacy parameter applies, and none is claimed. Random UUIDs for `photo_id` / `face_id` are **pseudonymous keys**, not de-identification.

The system therefore treats all stored data as special-category personal data and relies on access
control, minimisation, human review and short retention rather than on anonymisation.

If a future feature needs a formal guarantee (e.g. aggregate statistics export), it must use an
aggregation mechanism with stated parameters - for example suppress any group below **k = 5**, or a
differentially private release with a stated total ε and δ - and be added here before release.

## 2. Methods actually applied

| Method | Type | What it does | Where |
|---|---|---|---|
| Metadata stripping | Suppression | Image is decoded and **re-encoded from pixels only**: EXIF, GPS, camera make/model/serial, ICC and text chunks are dropped before the image is stored **or sent to AWS** | `pipeline.prepare()` / `_encode_clean()` |
| Filename removal | Suppression | Client filename is never stored (it often contains names); storage key is a random 128-bit id | `pipeline.ingest()`, `vector_store` payload allowlist |
| Resolution cap | Generalisation | Images reduced to ≤ 1600 px on the long edge | `pipeline._normalize()` |
| Attribute non-inference | Minimisation | Age/gender/landmark models are not loaded | `face_engine._get_app()` (`allowed_modules`) |
| Payload allowlist | Minimisation | Qdrant stores only `photo_id, bbox, det_score, quality, review_status, indexed_at, uploaded_by, model` | `vector_store.py` docstring + `upsert()` |
| Query image lifetime | Minimisation | Search reference photo is kept only while a reviewer needs it | `review.close_case()` |
| Log redaction | Masking | Photo/face ids, filenames, emails, URLs, bearer tokens and the last IPv4 octet are masked in every log line, including uvicorn access logs and tracebacks | `app/logging_setup.py` |
| Opaque public status | Minimisation | Public appeal lookup never returns contact details | `appeals.public_view()` |

## 3. Validation

| Claim | Test | Acceptance criterion |
|---|---|---|
| EXIF removed before storage and before Rekognition | `tests/test_pipeline.py::test_metadata_stripped_and_filename_not_stored` | Stored bytes have empty EXIF and do not contain the fixture's camera make string; bytes passed to Rekognition likewise |
| Filename not stored; payload limited to allowlist | same test | No `filename` key; payload keys ⊆ allowlist |
| Deletion removes both the image and every vector | `tests/test_governance.py::test_delete_endpoint_removes_file_and_vectors` | `storage.exists` false and no Qdrant points for the photo |
| Logs do not carry identifiers | `tests/test_governance.py::test_logs_redact_personal_data` | No photo id, IP, email, filename or token in the formatted message |
| Gallery/API do not expose filenames | `GET /gallery` response schema in `routes/photos.py` | No filename field |

Test data: synthetic only ([synthetic-data.md](synthetic-data.md)). Command:

```bash
cd backend && pytest tests/test_pipeline.py tests/test_governance.py
```
