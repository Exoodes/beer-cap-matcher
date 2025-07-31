import io
import os
from pathlib import Path
from typing import Awaitable, Callable, List

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.cap_detection.preprocessing.background_remover import BackgroundRemover
from src.cap_detection.preprocessing.image_processor import ImageAugmenter
from src.db.crud.augmented_cap import create_augmented_cap
from src.db.crud.beer_cap import get_all_beer_caps
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.storage.minio_client import MinioClientWrapper

load_dotenv()


class CapDetectionService:
    """Service for preprocessing beer cap images."""

    def __init__(
        self,
        minio_wrapper: MinioClientWrapper,
        session_maker: Callable[[], Awaitable[AsyncSession]] = GLOBAL_ASYNC_SESSION_MAKER,
        u2net_model_path: str | None = None,
        augmentations_per_image: int | None = None,
    ) -> None:
        self.minio_wrapper = minio_wrapper
        self.session_maker = session_maker

        self.original_caps_bucket = os.getenv("MINIO_ORIGINAL_CAPS_BUCKET")
        self.augmented_caps_bucket = os.getenv("MINIO_AUGMENTED_CAPS_BUCKET")

        if not self.original_caps_bucket or not self.augmented_caps_bucket:
            raise ValueError("MINIO_ORIGINAL_CAPS_BUCKET and MINIO_AUGMENTED_CAPS_BUCKET must be set in .env")

        self.u2net_model_path = u2net_model_path or os.getenv("U2NET_MODEL_PATH")
        if not self.u2net_model_path:
            raise ValueError("U2NET_MODEL_PATH must be provided or set in .env")

        self.augmentations_per_image = augmentations_per_image or int(os.getenv("AUGMENTATIONS_PER_IMAGE", 1))
        self.augmenter = ImageAugmenter(
            u2net_model_path=Path(self.u2net_model_path),
            augmentations_per_image=self.augmentations_per_image,
        )

    async def preprocess(self) -> int:
        """Download caps, augment them and upload results back to storage."""
        created = 0

        async with self.session_maker() as session:
            beer_caps = await get_all_beer_caps(session)

            for cap in beer_caps:
                original_bytes = self.minio_wrapper.download_bytes(self.original_caps_bucket, cap.s3_key)
                augmented_images = self.augmenter.augment_image_bytes(original_bytes)

                for idx, aug_bytes in enumerate(augmented_images):
                    object_name = f"{Path(cap.s3_key).stem}_aug_{idx:03d}.png"
                    self.minio_wrapper.upload_file(
                        self.augmented_caps_bucket, object_name, io.BytesIO(aug_bytes), len(aug_bytes)
                    )
                    await create_augmented_cap(session, cap.id, object_name)
                    created += 1

            await session.commit()

        return created
