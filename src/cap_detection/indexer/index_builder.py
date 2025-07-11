# pyright: reportUnknownMemberType=false

import faiss
import numpy as np
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexBuilder:
    def __init__(self, embeddings: list[np.ndarray], metadata: list[str]):
        self.embeddings = embeddings
        self.metadata = metadata

    def build_index(self) -> faiss.Index:
        """Build a FAISS index in memory from given embeddings."""

        embeddings = np.array(self.embeddings).astype("float32")
        faiss.normalize_L2(embeddings)

        logger.info("Building FAISS index with %d vectors", len(embeddings))
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)  # pyright: ignore[reportCallIssue]

        logger.info("Index build complete")
        return index
