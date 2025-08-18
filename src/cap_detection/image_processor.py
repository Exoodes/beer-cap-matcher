import io
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageChops

from src.cap_detection.background_remover import BackgroundRemover
from src.utils.logger import get_logger

from .augmentation import get_augmentation_pipeline

logger = get_logger(__name__)


def crop_transparent(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    bg = Image.new("RGBA", image.size, (0, 0, 0, 0))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    if bbox:
        return image.crop(bbox)
    else:
        return image


def _process_image_for_embedding(
    image_bytes: bytes,
    background_remover: BackgroundRemover,
    image_size: Tuple[int, int] = (224, 224),
) -> Image.Image:
    """
    Centralized function for image preprocessing.
    Performs background removal, cropping, and resizing.
    """
    img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img_pil = background_remover.remove_background(img_pil)
    img_pil = crop_transparent(img_pil)
    return img_pil.resize(image_size, Image.LANCZOS)


class ImageAugmenter:
    def __init__(
        self,
        u2net_model_path: Path,
        augmentations_per_image: int = 10,
        image_size: Tuple[int, int] = (224, 224),
    ):
        self.augmentations_per_image = augmentations_per_image
        self.pipeline = get_augmentation_pipeline(image_size=image_size)
        self.image_size = image_size
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

    def augment_image_bytes(self, image_bytes: bytes) -> List[bytes]:
        """
        Augment a single image provided as bytes and return a list of augmented image bytes (including the original).
        The processing pipeline is now handled by the new utility function.
        """
        processed_image = _process_image_for_embedding(
            image_bytes, self.background_remover, self.image_size
        )
        img_array = np.array(processed_image)

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

        for _ in range(self.augmentations_per_image):
            augmented = self.pipeline(image=rgb, alpha=alpha)
            aug_rgb = augmented["image"]
            aug_alpha = augmented["alpha"]

            if aug_alpha.ndim == 2:
                aug_alpha = aug_alpha[..., None]

            aug_rgba = np.concatenate([aug_rgb, aug_alpha], axis=-1)
            results.append(to_bytes(aug_rgba))

        return results
