# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app

# Runtime dependencies for opencv and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    postgresql-client \
    && MC_VERSION="RELEASE.2025-04-08T15-39-49Z" \
    && curl --fail --location \
       "https://dl.min.io/client/mc/release/linux-amd64/archive/mc.${MC_VERSION}" \
       -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

EXPOSE 8000
CMD ["uvicorn", "src.api.api_runner:app", "--host", "0.0.0.0", "--port", "8000"]
