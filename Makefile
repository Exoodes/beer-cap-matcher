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
	uvicorn run_api:app --reload --host 0.0.0.0 --port 8000

.PHONY: clean setup pipeline query repl
