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
	$(PYTHON) -m src.main --download-bg-model
	@echo "✅ Setup complete: U²-Net model downloaded."

pipeline:
	$(PYTHON) -m src.main --augment --generate-embeddings --index
	@echo "🚀 Pipeline completed: augmented, embedded, and indexed."

query:
	$(PYTHON) -m src.main --query $(IMAGE)

repl:
	$(PYTHON) -m src.main --repl

api:
	uvicorn src.api.api_runner:app --reload --host 0.0.0.0 --port 8000

setup-postgres:
	python -m src.scripts.create_tables
	@echo "✅ PostgreSQL tables ensured."

setup-minio:
	python -m src.scripts.setup_minio
	@echo "✅ MinIO buckets ensured."

setup-all: setup-postgres setup-minio
	@echo "🎉 All services set up successfully."

restart-docker:
	docker-compose down -v
	docker-compose up -d
	@echo "🔄 Docker services restarted."

restart-test-docker:
	docker-compose -f docker-compose.test.yml down -v
	docker-compose -f docker-compose.test.yml up -d
	@echo "🔄 Test Docker services restarted."

.PHONY: clean setup pipeline query repl api setup-postgres setup-minio setup-all
