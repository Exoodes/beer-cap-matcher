from pathlib import Path
from typing import Union

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from src.utils.logger import get_logger
from src.utils.u2net_model import U2NET

logger = get_logger(__name__)


class BackgroundRemover:
    def __init__(self, model_path: Path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = U2NET(3, 1)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose(
            [transforms.Resize((320, 320)), transforms.ToTensor()]
        )

    def remove_background(self, image: Union[Image.Image, np.ndarray]) -> Image.Image:
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image).convert("RGB")
        else:
            image = image.convert("RGB")

        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            pred = self.model(input_tensor)[0]
            mask = pred.squeeze().cpu().numpy()
            mask = (mask - mask.min()) / (mask.max() - mask.min())
            mask = cv2.resize(mask, image.size)
            mask = (mask * 255).astype(np.uint8)

        original = np.array(image)

        alpha = mask

        rgba = np.dstack((original, alpha))

        result_image = Image.fromarray(rgba, mode="RGBA")

        return result_image
