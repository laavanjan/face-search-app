"""Explainability for face matches (TRAN-03, TRAN-02).

Approach: evidence-based explanation, not feature attribution.
For every candidate the API explains *why it was proposed* with the quantities
the decision actually used - cosine similarity, the threshold in force, the
margin above it, a confidence band, the detected face box, detector and
quality scores, the model, and whether a human added or verified it - plus the
caveats that apply.

Why this fits: ArcFace embeddings are 512 opaque dimensions. Saliency or SHAP
maps over them are unstable and invite over-trust; the real decision is made
by a human comparing two faces. So the explanation gives the reviewer and the
requester the comparable evidence and calibrated score context, and says
plainly when the system is uncertain. Served at GET /review/cases/{id}/explain
(all candidates) and GET /search/cases/{id}/explain (released matches only).
"""
from __future__ import annotations

from app.config import get_settings
from app.services import vector_store

# Margin above the threshold -> band. Low-margin matches are where the model is
# least certain; the UI and API label them so people treat them with caution.
BANDS = ((0.10, "low"), (0.25, "medium"))

BAND_MEANING = {
    "low": "Barely above the threshold - the system is uncertain; a mistaken identity is plausible.",
    "medium": "Clearly above the threshold, but similar-looking people can score this high.",
    "high": "Strong similarity. Still not proof of identity.",
    "human": "Added by a human reviewer; no model score.",
}

CAVEATS = [
    "A similarity score is an estimate, not an identification.",
    "Accuracy can be lower for some ages, skin tones, poses, lighting and image quality.",
    "Low-quality, small, blurred, occluded or side-on faces make errors more likely.",
]


def confidence_band(score: float | None, threshold: float) -> str:
    if score is None:
        return "human"
    margin = score - threshold
    for limit, band in BANDS:
        if margin < limit:
            return band
    return "high"


def face_for(c: dict) -> dict | None:
    """Stored detector/quality evidence for a candidate face, if still indexed."""
    return next((f for f in vector_store.faces_for_photo(c["photo_id"]) if f["face_id"] == c["face_id"]), None)


def explain_candidate(c: dict, threshold: float, face: dict | None = None) -> dict:
    face = face or {}
    score = c.get("score")
    band = confidence_band(score, threshold)
    factors = []
    if score is not None:
        factors.append(f"Cosine similarity {score:.3f} vs threshold {threshold:.2f} (margin {score - threshold:+.3f}).")
    if face.get("det_score") is not None:
        factors.append(f"Face detector confidence {face['det_score']:.2f}; quality {face.get('quality', 0):.2f}.")
    factors.append("Proposed by the model" if c.get("source") == "model" else "Added manually by a reviewer")
    if c.get("decided_by"):
        factors.append(f"Decision '{c.get('decision')}' by reviewer {c['decided_by']}: {c.get('reason') or 'no reason given'}.")
    return {
        "face_id": c["face_id"],
        "photo_id": c["photo_id"],
        "score": score,
        "threshold": threshold,
        "margin": None if score is None else round(score - threshold, 4),
        "confidence_band": band,
        "band_meaning": BAND_MEANING[band],
        "bbox": c.get("bbox"),
        "det_score": face.get("det_score"),
        "quality": face.get("quality"),
        "model": get_settings().face_model_name,
        "factors": factors,
        "caveats": CAVEATS,
    }
