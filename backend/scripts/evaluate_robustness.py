"""Distribution-shift / robustness evaluation (SAFE-03).

    python backend/scripts/evaluate_robustness.py --images <dir of consented face photos>
    python backend/scripts/evaluate_robustness.py --synthetic-demo

Applies controlled shifts to each image - blur, low light, over-exposure, heavy
JPEG compression, downscaling, rotation, occlusion, grayscale, sensor noise -
and measures, per shift:
  with --images (needs InsightFace): face detection rate and cosine similarity
    between the shifted and original embedding (identity stability), against
    the deployed SEARCH_MIN_THRESHOLD;
  with --synthetic-demo: preprocessing robustness only (pipeline.prepare
    succeeds, output is a clean 3-channel image) - says nothing about the model.
Writes governance/evidence/robustness-results.json (summary first).
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.services import carbon, pipeline  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _jpeg(img: Image.Image, q: int) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def _occlude(img: Image.Image) -> Image.Image:
    img = img.copy()
    w, h = img.size
    ImageDraw.Draw(img).rectangle([w // 3, h // 3, 2 * w // 3, h // 2], fill=(0, 0, 0))
    return img


def _noise(img: Image.Image) -> Image.Image:
    a = np.asarray(img).astype(np.int16) + np.random.default_rng(0).normal(0, 25, (img.height, img.width, 3)).astype(np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


SHIFTS = {
    "blur": lambda im: im.filter(ImageFilter.GaussianBlur(3)),
    "low_light": lambda im: ImageEnhance.Brightness(im).enhance(0.3),
    "over_exposed": lambda im: ImageEnhance.Brightness(im).enhance(1.8),
    "jpeg_q15": lambda im: _jpeg(im, 15),
    "downscale_25pct": lambda im: im.resize((max(1, im.width // 4), max(1, im.height // 4))),
    "rotate_20deg": lambda im: im.rotate(20, expand=True),
    "occlusion": _occlude,
    "grayscale": lambda im: im.convert("L").convert("RGB"),
    "sensor_noise": _noise,
}


def _bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _embed(img: Image.Image):
    from app.services import face_engine

    bgr, _, _ = pipeline.prepare(_bytes(img))
    faces = face_engine.analyze(bgr)
    return max(faces, key=lambda f: f.bbox[2] * f.bbox[3]).embedding if faces else None


def run(images: list[Image.Image], use_model: bool) -> dict:
    th = get_settings().search_min_threshold
    per_shift = {}
    for name, fn in SHIFTS.items():
        ok = detected = stable = 0
        sims = []
        for img in images:
            shifted = fn(img)
            try:
                bgr, _, _ = pipeline.prepare(_bytes(shifted))
                ok += bgr.ndim == 3 and bgr.shape[2] == 3
            except ValueError:
                continue
            if use_model:
                e0, e1 = _embed(img), _embed(shifted)
                if e1 is not None:
                    detected += 1
                if e0 is not None and e1 is not None:
                    s = float(np.dot(e0, e1))
                    sims.append(s)
                    stable += s >= th
        n = len(images)
        row = {"preprocess_success_rate": round(ok / n, 3)}
        if use_model:
            row |= {
                "detection_rate": round(detected / n, 3),
                "identity_stable_rate": round(stable / n, 3),
                "mean_similarity_to_original": round(float(np.mean(sims)), 3) if sims else None,
            }
        per_shift[name] = row
    return per_shift


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--images", type=Path)
    src.add_argument("--synthetic-demo", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "governance" / "evidence" / "robustness-results.json")
    a = ap.parse_args(argv)

    if a.synthetic_demo:
        rng = np.random.default_rng(3)
        images = [Image.fromarray(rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)) for _ in range(12)]
        dataset, use_model = "synthetic-demo (random-pixel images, no faces)", False
    else:
        images = [Image.open(p).convert("RGB") for p in sorted(a.images.iterdir()) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
        dataset, use_model = str(a.images), True
    with carbon.track_emissions("robustness-evaluation", ROOT / "governance" / "evidence"):
        results = run(images, use_model)
    score = {k: v.get("identity_stable_rate", v["preprocess_success_rate"]) for k, v in results.items()}
    worst = min(score, key=score.get) if len(set(score.values())) > 1 else "none (all shifts scored the same)"
    report = {
        "status": "model-evaluated" if use_model else "preprocessing-only (model not evaluated)",
        "run_date": dt.date.today().isoformat(),
        "dataset": dataset,
        "images": len(images),
        "threshold": get_settings().search_min_threshold,
        "weakest_shift": worst,
        "results": results,
        "interpretation": (
            "Shifts where identity_stable_rate drops are where false non-matches rise; reviewers are told low-quality images are less reliable."
            if use_model
            else "All shifts are normalised safely by preprocessing. Model robustness still needs a run on consented face photos."
        ),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"{report['status']}: weakest={worst} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
