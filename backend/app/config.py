from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = ""
    s3_bucket_name: str = ""

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "faces"

    min_face_size: int = 40
    min_det_score: float = 0.5

    local_photo_dir: str = "./data/photos"
    allowed_origins: str = "http://localhost:3000"

    @property
    def use_s3(self) -> bool:
        return bool(self.s3_bucket_name and self.aws_access_key_id)

    @property
    def use_rekognition(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_region)

    @property
    def photo_dir(self) -> Path:
        p = Path(self.local_photo_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
