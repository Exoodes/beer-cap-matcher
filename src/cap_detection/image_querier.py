from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import faiss  # type: ignore[import-untyped]
import numpy as np
import torch
from PIL import Image

from src.cap_detection.background_remover import BackgroundRemover
from src.cap_detection.image_processor import _process_image_for_embedding
from src.cap_detection.model_loader import load_model_and_preprocess
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedResult:
    """Aggregated similarity metrics for a beer cap match."""

    match_count: int
    mean_similarity: float
    min_similarity: float
    max_similarity: float


@dataclass
class _Agg:
    count: int = 0
    similarities: list[float] = field(default_factory=list)


class ImageQuerier:
    """Query a FAISS index with processed cap images."""

    def __init__(
        self,
        index: faiss.Index,
        metadata: list[int],
        augmented_cap_to_cap: dict[str, int],
        u2net_model_path: str,
        image_size: tuple[int, int] = (224, 224),
    ):
        """Initialise the querier with an index and preprocessing tools.

        Args:
            index: FAISS index containing cap embeddings.
            metadata: Mapping of index entries to cap identifiers.
            augmented_cap_to_cap: Lookup from augmented image IDs to original IDs.
            u2net_model_path: Path to the background removal model.
            image_size: Resolution used for preprocessing query images.
        """

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model: Any
        self.preprocess: Callable[[Image.Image], torch.Tensor]
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.index = index
        self.metadata = metadata
        self.augmented_cap_to_cap = augmented_cap_to_cap
        self.background_remover = BackgroundRemover(model_path=Path(u2net_model_path))
        self.image_size = image_size

    def query(
        self,
        image_bytes: Optional[bytes] = None,
        top_k: int = 3,
        faiss_k: int = 10000,
    ) -> dict[int, AggregatedResult]:
        """Run a nearest-neighbour search for a cap image.

        Args:
            image_bytes: Raw image data to search against the index.
            top_k: Number of aggregated results to return.
            faiss_k: Number of raw FAISS neighbours to retrieve before
                aggregation.

        Returns:
            A dictionary mapping cap IDs to their aggregated similarity
            statistics, ordered by mean similarity.
        """

        if image_bytes is None:
            raise ValueError("image_bytes must be provided")

        logger.info("Querying image from bytes")
        image_tensor = self._process_image_bytes(image_bytes)
        results = self._query_embedding(image_tensor, faiss_k)
        full_results = self._aggregate_results(results)

        top_k_items = dict(
            sorted(
                full_results.items(),
                key=lambda item: item[1].mean_similarity,
                reverse=True,
            )[:top_k]
        )

        return top_k_items

    def _process_image_bytes(self, data: bytes) -> torch.Tensor:
        processed_image = _process_image_for_embedding(
            data, self.background_remover, self.image_size
        )

        image_tensor = self.preprocess(processed_image).unsqueeze(0).to(self.device)
        return image_tensor

    def _query_embedding(
        self, image_tensor: torch.Tensor, top_k: int
    ) -> list[tuple[int, float]]:
        top_k = min(top_k, self.index.ntotal)
        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor).cpu().numpy()
            faiss.normalize_L2(embedding)

        similarities, indices = self.index.search(embedding, top_k)
        results = [
            (self.metadata[idx], float(sim))
            for idx, sim in zip(indices[0], similarities[0])
        ]
        return results

    def _aggregate_results(
        self, results: list[tuple[int, float]]
    ) -> dict[int, AggregatedResult]:
        aggregation: dict[int, _Agg] = defaultdict(_Agg)

        for matched_augmented_cap_id, similarity in results:
            cap_id = self.augmented_cap_to_cap.get(str(matched_augmented_cap_id))
            if cap_id is None:
                continue

            aggregation[cap_id].count += 1
            aggregation[cap_id].similarities.append(similarity)

        aggregated_results: dict[int, AggregatedResult] = {}
        for cap_id, data in aggregation.items():
            mean_similarity = float(np.mean(data.similarities))
            min_similarity = float(np.min(data.similarities))
            max_similarity = float(np.max(data.similarities))
            aggregated_results[cap_id] = AggregatedResult(
                match_count=data.count,
                mean_similarity=mean_similarity,
                min_similarity=min_similarity,
                max_similarity=max_similarity,
            )

        return aggregated_results
