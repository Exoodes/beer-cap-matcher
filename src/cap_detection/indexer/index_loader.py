# pyright: reportUnknownMemberType=false

import pickle
import faiss
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexLoader:
    def __init__(self, index_path: str, metadata_path: str):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata: List[str] = []

    def load(self) -> None:
        logger.info("Loading FAISS index from %s", self.index_path)
        self.index = faiss.read_index(self.index_path)

        logger.info("Loading metadata from %s", self.metadata_path)
        with open(self.metadata_path, "rb") as f:
            self.metadata = pickle.load(f)

        logger.info("Loaded index and %d metadata entries.", len(self.metadata))
