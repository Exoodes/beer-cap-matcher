from unittest.mock import MagicMock, patch
import sys

import torch
from PIL import Image

sys.modules["cv2"] = MagicMock()

from src.cap_detection.image_querier import ImageQuerier


@patch("src.cap_detection.image_querier._process_image_for_embedding")
@patch("src.cap_detection.image_querier.BackgroundRemover")
@patch("src.cap_detection.image_querier.load_model_and_preprocess")
def test_process_image_bytes_uses_image_processor(mock_load, mock_br, mock_process):
    dummy_model = MagicMock()
    dummy_preprocess = MagicMock(return_value=torch.zeros((3, 224, 224)))
    mock_load.return_value = (dummy_model, dummy_preprocess)
    mock_br.return_value = MagicMock()
    mock_process.return_value = Image.new("RGB", (224, 224))

    dummy_index = MagicMock()
    querier = ImageQuerier(
        index=dummy_index,
        metadata=[],
        augmented_cap_to_cap={},
        u2net_model_path="dummy",
    )

    tensor = querier._process_image_bytes(b"data")

    mock_process.assert_called_once()
    dummy_preprocess.assert_called_once_with(mock_process.return_value)
    assert tensor.shape == (1, 3, 224, 224)
