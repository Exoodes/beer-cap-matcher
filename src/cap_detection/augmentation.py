from typing import Tuple

import albumentations as A  # type: ignore[import-untyped]
from PIL import Image, ImageChops


def get_augmentation_pipeline(image_size: Tuple[int, int] = (224, 224)) -> A.Compose:
    return A.Compose(
        [
            A.Resize(*image_size),
            A.Affine(
                translate_percent={"x": (-0.05, 0.05), "y": (-0.05, 0.05)},
                scale=(0.5, 1.2),
                rotate=(-20, 20),
                p=1.0,
                keep_ratio=True,
            ),
            A.RandomBrightnessContrast(
                brightness_limit=(-0.3, 0.3), contrast_limit=(-0.3, 0.3), p=0.5
            ),
            A.OneOf(
                [
                    A.MotionBlur(p=0.2),
                    A.MedianBlur(blur_limit=3, p=0.1),
                    A.Blur(blur_limit=3, p=0.1),
                ],
                p=0.2,
            ),
        ],
        additional_targets={"alpha": "mask"},
    )


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
