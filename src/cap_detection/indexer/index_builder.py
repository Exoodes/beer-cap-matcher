# pyright: reportUnknownMemberType=false

import pickle

import faiss
import numpy as np

from src.utils.constants import EMBEDDINGS_KEY, IMAGE_PATHS_KEY
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexBuilder:
    def __init__(self, embedding_path: str, index_path: str, metadata_path: str):
        self.embedding_path = embedding_path
        self.index_path = index_path
        self.metadata_path = metadata_path

    def build_index(self) -> None:
        logger.info("Loading embeddings from %s", self.embedding_path)
        with open(self.embedding_path, "rb") as f:
            data = pickle.load(f)

        embeddings = np.array(data[EMBEDDINGS_KEY]).astype("float32")
        metadata = data[IMAGE_PATHS_KEY]

        faiss.normalize_L2(embeddings)

        logger.info("Building FAISS index with %d vectors", len(embeddings))
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)  # pyright: ignore[reportCallIssue]

        logger.info("Saving index to %s", self.index_path)
        faiss.write_index(index, self.index_path)

        logger.info("Saving metadata to %s", self.metadata_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(metadata, f)

        logger.info("Index building complete.")
