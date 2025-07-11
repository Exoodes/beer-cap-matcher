import io
from typing import Dict, Iterable, List, Tuple

import torch
from PIL import Image
from tqdm import tqdm

from src.embeddings.model_loader import load_model_and_preprocess
from src.utils.constants import EMBEDDINGS_KEY, IMAGE_PATHS_KEY
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate CLIP embeddings for images provided as bytes."""

    def __init__(self) -> None:
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()


    def generate_embeddings_from_bytes(self, images: Iterable[Tuple[str, bytes]]) -> Dict[str, List]:
        """Generate embeddings directly from image bytes."""

        embeddings: List[torch.Tensor] = []
        filenames: List[str] = []

        for filename, data in images:
            try:
                image = Image.open(io.BytesIO(data))

                if image.mode == "RGBA":
                    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                    image = Image.alpha_composite(background, image).convert("RGB")
                else:
                    image = image.convert("RGB")

                image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model.encode_image(image_tensor)
                    embedding = embedding.squeeze(0).cpu()

                embeddings.append(embedding)
                filenames.append(filename)

            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        return {IMAGE_PATHS_KEY: filenames, EMBEDDINGS_KEY: embeddings}

    def save_embeddings(self, embeddings: List[torch.Tensor], filenames: List[str]) -> None:
        """Deprecated: saving to disk is no longer supported."""
        raise NotImplementedError("Saving embeddings to disk is removed")

