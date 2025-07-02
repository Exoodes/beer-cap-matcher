PYTHON=python
RAW_DATA_DIR=data/images
AUGMENTED_DATA_DIR=data/augmented
EMBEDDINGS_PATH=models/embeddings.pkl
INDEX_PATH=models/faiss.index
METADATA_PATH=models/metadata.pkl
MODEL_PATH=models/u2net.pth

clean:
	rm -rf $(AUGMENTED_DATA_DIR)/*
	rm -f $(EMBEDDINGS_PATH)
	rm -f $(INDEX_PATH)
	rm -f $(METADATA_PATH)
	@echo "🧹 Cleaned augmented images, embeddings, and index."

setup:
	$(PYTHON) -m src.main --download-bg-model
	@echo "✅ Setup complete: U²-Net model downloaded."

pipeline:
	$(PYTHON) -m src.main --augment --generate-embeddings --index
	@echo "🚀 Pipeline completed: augmented, embedded, and indexed."

query:
	$(PYTHON) -m src.main --query $(IMAGE)

.PHONY: clean setup pipeline query
