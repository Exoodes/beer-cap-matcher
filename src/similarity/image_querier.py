from typing import Tuple

import faiss
import numpy as np
import torch
from PIL import Image

from src.embeddings.model_loader import load_model_and_preprocess
from src.preprocessing.augmentation import crop_transparent
from src.preprocessing.background_remover import BackgroundRemover
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageQuerier:
    def __init__(self, index: faiss.Index, metadata: list, u2net_model_path: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.index = index
        self.metadata = metadata

        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

    def query(self, image_path: str, top_k: int = 50) -> Tuple[list, list]:
        logger.info("Querying image: %s", image_path)

        image = Image.open(image_path).convert("RGBA")
        image = self.background_remover.remove_background(image)
        image = crop_transparent(image)

        image_array = np.array(image)

        if image_array.shape[-1] == 4:
            rgb = image_array[..., :3]
            alpha = image_array[..., 3]
        else:
            rgb = image_array
            alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)

        image_pil = Image.fromarray(rgb)
        image_tensor = self.preprocess(image_pil).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor).cpu().numpy()
            faiss.normalize_L2(embedding)

        logger.info("Searching index...")
        distances, indices = self.index.search(embedding, top_k)

        results = [(self.metadata[idx], float(dist)) for idx, dist in zip(indices[0], distances[0])]
        return results
