import io
import os
from pathlib import Path
from typing import Awaitable, BinaryIO, Callable, Optional

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.augmented_cap import create_augmented_cap, delete_augmented_cap, get_all_augmented_caps
from src.db.crud.beer import create_beer, get_beer_by_id
from src.db.crud.beer_cap import create_beer_cap, get_beer_cap_by_id
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.db.entities.augmented_cap import AugmentedCap
from src.db.entities.beer_cap import BeerCap
from src.cap_detection.preprocessing.image_processor import ImageAugmenter
from src.schemas.augmented_cap_schema import AugmentedCapCreateSchema
from src.schemas.beer_cap_schema import BeerCapCreateSchema
from src.storage.minio_client import MinioClientWrapper

load_dotenv()


class BeerCapFacade:
    def __init__(
        self,
        minio_wrapper: MinioClientWrapper,
        session_maker: Callable[[], Awaitable[AsyncSession]] = GLOBAL_ASYNC_SESSION_MAKER,
    ):
        self.minio_wrapper = minio_wrapper
        self.session_maker = session_maker

        self.original_caps_bucket = os.getenv("MINIO_ORIGINAL_CAPS_BUCKET")
        self.augmented_caps_bucket = os.getenv("MINIO_AUGMENTED_CAPS_BUCKET")

        if not self.original_caps_bucket or not self.augmented_caps_bucket:
            raise ValueError("MINIO_ORIGINAL_CAPS_BUCKET and MINIO_AUGMENTED_CAPS_BUCKET must be set in .env")

    async def create_beer_with_cap_and_upload(
        self,
        beer_name: str,
        cap_metadata: BeerCapCreateSchema,
        image_data: BinaryIO,
        image_length: int,
        content_type: str = "image/png",
    ) -> BeerCap:
        async with self.session_maker() as session:
            beer = await create_beer(session, beer_name, False)

            object_name = cap_metadata.filename
            self.minio_wrapper.upload_file(
                self.original_caps_bucket, object_name, image_data, image_length, content_type
            )

            beer_cap = await create_beer_cap(session, beer.id, object_name, cap_metadata)
            beer_cap = await get_beer_cap_by_id(session, beer_cap.id, load_beer=True)
            return beer_cap

    async def create_cap_for_existing_beer_and_upload(
        self,
        beer_id: int,
        cap_metadata: BeerCapCreateSchema,
        image_data: BinaryIO,
        image_length: int,
        content_type: str = "image/png",
    ) -> Optional[BeerCap]:
        async with self.session_maker() as session:
            beer = await get_beer_by_id(session, beer_id)
            if not beer:
                return None

            object_name = cap_metadata.filename
            self.minio_wrapper.upload_file(
                self.original_caps_bucket, object_name, image_data, image_length, content_type
            )

            beer_cap = await create_beer_cap(session, beer.id, object_name, cap_metadata)
            beer_cap = await get_beer_cap_by_id(session, beer_cap.id, load_beer=True)
            return beer_cap

    async def _delete_augmented_caps_helper(self, session: AsyncSession, beer_cap_id: int) -> Optional[BeerCap]:
        beer_cap = await get_beer_cap_by_id(session, beer_cap_id, load_augmented_caps=True)
        if not beer_cap:
            return None

        for aug in beer_cap.augmented_caps:
            self.minio_wrapper.delete_file(self.augmented_caps_bucket, aug.s3_key)
            await session.delete(aug)

        await session.flush()
        return beer_cap

    async def delete_beer_cap_and_its_augmented_caps(self, beer_cap_id: int) -> bool:
        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(session, beer_cap_id, load_augmented_caps=True)
            if not beer_cap:
                return False

            for aug_cap in beer_cap.augmented_caps:
                self.minio_wrapper.delete_file(self.augmented_caps_bucket, aug_cap.s3_key)

            self.minio_wrapper.delete_file(self.original_caps_bucket, beer_cap.s3_key)

            await session.delete(beer_cap)
            await session.commit()
            return True

    async def delete_augmented_caps(self, beer_cap_id: int) -> bool:
        async with self.session_maker() as session:
            result = await self._delete_augmented_caps_helper(session, beer_cap_id)
            await session.commit()

        return result is not None

    async def delete_all_augmented_caps(self) -> int:
        deleted_count = 0
        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)
            for aug in augmented_caps:
                self.minio_wrapper.delete_file(self.augmented_caps_bucket, aug.s3_key)
                await delete_augmented_cap(session, aug.id)
                deleted_count += 1

            await session.commit()
        return deleted_count

    async def delete_beer_and_caps(self, beer_id: int) -> bool:
        async with self.session_maker() as session:
            beer = await get_beer_by_id(session, beer_id, load_caps=True)
            if not beer:
                return False

            for cap in beer.caps:
                await self._delete_augmented_caps_helper(session, cap.id)
                self.minio_wrapper.delete_file(self.original_caps_bucket, cap.s3_key)
                await session.delete(cap)

            await session.delete(beer)
            await session.commit()
            return True

    async def add_augmented_cap_and_upload(
        self,
        beer_cap_id: int,
        aug_metadata: AugmentedCapCreateSchema,
        image_data: BinaryIO,
        image_length: int,
        content_type: str = "image/png",
    ) -> Optional[AugmentedCap]:
        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(session, beer_cap_id)
            if not beer_cap:
                return None

            object_name = aug_metadata.filename
            self.minio_wrapper.upload_file(
                self.augmented_caps_bucket, object_name, image_data, image_length, content_type
            )

            aug_cap = await create_augmented_cap(session, beer_cap_id, object_name)

            return aug_cap

    def get_presigned_url_for_cap(self, filename: str, is_augmented: bool = False) -> str:
        object_name = filename
        bucket_name = self.augmented_caps_bucket if is_augmented else self.original_caps_bucket

        return self.minio_wrapper.generate_presigned_url(bucket_name, object_name)

    async def augment_beer_cap(
        self,
        beer_cap_id: int,
        u2net_model_path: Optional[str] = None,
        augmentations_per_image: int = 10,
    ) -> list[AugmentedCap]:
        """Download a beer cap, generate augmentations and upload them back."""

        if u2net_model_path is None:
            u2net_model_path = os.getenv("U2NET_MODEL_PATH")
            if not u2net_model_path:
                raise ValueError("U2NET_MODEL_PATH must be provided or set in environment")

        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(session, beer_cap_id)
            if not beer_cap:
                return []

            image_bytes = self.minio_wrapper.download_bytes(self.original_caps_bucket, beer_cap.s3_key)

            augmenter = ImageAugmenter(
                input_dir=None,
                output_dir=None,
                u2net_model_path=Path(u2net_model_path),
                augmentation_map_path=None,
                augmentations_per_image=augmentations_per_image,
            )

            augmented_images = augmenter.augment_image_bytes(image_bytes, beer_cap.s3_key)

            created: list[AugmentedCap] = []
            for filename, data in augmented_images.items():
                file_like = io.BytesIO(data)
                self.minio_wrapper.upload_file(
                    self.augmented_caps_bucket,
                    filename,
                    file_like,
                    len(data),
                    "image/png",
                )

                aug_cap = await create_augmented_cap(session, beer_cap_id, filename)
                created.append(aug_cap)

            await session.commit()
            return created
