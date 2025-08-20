import pickle
from typing import List

import faiss  # type: ignore[import-untyped]
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexBuilder:
    """Create and serialize FAISS indexes for cap embeddings."""

    def build_index(
        self, embeddings: List[List[float]], metadata: List[int]
    ) -> tuple[faiss.IndexFlatIP, bytes]:
        """
        Build a FAISS index from in-memory data.

        Args:
            embeddings: A list of float vectors (same length).
            metadata: A list of identifiers (e.g. s3 keys or image IDs).

        Returns:
            index: The built FAISS index object.
            metadata_blob: The pickled metadata for saving.
        """
        logger.info("Building FAISS index with %d vectors", len(embeddings))

        np_embeddings = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(np_embeddings)

        index = faiss.IndexFlatIP(np_embeddings.shape[1])
        index.add(np_embeddings)

        metadata_blob = pickle.dumps(metadata)

        return index, metadata_blob
