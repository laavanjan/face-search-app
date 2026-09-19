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
- [ ] Install `insightface` and `onnxruntime`
- [ ] Write a script that loads the InsightFace model (`buffalo_l`)
- [ ] Run detection on 5 sample photos, print bounding boxes
- [ ] Generate embeddings for detected faces, print vector shape (should be 512-d)
- [ ] Sanity check: same person across 2 photos -> high cosine similarity; different people -> low similarity

## Phase 2 - Optional cloud detection layer (Vision API / Rekognition)
- [ ] Create GCP or AWS account, set a budget alert
- [ ] Enable Vision API (GCP) or Rekognition (AWS)
- [ ] Write a function that calls DetectFaces and parses bounding box + quality score
- [ ] Add a filter step: discard blurry/low-quality crops before embedding

## Phase 3 - Vector storage with Qdrant
- [ ] Sign up for Qdrant Cloud free tier, get cluster URL + API key
- [ ] Create a collection (512 dimensions, cosine distance)
- [ ] Write an upsert function: embedding + image reference + quality metadata
- [ ] Manually index 10 photos, confirm vectors are stored and queryable

## Phase 4 - Backend API
- [ ] `POST /upload` - accepts a photo, runs detect -> filter -> embed -> store
- [ ] `POST /search` - accepts a reference photo, returns matching image IDs
- [ ] Handle edge cases: no face detected, multiple faces, unsupported file type
- [ ] Write a few unit tests for the detection/embedding functions

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
