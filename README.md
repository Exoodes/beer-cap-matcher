# Beer Cap Matcher

[![CI](https://github.com/OWNER/beer-cap-matcher/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/beer-cap-matcher/actions/workflows/ci.yml)

This project provides a FastAPI service for matching beer caps using image embeddings and FAISS.

## Running with Docker Compose

Build and start the services:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Health Checks

- The API exposes a `/health` endpoint returning the service status.
- `docker-compose.yml` defines health checks for the API, PostgreSQL and MinIO services.

Use `docker compose ps` to view container health states.

## U²-Net Model

The application uses the [U²-Net](https://github.com/xuebinqin/U-2-Net) model for
background removal. By default the model weights are expected at
`models/u2net.pth`. You can download the weights with:

```bash
python scripts/download_u2net.py
```

To store the model in a different location, set the `U2NET_MODEL_PATH`
environment variable to your desired path before running the download script or
the application.
