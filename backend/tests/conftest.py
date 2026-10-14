"""Test environment: isolated temp stores, synthetic data allowed, and one
API key per role. Env vars are set before `app` is imported so the cached
Settings pick them up (env vars also override any local backend/.env)."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="face-search-tests-")
os.environ.update(
    {
        "API_KEYS": ",".join(
            [
                "olivia:operator:op-token",
                "rita:reviewer:rev-token",
                "adam:admin:admin-token",
                "vic:viewer:view-token",
                "sam:operator+reviewer:sam-token",
            ]
        ),
        "ALLOWED_ROLE_BUNDLES": "operator+reviewer",
        "RATE_LIMIT_PER_MINUTE": "100000",
        "DATA_ENCRYPTION_KEY": "test-only-key",
        "GOVERNANCE_DB_PATH": os.path.join(_tmp, "governance.db"),
        "LOCAL_PHOTO_DIR": os.path.join(_tmp, "photos"),
        "QDRANT_URL": "",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_REGION": "",
        "S3_BUCKET_NAME": "",
        "SYNTHETIC_DATA_ENABLED": "true",
        "DATA_PROCESSING_LEGAL_BASIS": "consent",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

OPERATOR = {"Authorization": "Bearer op-token"}
REVIEWER = {"Authorization": "Bearer rev-token"}
ADMIN = {"Authorization": "Bearer admin-token"}
VIEWER = {"Authorization": "Bearer view-token"}
SAM = {"Authorization": "Bearer sam-token"}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.services import carbon, ratelimit

    ratelimit.reset_for_tests()
    carbon.reset_for_tests()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
