import asyncio
import io
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Awaitable, Callable

import faiss
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.cap_detection.embedding_generator import EmbeddingGenerator
from src.cap_detection.image_processor import ImageAugmenter
from src.cap_detection.index_builder import IndexBuilder
from src.db.crud.augmented_cap_crud import create_augmented_cap, get_all_augmented_caps
from src.db.crud.beer_cap_crud import get_all_beer_caps
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.storage.minio.minio_client import MinioClientWrapper

load_dotenv()


class CapDetectionService:
    """Service for preprocessing beer cap images."""

    def __init__(
        self,
        minio_wrapper: MinioClientWrapper,
        session_maker: Callable[[], Awaitable[AsyncSession]] = GLOBAL_ASYNC_SESSION_MAKER,
        u2net_model_path: str | None = None,
    ) -> None:
        self.minio_wrapper = minio_wrapper
        self.session_maker = session_maker

        self.original_caps_bucket = os.getenv("MINIO_ORIGINAL_CAPS_BUCKET")
        self.augmented_caps_bucket = os.getenv("MINIO_AUGMENTED_CAPS_BUCKET")
        self.index_bucket = os.getenv("MINIO_INDEX_BUCKET")
        self.u2net_model_path = u2net_model_path or os.getenv("U2NET_MODEL_PATH")
        self.index_file_name = os.getenv("MINIO_INDEX_FILE_NAME")
        self.metadata_file_name = os.getenv("MINIO_METADATA_FILE_NAME")

        self.embedding_generator = EmbeddingGenerator(self.u2net_model_path)
        self.index_builder = IndexBuilder()

    async def preprocess(self, augmentations_per_image: int) -> int:
        created = 0

        async with self.session_maker() as session:
            beer_caps = await get_all_beer_caps(session)
            augmenter = ImageAugmenter(
                u2net_model_path=self.u2net_model_path, augmentations_per_image=augmentations_per_image
            )

            def process_cap(cap):
                original_bytes = self.minio_wrapper.download_bytes(self.original_caps_bucket, cap.s3_key)
                augmented_images = augmenter.augment_image_bytes(original_bytes)
                return cap, augmented_images

            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                results = await asyncio.gather(*[loop.run_in_executor(executor, process_cap, cap) for cap in beer_caps])

            for cap, augmented_images in results:
                for idx, aug_bytes in enumerate(augmented_images):
                    object_name = f"{Path(cap.s3_key).stem}_aug_{idx:03d}.png"
                    self.minio_wrapper.upload_file(
                        self.augmented_caps_bucket, object_name, io.BytesIO(aug_bytes), len(aug_bytes)
                    )
                    await create_augmented_cap(session, cap.id, object_name)
                    created += 1

            await session.commit()
        return created

    async def generate_embeddings(self) -> dict:
        """Generate embeddings for augmented beer caps."""

        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)

            for aug_cap in augmented_caps:
                aug_bytes = await asyncio.to_thread(
                    self.minio_wrapper.download_bytes,
                    self.augmented_caps_bucket,
                    aug_cap.s3_key,
                )
                embedding_tensor = await asyncio.to_thread(
                    self.embedding_generator.generate_embeddings,
                    aug_bytes,
                )

                aug_cap.embedding_vector = embedding_tensor.tolist()

            await session.commit()
            return {"updated_embeddings": len(augmented_caps)}

    async def generate_index(self) -> int:
        """Generate FAISS index for augmented beer caps and store it in MinIO."""
        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)

            embeddings = []
            metadata = []
            for aug_cap in augmented_caps:
                if aug_cap.embedding_vector:
                    embeddings.append(aug_cap.embedding_vector)
                    metadata.append(aug_cap.id)

            index, metadata_blob = await asyncio.to_thread(self.index_builder.build_index, embeddings, metadata)

            with tempfile.NamedTemporaryFile(suffix=".index") as tmp:
                faiss.write_index(index, tmp.name)
                tmp.seek(0)
                index_data = tmp.read()

            self.minio_wrapper.upload_file(
                self.index_bucket,
                self.index_file_name,
                io.BytesIO(index_data),
                len(index_data),
            )

            self.minio_wrapper.upload_file(
                self.index_bucket,
                self.metadata_file_name,
                io.BytesIO(metadata_blob),
                len(metadata_blob),
            )

            return len(embeddings)
