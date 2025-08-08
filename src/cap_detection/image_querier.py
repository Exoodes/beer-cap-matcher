from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
import torch
from PIL import Image
from torchvision.utils import save_image

from src.cap_detection.background_remover import BackgroundRemover
from src.cap_detection.image_processor import _process_image_for_embedding
from src.cap_detection.model_loader import load_model_and_preprocess
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedResult:
    match_count: int
    mean_distance: float
    min_distance: float
    max_distance: float


class ImageQuerier:
    def __init__(
        self,
        index: faiss.Index,
        metadata: List[int],
        augmented_cap_to_cap: Dict[str, int],
        u2net_model_path: str,
        image_size: Tuple[int, int] = (224, 224),
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.index = index
        self.metadata = metadata
        self.augmented_cap_to_cap = augmented_cap_to_cap
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)
        self.image_size = image_size

    def query(
        self,
        image_bytes: Optional[bytes] = None,
        top_k: int = 3,
        faiss_k: int = 10000,
    ) -> Dict[int, AggregatedResult]:
        if image_bytes is None:
            raise ValueError("image_bytes must be provided")

        logger.info("Querying image from bytes")
        image_tensor = self._process_image_bytes(image_bytes)
        save_image(image_tensor, "query_tensor.png")
        results = self._query_embedding(image_tensor, faiss_k)
        full_results = self._aggregate_results(results)

        top_k_items = dict(sorted(full_results.items(), key=lambda item: item[1].mean_distance, reverse=True)[:top_k])

        return top_k_items

    def _process_image_bytes(self, data: bytes) -> torch.Tensor:
        """
        Processes an image from bytes using the new shared utility function.
        """
        processed_image = _process_image_for_embedding(data, self.background_remover, self.image_size)

        image_array = np.array(processed_image)
        rgb = image_array[..., :3] if image_array.shape[-1] == 4 else image_array
        image_pil = Image.fromarray(rgb).resize(self.image_size, Image.LANCZOS)

        image_tensor = self.preprocess(image_pil).unsqueeze(0).to(self.device)
        return image_tensor

    def _query_embedding(self, image_tensor: torch.Tensor, top_k: int) -> List[Tuple[int, float]]:
        top_k = min(top_k, self.index.ntotal)
        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor).cpu().numpy()
            faiss.normalize_L2(embedding)

        distances, indices = self.index.search(embedding, top_k)
        results = [(self.metadata[idx], float(dist)) for idx, dist in zip(indices[0], distances[0])]
        return results

    def _aggregate_results(self, results: List[Tuple[int, float]]) -> Dict[int, AggregatedResult]:
        aggregation: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: {"count": 0, "distances": []})

        for matched_augmented_cap_id, distance in results:
            cap_id = self.augmented_cap_to_cap.get(matched_augmented_cap_id)
            if cap_id is None:
                continue

            aggregation[cap_id]["count"] += 1
            aggregation[cap_id]["distances"].append(distance)

        aggregated_results = {}
        for cap_id, data in aggregation.items():
            mean_distance = float(np.mean(data["distances"]))
            min_distance = float(np.min(data["distances"]))
            max_distance = float(np.max(data["distances"]))
            aggregated_results[cap_id] = AggregatedResult(
                match_count=data["count"],
                mean_distance=mean_distance,
                min_distance=min_distance,
                max_distance=max_distance,
            )

        return aggregated_results
