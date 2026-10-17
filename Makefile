PYTHON=python

clean:
	rm -rf data/augmented/*
	rm -f models/embeddings.pkl
	rm -f models/faiss.index
	rm -f models/metadata.pkl
	rm -f models/u2net.pth
	rm -f models/augmentation_map.json
	@echo "🧹 Cleaned all generated files."

setup:
	$(PYTHON) -m scripts.download_u2net
	@echo "✅ Setup complete: U²-Net model downloaded."

api:
	uvicorn src.api.api_runner:app --reload --host 0.0.0.0 --port 8000

setup-postgres:
	python -m scripts.create_tables
	@echo "✅ PostgreSQL tables ensured."

seed-postgres:
	python -m scripts.seed_db
	@echo "✅ PostgreSQL database seeded."

setup-minio:
	python -m scripts.setup_minio
	@echo "✅ MinIO buckets ensured."

setup-all: setup-postgres setup-minio
	@echo "🎉 All services set up successfully."

restart-docker:
	docker compose down -v
	docker compose up -d
	@echo "🔄 Docker services restarted."

test:
	$(PYTHON) -m pytest

restart-test-docker:
	docker compose -f docker-compose.test.yml down -v
	docker compose -f docker-compose.test.yml up -d
	@echo "🔄 Test Docker services restarted."

.PHONY: clean setup api test setup-postgres seed-postgres setup-minio setup-all restart-docker restart-test-docker
