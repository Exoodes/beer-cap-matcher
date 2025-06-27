from pathlib import Path
from typing import Union
import numpy as np
from PIL import Image
from typing import Tuple

from .augmentation import get_augmentation_pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ImageAugmenter:
    def __init__(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
        augmentations_per_image: int = 10,
        image_size: Tuple[int, int] = (224, 224),
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.augmentations_per_image = augmentations_per_image
        self.pipeline = get_augmentation_pipeline(image_size=image_size)

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_image(self, path: Path) -> np.ndarray:
        image = Image.open(path).convert("RGB")
        return np.array(image)

    def save_image(self, image_array: np.ndarray, save_path: Path) -> None:
        image = Image.fromarray(image_array)
        image.save(save_path)

    def augment_and_save(self) -> None:
        images = list(self.input_dir.glob("*.[jp][pn]g"))  # jpg or png

        if not images:
            logger.warning(f"No images found in {self.input_dir}")
            return

        logger.info(f"Found {len(images)} images. Augmenting...")

        for img_path in images:
            try:
                img_array = self.load_image(img_path)
                for i in range(self.augmentations_per_image):
                    augmented = self.pipeline(image=img_array)["image"]
                    filename = f"{img_path.stem}_aug_{i:03d}{img_path.suffix}"
                    save_path = self.output_dir / filename
                    self.save_image(augmented, save_path)

                logger.info(f"Augmented {img_path.name} × {self.augmentations_per_image}")
            except Exception as e:
                logger.error(f"Failed to process {img_path.name}: {e}")
