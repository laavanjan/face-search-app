from fastapi import HTTPException, UploadFile

from app.services.resilience import DeadlineExceeded

ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 15 * 1024 * 1024


async def read_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"Unsupported type {file.content_type}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Max 15MB per photo")
    return data


def pipeline_error(e: Exception, no_face_msg: str) -> HTTPException:
    if isinstance(e, DeadlineExceeded):
        return HTTPException(504, "Face analysis timed out; please retry or contact the service owner.")
    if isinstance(e, ImportError):
        return HTTPException(503, "Face analysis model is not installed on this server.")
    if isinstance(e, ValueError):
        msg = str(e)
        if msg == "no_face_detected":
            return HTTPException(422, no_face_msg)
        if msg == "invalid_image":
            return HTTPException(400, "File is not a readable image")
        if msg == "synthetic_data_rejected":
            return HTTPException(422, "Synthetic test fixtures are not accepted by this deployment")
    raise e
