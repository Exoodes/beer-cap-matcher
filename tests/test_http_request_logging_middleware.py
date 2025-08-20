import json
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.testclient import TestClient

from src.api.middleware.http_request_logging_middleware import LogRequestMiddleware


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LogRequestMiddleware)

    @app.post("/json")
    async def json_endpoint(request: Request):
        data = await request.json()
        state_body = getattr(request.state, "body", b"").decode()
        return {"received": data, "state_body": state_body}

    @app.post("/upload")
    async def upload_endpoint(file: UploadFile = File(...)):
        content = await file.read()
        return {"filename": file.filename, "size": len(content)}

    return app


def test_json_request_handling():
    app = create_app()
    client = TestClient(app)

    payload = {"hello": "world"}
    response = client.post("/json", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["received"] == payload
    assert json.loads(data["state_body"]) == payload


def test_multipart_request_handling():
    app = create_app()
    client = TestClient(app)

    file_content = b"test file"
    files = {"file": ("test.txt", file_content, "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["size"] == len(file_content)
