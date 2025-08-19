from functools import lru_cache
from typing import Tuple

import clip  # type: ignore[import-untyped]
import torch
from torch import nn
from torchvision.transforms import Compose  # type: ignore[import-untyped]

from src.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def load_model_and_preprocess() -> Tuple[nn.Module, Compose]:
    try:
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        logger.info("Loaded CLIP model ViT-B/32")

        return model, preprocess
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        raise
