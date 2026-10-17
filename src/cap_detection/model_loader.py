from functools import lru_cache

import clip  # type: ignore[import-untyped]
import torch
from torch import nn
from torchvision.transforms import Compose  # type: ignore[import-untyped]

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def load_model_and_preprocess() -> tuple[nn.Module, Compose]:
    """Load the CLIP model and preprocessing pipeline.

    Returns:
        A tuple containing the loaded model and its preprocessing transform.
    """

    try:
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
        # Cache weights next to U²-Net so they persist in the mounted models volume.
        model, preprocess = clip.load(
            "ViT-B/32",
            device=device,
            download_root=str(settings.u2net_model_path.parent),
        )
        logger.info("Loaded CLIP model ViT-B/32")

        return model, preprocess
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        raise
