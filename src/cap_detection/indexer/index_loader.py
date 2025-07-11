# pyright: reportUnknownMemberType=false

import faiss
from typing import List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexLoader:
    def __init__(self, index: faiss.Index, metadata: List[str]):
        self.index = index
        self.metadata = metadata

    def load(self) -> None:  # kept for backwards compatibility
        logger.info("Index already loaded in memory; skipping disk load")
