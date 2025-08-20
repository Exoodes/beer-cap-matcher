import os
from typing import Optional

import gdown

from src.config import settings


def download_u2net_model(model_path: Optional[str] = None) -> None:
    """Downloads the U²-Net model from Google Drive.

    Checks if the model file already exists at the specified path. If not, it
    creates the necessary directories and downloads the model.

    Args:
        model_path: The full path where the model should be saved. If ``None``,
            the value of :data:`settings.u2net_model_path` is used. By default
            this points to ``models/u2net.pth`` but can be overridden via the
            ``U2NET_MODEL_PATH`` environment variable.
    """
    if model_path is None:
        # Use the same default path as ``settings.u2net_model_path`` which
        # itself honours the ``U2NET_MODEL_PATH`` environment variable.
        model_path = str(settings.u2net_model_path)

    if not os.path.exists(model_path):
        model_dir = os.path.dirname(model_path)
        if model_dir:
            os.makedirs(model_dir, exist_ok=True)

        url = "https://drive.google.com/uc?id=1ao1ovG1Qtx4b7EoskHXmi2E9rp5CHLcZ"
        print(f"Downloading u2net.pth model to {model_path}...")
        gdown.download(url, model_path, quiet=False)
    else:
        print(f"U²-Net model already exists at {model_path}.")


if __name__ == "__main__":
    download_u2net_model()
