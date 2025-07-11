from collections import defaultdict
from dataclasses import dataclass
import io
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
import torch
from PIL import Image

from src.embeddings.model_loader import load_model_and_preprocess
from src.preprocessing.augmentation import crop_transparent
from src.preprocessing.background_remover import BackgroundRemover
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AggregatedResult:
    beer_cap_id: int
    match_count: int
    mean_distance: float
    min_distance: float
    max_distance: float


class ImageQuerier:
    def __init__(
        self,
        index: faiss.Index,
        filenames: List[str],
        filename_to_cap_id: Dict[str, int],
        u2net_model_path: str,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.index = index
        self.metadata = filenames
        self.filename_to_cap_id = filename_to_cap_id
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

    def query(
        self,
        image_bytes: Optional[bytes] = None,
        top_k: int = 5,
        faiss_k: int = 10000,
    ) -> List[AggregatedResult]:
        if image_bytes is None:
            raise ValueError("image_bytes must be provided")

        logger.info("Querying image from bytes")
        image_tensor = self._process_image_bytes(image_bytes)
        results = self._query_embedding(image_tensor, faiss_k)
        aggregated = self._aggregate_results(results)

        return aggregated[:top_k]


    def _process_image_bytes(self, data: bytes) -> torch.Tensor:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
        image = self.background_remover.remove_background(image)
        image = crop_transparent(image)

        image_array = np.array(image)
        rgb = image_array[..., :3] if image_array.shape[-1] == 4 else image_array
        image_pil = Image.fromarray(rgb)
        image_tensor = self.preprocess(image_pil).unsqueeze(0).to(self.device)
        return image_tensor

    def _query_embedding(self, image_tensor: torch.Tensor, top_k: int) -> List[Tuple[str, float]]:
        top_k = min(top_k, self.index.ntotal)
        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor).cpu().numpy()
            faiss.normalize_L2(embedding)

        distances, indices = self.index.search(embedding, top_k)
        results = [
            (self.metadata[idx], float(dist))
            for idx, dist in zip(indices[0], distances[0])
        ]
        return results

    def _aggregate_results(self, results: List[Tuple[str, float]]) -> List[AggregatedResult]:
        aggregation: Dict[int, Dict[str, List[float] | int]] = defaultdict(lambda: {"count": 0, "distances": []})

        for matched_filename, distance in results:
            cap_id = self.filename_to_cap_id.get(matched_filename)
            if cap_id is None:
                continue
            aggregation[cap_id]["count"] += 1  # type: ignore[index]
            aggregation[cap_id]["distances"].append(distance)  # type: ignore[index]

        aggregated_results = []
        for cap_id, data in aggregation.items():
            mean_distance = float(np.mean(data["distances"]))
            min_distance = float(np.min(data["distances"]))
            max_distance = float(np.max(data["distances"]))
            aggregated_results.append(
                AggregatedResult(
                    beer_cap_id=cap_id,
                    match_count=data["count"],
                    mean_distance=mean_distance,
                    min_distance=min_distance,
                    max_distance=max_distance,
                )
            )

        aggregated_results.sort(key=lambda x: x.mean_distance, reverse=True)
        return aggregated_results
