import subprocess
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies.auth import verify_admin
from src.api.routers.augmented_cap_router import router as augmented_cap_router
from src.api.routers.similarity_router import router as similarity_router
from src.config import settings


@pytest.fixture
def client_without_matching() -> TestClient:
    app = FastAPI()
    app.include_router(similarity_router)
    app.include_router(augmented_cap_router)
    app.state.query_service = None
    app.state.cap_detection_service = None
    app.dependency_overrides[verify_admin] = lambda: None
    return TestClient(app)


def test_similarity_returns_503_when_matching_disabled(
    client_without_matching: TestClient,
) -> None:
    resp = client_without_matching.post(
        "/similarity/query-image",
        files={"file": ("cap.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 503
    assert "ENABLE_MATCHING" in resp.json()["detail"]


@pytest.mark.parametrize(
    "path",
    [
        "/augmented_caps/generate_all/?augmentations_per_image=1",
        "/augmented_caps/generate_embeddings/",
        "/augmented_caps/generate_index/",
    ],
)
def test_pipeline_returns_503_when_matching_disabled(
    client_without_matching: TestClient, path: str
) -> None:
    resp = client_without_matching.post(path)
    assert resp.status_code == 503


def test_admin_endpoints_reject_everything_without_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "admin_secret_token", None)
    app = FastAPI()
    app.include_router(similarity_router)
    client = TestClient(app)

    resp = client.post(
        "/similarity/query-image",
        headers={"X-Admin-Token": ""},
        files={"file": ("cap.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 401


def test_admin_token_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_secret_token", "s3cret")
    app = FastAPI()
    app.include_router(similarity_router)
    app.state.query_service = None
    client = TestClient(app)
    files = {"file": ("cap.jpg", b"data", "image/jpeg")}

    wrong = client.post(
        "/similarity/query-image", headers={"X-Admin-Token": "nope"}, files=files
    )
    right = client.post(
        "/similarity/query-image", headers={"X-Admin-Token": "s3cret"}, files=files
    )
    assert wrong.status_code == 401
    assert right.status_code == 503


def test_api_import_does_not_load_ml_libraries() -> None:
    code = (
        "import sys; import src.api.api_runner; "
        "print(sorted(m for m in ('torch', 'clip', 'faiss') if m in sys.modules))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "[]"


@pytest.fixture
def health_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    import src.api.api_runner as api_runner
    from src.db.database import get_db_resources
    from tests.conftest import TEST_BUCKET_NAME, TEST_POSTGRES_DATABASE_URL

    assert TEST_POSTGRES_DATABASE_URL
    _, session_maker = get_db_resources(TEST_POSTGRES_DATABASE_URL, echo=False)
    monkeypatch.setattr(api_runner, "GLOBAL_ASYNC_SESSION_MAKER", session_maker)
    monkeypatch.setattr(settings, "minio_original_caps_bucket", TEST_BUCKET_NAME)
    monkeypatch.setattr(settings, "enable_matching", False)
    api_runner.app.state.query_service = None
    # No context manager: the lifespan (and its real MinIO client) is skipped.
    return TestClient(api_runner.app)


def test_health_reports_ok(health_client: TestClient, real_minio_client) -> None:
    health_client.app.state.minio_client = real_minio_client  # type: ignore[attr-defined]
    resp = health_client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checks"] == {"database": "ok", "storage": "ok"}
    assert body["matching"] == {"enabled": False, "index_loaded": False}


def test_health_returns_503_when_storage_down(health_client: TestClient) -> None:
    broken = MagicMock()
    broken.client.bucket_exists.side_effect = ConnectionError("down")
    health_client.app.state.minio_client = broken  # type: ignore[attr-defined]
    resp = health_client.get("/health")

    assert resp.status_code == 503
    assert resp.json()["checks"] == {"database": "ok", "storage": "error"}
