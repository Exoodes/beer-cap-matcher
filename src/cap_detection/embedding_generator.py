import io
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import torch
from PIL import Image
from torchvision.utils import save_image

from src.cap_detection.model_loader import load_model_and_preprocess
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate CLIP embeddings for images provided as bytes."""

    def __init__(self, image_size: Tuple[int, int] = (224, 224)) -> None:
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()
        self.image_size = image_size

    def generate_embeddings_from_bytes(self, images: Iterable[Tuple[str, bytes]]) -> Dict[str, List]:
        """Generate embeddings directly from image bytes."""
        result = {}

        for filename, data in images:
            try:
                result[filename] = self.generate_embeddings(data)
            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        return result

    def generate_embeddings(self, bytes: bytes) -> torch.Tensor:
        """
        Generate embeddings directly from image bytes.
        This method assumes the input bytes are already preprocessed.
        """
        image = Image.open(io.BytesIO(bytes)).convert("RGBA")

        image_array = np.array(image)
        rgb = image_array[..., :3] if image_array.shape[-1] == 4 else image_array
        image_rgb = Image.fromarray(rgb)

        image_tensor = self.preprocess(image_rgb).unsqueeze(0).to(self.device)

        save_image(image_tensor, "embed_tensor.png")

        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor)
            embedding = embedding.squeeze(0).cpu()

        return embedding
