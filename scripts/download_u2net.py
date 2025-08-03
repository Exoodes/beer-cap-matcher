import os

import gdown


def download_u2net_model():
    model_dir = "models"
    model_path = os.path.join(model_dir, "u2net.pth")
    if not os.path.exists(model_path):
        os.makedirs(model_dir, exist_ok=True)
        url = "https://drive.google.com/uc?id=1ao1ovG1Qtx4b7EoskHXmi2E9rp5CHLcZ"
        print("Downloading u2net.pth model...")
        gdown.download(url, model_path, quiet=False)
    else:
        print("U²-Net model already exists.")


if __name__ == "__main__":
    download_u2net_model()
