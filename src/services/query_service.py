import asyncio
import pickle
import tempfile
from typing import Any, Callable, List, Tuple, cast

import faiss  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession

from src.cap_detection.image_querier import AggregatedResult, ImageQuerier
from src.config.settings import settings
from src.db.crud.augmented_cap_crud import get_all_augmented_caps
from src.db.crud.beer_cap_crud import get_beer_cap_by_id
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.db.entities.beer_cap_entity import BeerCap
from src.storage.minio.minio_client import MinioClientWrapper


class QueryService:
    """Service for querying beer cap images."""

    def __init__(
        self,
        minio_wrapper: MinioClientWrapper,
        session_maker: Callable[[], AsyncSession] = GLOBAL_ASYNC_SESSION_MAKER,
    ) -> None:
        self.session_maker = session_maker
        self.minio_wrapper = minio_wrapper

        self.index_file_name = settings.minio_index_file_name
        self.metadata_file_name = settings.minio_metadata_file_name
        self.index_bucket = settings.minio_augmented_caps_bucket
        self.u2net_model_path = settings.u2net_model_path

        self.index: Any | None = None
        self.metadata: list[int] | None = None
        self.querier: ImageQuerier | None = None

    async def load_index(self) -> None:
        if not self.minio_wrapper.object_exists(
            self.index_bucket, self.index_file_name
        ) or not self.minio_wrapper.object_exists(
            self.index_bucket, self.metadata_file_name
        ):
            return

        index_bytes = await asyncio.to_thread(
            self.minio_wrapper.download_bytes,
            self.index_bucket,
            self.index_file_name,
        )

        metadata_blob = await asyncio.to_thread(
            self.minio_wrapper.download_bytes,
            self.index_bucket,
            self.metadata_file_name,
        )

        with tempfile.NamedTemporaryFile(suffix=".index") as tmp:
            tmp.write(index_bytes)
            tmp.flush()
            index = faiss.read_index(tmp.name)

        metadata = cast(list[int], pickle.loads(metadata_blob))

        self.index = index
        self.metadata = metadata

        session = self.session_maker()
        async with session:
            augmented_caps = await get_all_augmented_caps(session)

        augmented_cap_to_cap = {str(aug.id): aug.beer_cap_id for aug in augmented_caps}

        self.querier = ImageQuerier(
            index=self.index,
            metadata=self.metadata,
            augmented_cap_to_cap=augmented_cap_to_cap,
            u2net_model_path=str(self.u2net_model_path),
        )

    async def query_image(
        self,
        image_bytes: bytes,
        top_k: int = 3,
        faiss_k: int = 10000,
    ) -> Tuple[List[BeerCap], List[AggregatedResult]]:
        if self.querier is None:
            raise RuntimeError("Index not loaded; call load_index() first")

        results = self.querier.query(
            image_bytes=image_bytes, top_k=top_k, faiss_k=faiss_k
        )
        print(f"Queried {len(results)} results")

        caps: List[BeerCap] = []

        session = self.session_maker()
        async with session:
            for cap_id in results.keys():
                cap = await get_beer_cap_by_id(session, cap_id)
                assert cap is not None, f"Cap with ID {cap_id} not found"
                caps.append(cap)

        return caps, [result for result in results.values()]
