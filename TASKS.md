# Face search app - project plan

A portfolio project: upload a reference photo, get back every photo containing that person. Built with open-source face recognition (InsightFace), optional cloud detection (Google Vision / Amazon Rekognition), Qdrant for vector search, FastAPI backend, Next.js frontend.

---

## Phase 0 - Repo & environment setup
- [x] Create GitHub repo, add `.gitignore` (Python + Node)
- [x] Add README stub with project description
- [x] Create Python virtual environment, install `fastapi`, `uvicorn`
- [x] Scaffold Next.js frontend (App Router, Tailwind)
- [x] Set up `requirements.txt`

## Phase 1 - Core detection + embedding pipeline (local only, no cloud yet)
- [x] Install `insightface` and `onnxruntime`
- [x] Load the InsightFace model (`buffalo_l`) lazily on first request
- [x] Detect faces + filter by score & size (`app/services/face_engine.py`)
- [x] Generate 512-d L2-normalized embeddings
- [x] Sanity-check similarity in tests (`tests/test_pipeline.py`)

## Phase 2 - Optional cloud detection layer (Rekognition)
- [x] Wire up an optional Rekognition path (`app/services/rekognition.py`)
- [x] Blend Rekognition quality score with InsightFace confidence when enabled
- [x] Fall back cleanly to InsightFace-only when AWS is blank
- [ ] Create AWS account, set a budget alert (deferred - AWS blank)

## Phase 3 - Vector storage with Qdrant
- [x] Qdrant client with in-memory fallback (`app/services/vector_store.py`)
- [x] 512-d cosine collection created on startup
- [x] Upsert with photo/face/bbox/quality payload
- [x] Search endpoint returns matches with scores
- [ ] Point at Qdrant Cloud once cluster is provisioned

## Phase 4 - Backend API
- [x] `POST /upload` - detect -> filter -> embed -> store
- [x] `POST /search` - reference photo -> cosine matches
- [x] Handles no-face / multi-face / bad content-type / oversize
- [x] Unit tests for pipeline + health

## Phase 5 - Frontend
- [ ] Upload page (drag-and-drop or file picker)
- [ ] Results gallery page showing matched photos
- [ ] Wire up API calls, loading states, error states

## Phase 6 - Deploy
- [ ] Containerize the backend (`Dockerfile`)
- [ ] Deploy backend (Cloud Run on GCP, or Lambda + Mangum on AWS)
- [ ] Deploy frontend (Firebase Hosting / Amplify / Vercel)
- [ ] Confirm budget alerts are active before going live
- [ ] Full end-to-end test in production

## Phase 7 - Portfolio polish (stretch)
- [ ] Write a proper README: architecture diagram, demo GIF, tech stack
- [ ] Add face clustering - auto-group photos by person, no reference photo needed
- [ ] Add a quality filter to search (e.g. "only sharp, front-facing photos")
- [ ] Record a short demo video
