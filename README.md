# Beer Cap Matcher

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
