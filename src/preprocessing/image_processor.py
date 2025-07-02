from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
from tqdm import tqdm

from src.preprocessing.background_remover import BackgroundRemover
from src.utils.logger import get_logger

from .augmentation import crop_transparent, get_augmentation_pipeline

logger = get_logger(__name__)


class ImageAugmenter:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        u2net_model_path: Path,
        augmentations_per_image: int = 10,
        image_size: Tuple[int, int] = (224, 224),
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.augmentations_per_image = augmentations_per_image
        self.pipeline = get_augmentation_pipeline(image_size=image_size)
        self.background_remover = BackgroundRemover(model_path=u2net_model_path)

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_image(self, path: Path) -> np.ndarray:
        image = Image.open(path).convert("RGBA")
        return np.array(image)

    def save_image(self, image_array: np.ndarray, save_path: Path) -> None:
        if image_array.shape[-1] == 4:
            image = Image.fromarray(image_array, mode="RGBA")
        else:
            image = Image.fromarray(image_array)
        image.save(save_path)

    def augment_and_save(self) -> None:
        images = list(self.input_dir.glob("*.[jp][pn]g"))  # jpg or png

        if not images:
            logger.warning(f"No images found in {self.input_dir}")
            return

        logger.info(f"Found {len(images)} images. Augmenting...")

        for img_path in tqdm(images, desc="Augmenting images"):
            try:
                img_array = self.load_image(img_path)

                # Background removal and cropping
                img_pil = Image.fromarray(img_array)
                img_pil = self.background_remover.remove_background(img_pil)
                img_pil = crop_transparent(img_pil)
                img_array = np.array(img_pil)

                # Separate RGB and alpha
                if img_array.shape[-1] == 4:
                    rgb = img_array[..., :3]
                    alpha = img_array[..., 3]
                else:
                    rgb = img_array
                    alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)

                # Save original
                filename = f"{img_path.stem}_original.png"
                save_path = self.output_dir / filename
                self.save_image(np.dstack([rgb, alpha]), save_path)

                for i in range(self.augmentations_per_image):
                    augmented = self.pipeline(image=rgb, alpha=alpha)
                    aug_rgb = augmented["image"]
                    aug_alpha = augmented["alpha"]

                    if aug_alpha.ndim == 2:
                        aug_alpha = aug_alpha[..., None]

                    aug_rgba = np.concatenate([aug_rgb, aug_alpha], axis=-1)

                    filename = f"{img_path.stem}_aug_{i:03d}.png"
                    save_path = self.output_dir / filename
                    self.save_image(aug_rgba, save_path)

            except Exception as e:
                logger.error(f"Failed to process {img_path.name}: {e}")

        logger.info("Augmentation complete.")
