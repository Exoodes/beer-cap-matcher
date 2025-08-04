import os
from typing import Optional

import gdown


def download_u2net_model(model_path: Optional[str] = None) -> None:
    """Downloads the U²-Net model from Google Drive.

    Checks if the model file already exists at the specified path. If not, it
    creates the necessary directories and downloads the model.

    Args:
        model_path: The full path where the model should be saved.
            If None, it defaults to the value of the U2NET_MODEL_PATH
            environment variable, or 'data/models/u2net.pth' if the
            variable is not set.
    """
    if model_path is None:
        model_path = os.getenv("U2NET_MODEL_PATH", "data/models/u2net.pth")

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
