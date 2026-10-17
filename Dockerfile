# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CLIP's setup.py needs pkg_resources, which newer setuptools no longer ships,
# so build without isolation against a pinned setuptools (same as CI).
RUN pip install "setuptools<70" wheel \
    && pip install --prefix=/install --no-build-isolation -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app

# Runtime dependencies for opencv and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# MinIO client for backups. dl.min.io no longer serves mc binaries, so take the
# statically linked one from the Chainguard MinIO image.
COPY --from=chainguard/minio:latest /usr/bin/mc /usr/local/bin/mc

COPY --from=builder /install /usr/local
COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.api.api_runner:app", "--host", "0.0.0.0", "--port", "8000"]
