import asyncio
import io
import os
import pickle
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, List, Tuple

import faiss
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.cap_detection.background_remover import BackgroundRemover
from src.cap_detection.embedding_generator import EmbeddingGenerator
from src.cap_detection.image_processor import ImageAugmenter
from src.cap_detection.image_querier import AggregatedResult, ImageQuerier
from src.cap_detection.index_builder import IndexBuilder
from src.db.crud.augmented_cap import create_augmented_cap, get_all_augmented_caps
from src.db.crud.beer_cap import get_all_beer_caps, get_beer_cap_by_id
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.db.entities.beer_cap import BeerCap
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
        self.index_bucket = os.getenv("MINIO_INDEX_BUCKET")

        if not self.original_caps_bucket or not self.augmented_caps_bucket or not self.index_bucket:
            raise ValueError(
                "MINIO_ORIGINAL_CAPS_BUCKET, MINIO_AUGMENTED_CAPS_BUCKET, and MINIO_INDEX_BUCKET must be set in .env"
            )

        self.u2net_model_path = u2net_model_path or os.getenv("U2NET_MODEL_PATH")
        if not self.u2net_model_path:
            raise ValueError("U2NET_MODEL_PATH must be provided or set in .env")

        self.augmentations_per_image = augmentations_per_image or int(os.getenv("AUGMENTATIONS_PER_IMAGE", 1))
        self.augmenter = ImageAugmenter(
            u2net_model_path=Path(self.u2net_model_path),
            augmentations_per_image=self.augmentations_per_image,
        )

        self.embedding_generator = EmbeddingGenerator()
        self.index_builder = IndexBuilder()

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
                "beer-cap.index",
                io.BytesIO(index_data),
                len(index_data),
            )

            self.minio_wrapper.upload_file(
                self.index_bucket,
                "beer-cap.metadata.pkl",
                io.BytesIO(metadata_blob),
                len(metadata_blob),
            )

            return len(embeddings)

    async def get_index_with_metadata(self) -> tuple[faiss.Index, list[str]]:
        """Download FAISS index and metadata from MinIO and return them."""
        index_bytes = await asyncio.to_thread(
            self.minio_wrapper.download_bytes,
            self.index_bucket,
            "beer-cap.index",
        )

        metadata_blob = await asyncio.to_thread(
            self.minio_wrapper.download_bytes,
            self.index_bucket,
            "beer-cap.metadata.pkl",
        )

        with tempfile.NamedTemporaryFile(suffix=".index") as tmp:
            tmp.write(index_bytes)
            tmp.flush()
            index = faiss.read_index(tmp.name)

        metadata = pickle.loads(metadata_blob)
        return index, metadata

    async def query_image(
        self,
        image_bytes: bytes,
        top_k: int = 3,
        faiss_k: int = 10000,
    ) -> Tuple[List[BeerCap], List[AggregatedResult]]:
        """Query the FAISS index with an image."""
        index, metadata = await self.get_index_with_metadata()

        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)

        augmented_cap_to_cap = {aug.id: aug.beer_cap_id for aug in augmented_caps}

        querier = ImageQuerier(
            index=index,
            metadata=metadata,
            augmented_cap_to_cap=augmented_cap_to_cap,
            u2net_model_path=self.u2net_model_path,
        )

        results = querier.query(image_bytes=image_bytes, top_k=top_k, faiss_k=faiss_k)
        caps = []

        async with self.session_maker() as session:
            for cap_id in results.keys():
                cap = await get_beer_cap_by_id(session, cap_id)
                assert cap is not None, f"Cap with ID {cap_id} not found"
                caps.append(cap)

        return caps, [result for result in results.values()]
