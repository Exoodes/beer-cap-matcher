import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

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
    original_image: str
    match_count: int
    mean_distance: float
    min_distance: float
    max_distance: float


class ImageQuerier:
    def __init__(
        self,
        index: faiss.Index,
        metadata: List[str],
        u2net_model_path: str,
        augmentation_map_path: str,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.index = index
        self.metadata = metadata
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

        with open(augmentation_map_path, "r") as f:
            self.augmentation_map: Dict[str, List[str]] = json.load(f)

        self.reverse_map: Dict[str, str] = {
            aug: original for original, aug_list in self.augmentation_map.items() for aug in aug_list
        }

        for original in self.augmentation_map.keys():
            self.reverse_map[original] = original

    def query(self, image_path: str, top_k: int = 5, faiss_k: int = 10000) -> List[AggregatedResult]:
        logger.info("Querying image: %s", image_path)

        image_tensor = self._process_image(image_path)
        results = self._query_embedding(image_tensor, faiss_k)
        aggregated = self._aggregate_results(results)

        return aggregated[:top_k]

    def _process_image(self, image_path: str) -> torch.Tensor:
        image = Image.open(image_path).convert("RGBA")
        image = self.background_remover.remove_background(image)
        image = crop_transparent(image)

        image_array = np.array(image)
        rgb = image_array[..., :3] if image_array.shape[-1] == 4 else image_array
        image_pil = Image.fromarray(rgb)
        image_tensor = self.preprocess(image_pil).unsqueeze(0).to(self.device)
        return image_tensor

    def _query_embedding(self, image_tensor: torch.Tensor, top_k: int) -> List[Tuple[str, float]]:
        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor).cpu().numpy()
            faiss.normalize_L2(embedding)

        distances, indices = self.index.search(embedding, top_k)
        results = [(self.metadata[idx], float(dist)) for idx, dist in zip(indices[0], distances[0])]
        return results

    def _aggregate_results(self, results: List[Tuple[str, float]]) -> List[AggregatedResult]:
        aggregation = defaultdict(lambda: {"count": 0, "distances": []})

        for matched_filename, distance in results:
            original = self.reverse_map.get(matched_filename, matched_filename)
            aggregation[original]["count"] += 1
            aggregation[original]["distances"].append(distance)

        aggregated_results = []
        for original, data in aggregation.items():
            mean_distance = float(np.mean(data["distances"]))
            min_distance = float(np.min(data["distances"]))
            max_distance = float(np.max(data["distances"]))
            aggregated_results.append(
                AggregatedResult(
                    original_image=original,
                    match_count=data["count"],
                    mean_distance=mean_distance,
                    min_distance=min_distance,
                    max_distance=max_distance,
                )
            )

        aggregated_results.sort(key=lambda x: x.mean_distance, reverse=True)
        return aggregated_results
