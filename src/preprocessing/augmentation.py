from albumentations import Compose, Rotate, RandomBrightnessContrast, GaussianBlur, HueSaturationValue, Resize
from typing import Tuple


def get_augmentation_pipeline(image_size: Tuple[int, int] = (224, 224)) -> Compose:
    return Compose(
        [
            Rotate(limit=15, p=0.9),
            RandomBrightnessContrast(p=0.8),
            GaussianBlur(blur_limit=(3, 7), p=0.3),
            HueSaturationValue(p=0.7),
            Resize(*image_size),
        ]
    )
