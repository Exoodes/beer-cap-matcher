import io
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

from src.cap_detection.background_remover import BackgroundRemover
from src.utils.logger import get_logger

from .augmentation import crop_transparent, get_augmentation_pipeline

logger = get_logger(__name__)


class ImageAugmenter:
    def __init__(
        self,
        u2net_model_path: Path,
        augmentations_per_image: int = 10,
        image_size: Tuple[int, int] = (224, 224),
    ):
        self.augmentations_per_image = augmentations_per_image
        self.pipeline = get_augmentation_pipeline(image_size=image_size)
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

    def augment_image_bytes(self, image_bytes: bytes) -> List[bytes]:
        """Augment a single image provided as bytes and return a mapping of filenames to image bytes."""

        img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        img_pil = self.background_remover.remove_background(img_pil)
        img_pil = crop_transparent(img_pil)
        img_array = np.array(img_pil)

        if img_array.shape[-1] == 4:
            rgb = img_array[..., :3]
            alpha = img_array[..., 3]
        else:
            rgb = img_array
            alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)

        def to_bytes(arr: np.ndarray) -> bytes:
            buf = io.BytesIO()
            Image.fromarray(arr, mode="RGBA").save(buf, format="PNG")
            return buf.getvalue()

        results: List[bytes] = []

        results.append(to_bytes(np.dstack([rgb, alpha])))

        for i in range(self.augmentations_per_image):
            augmented = self.pipeline(image=rgb, alpha=alpha)
            aug_rgb = augmented["image"]
            aug_alpha = augmented["alpha"]

            if aug_alpha.ndim == 2:
                aug_alpha = aug_alpha[..., None]

            aug_rgba = np.concatenate([aug_rgb, aug_alpha], axis=-1)
            results.append(to_bytes(aug_rgba))

        return results
