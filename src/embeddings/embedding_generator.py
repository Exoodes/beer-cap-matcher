# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false


import os
import pickle
from typing import List, Tuple

import torch
from PIL import Image
from tqdm import tqdm

from src.utils.logger import get_logger
from src.embeddings.model_loader import load_model_and_preprocess

logger = get_logger(__name__)


class EmbeddingGenerator:
    def __init__(self, image_dir: str, output_path: str) -> None:
        self.image_dir = image_dir
        self.output_path = output_path
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = load_model_and_preprocess()
        self.model.eval()

    def generate_embeddings(self) -> None:
        embeddings: List[torch.Tensor] = []
        filenames: List[str] = []

        for filename in tqdm(os.listdir(self.image_dir), desc="Generating embeddings"):
            if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                continue

            image_path = os.path.join(self.image_dir, filename)
            try:
                image = Image.open(image_path).convert("RGB")
                image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model.encode_image(image_tensor)
                    embedding = embedding.squeeze(0).cpu()

                embeddings.append(embedding)
                filenames.append(filename)

            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        self.save_embeddings(embeddings, filenames)

    def save_embeddings(self, embeddings: List[torch.Tensor], filenames: List[str]) -> None:
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        data: Tuple[List[torch.Tensor], List[str]] = (embeddings, filenames)
        with open(self.output_path, "wb") as f:
            pickle.dump(data, f)

        logger.info(f"Saved {len(embeddings)} embeddings to {self.output_path}")
