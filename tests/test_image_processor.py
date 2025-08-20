import sys
from pathlib import Path
from unittest.mock import MagicMock

from PIL import Image

sys.modules["cv2"] = MagicMock()

from src.cap_detection.image_processor import _process_image_for_embedding


class DummyBackgroundRemover:
    def remove_background(self, img: Image.Image) -> Image.Image:
        return img


def load_image_bytes() -> bytes:
    with open(Path("tests/data/test_image.jpg"), "rb") as f:
        return f.read()


def test_process_image_for_embedding_without_alpha():
    image_bytes = load_image_bytes()
    remover = DummyBackgroundRemover()
    processed = _process_image_for_embedding(image_bytes, remover, (128, 128))
    assert processed.mode == "RGB"
    assert processed.size == (128, 128)


def test_process_image_for_embedding_with_alpha():
    image_bytes = load_image_bytes()
    remover = DummyBackgroundRemover()
    processed = _process_image_for_embedding(
        image_bytes, remover, (128, 128), keep_alpha=True
    )
    assert processed.mode == "RGBA"
    assert processed.size == (128, 128)
