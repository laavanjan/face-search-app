"""Out-of-distribution inputs (SAFE-03): image formats, modes, sizes and
orientations the pipeline was not designed around must either be normalised to
a clean 3-channel image or rejected cleanly - never crash or leak metadata.
Model-level distribution shift is measured by backend/scripts/evaluate_robustness.py.
"""
import io

import numpy as np
import pytest
from PIL import Image

from app.services import pipeline


def _encode(img: Image.Image, fmt: str, **kw) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kw)
    return buf.getvalue()


OOD_IMAGES = {
    "grayscale_png": lambda: _encode(Image.new("L", (300, 200), 128), "PNG"),
    "rgba_png": lambda: _encode(Image.new("RGBA", (300, 200), (10, 20, 30, 0)), "PNG"),
    "palette_png": lambda: _encode(Image.new("P", (300, 200), 5), "PNG"),
    "cmyk_jpeg": lambda: _encode(Image.new("CMYK", (300, 200), (0, 50, 100, 0)), "JPEG"),
    "16bit_png": lambda: _encode(Image.new("I;16", (300, 200), 30000), "PNG"),
    "webp": lambda: _encode(Image.new("RGB", (300, 200), (90, 10, 10)), "WEBP"),
    "extreme_aspect": lambda: _encode(Image.new("RGB", (4000, 10), (1, 2, 3)), "PNG"),
    "tiny_1x1": lambda: _encode(Image.new("RGB", (1, 1), (1, 2, 3)), "PNG"),
    "huge_dims_downscaled": lambda: _encode(Image.new("RGB", (5000, 3000), (9, 9, 9)), "JPEG"),
}


@pytest.mark.parametrize("name", sorted(OOD_IMAGES))
def test_ood_images_normalised(name):
    bgr, clean, ext = pipeline.prepare(OOD_IMAGES[name]())
    assert bgr.ndim == 3 and bgr.shape[2] == 3 and bgr.dtype == np.uint8
    assert max(bgr.shape[:2]) <= pipeline.MAX_DIM
    assert ext in {"jpg", "png"}
    assert not Image.open(io.BytesIO(clean)).getexif()


def test_exif_orientation_applied():
    img = Image.new("RGB", (400, 200), (5, 5, 5))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees
    bgr, clean, _ = pipeline.prepare(_encode(img, "JPEG", exif=exif.tobytes()))
    assert bgr.shape[:2] == (400, 200)  # height, width after rotation
    assert not Image.open(io.BytesIO(clean)).getexif()


@pytest.mark.parametrize(
    "data",
    [b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, b"\xff\xd8\xff" + b"\x00" * 50, b"RIFF0000WEBP", bytes(range(256))],
)
def test_truncated_or_garbage_rejected(data):
    with pytest.raises(ValueError, match="invalid_image"):
        pipeline.prepare(data)
