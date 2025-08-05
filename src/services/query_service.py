import asyncio
import os
import pickle
import tempfile
from typing import Awaitable, Callable, List, Tuple

import faiss
from sqlalchemy.ext.asyncio import AsyncSession

from src.cap_detection.image_querier import AggregatedResult, ImageQuerier
from src.db.crud.augmented_cap_crud import get_all_augmented_caps
from src.db.crud.beer_cap_crud import get_beer_cap_by_id
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.db.entities.beer_cap_entity import BeerCap


class QueryService:
    """Service for querying beer cap images."""

    def __init__(
        self,
        session_maker: Callable[[], Awaitable[AsyncSession]] = GLOBAL_ASYNC_SESSION_MAKER,
    ) -> None:
        self.session_maker = session_maker

        self.index_file_name = os.getenv("MINIO_INDEX_FILE_NAME")
        self.metadata_file_name = os.getenv("MINIO_METADATA_FILE_NAME")

        self.index = None
        self.metadata = None
        self.querier = None

    async def load_index(self) -> None:
        """Download FAISS index and metadata from MinIO and return them."""
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

        metadata = pickle.loads(metadata_blob)

        self.index = index
        self.metadata = metadata

        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)

        augmented_cap_to_cap = {aug.id: aug.beer_cap_id for aug in augmented_caps}

        self.querier = ImageQuerier(
            index=self.index,
            metadata=self.metadata,
            augmented_cap_to_cap=augmented_cap_to_cap,
            u2net_model_path=self.u2net_model_path,
        )

    async def query_image(
        self,
        image_bytes: bytes,
        top_k: int = 3,
        faiss_k: int = 10000,
    ) -> Tuple[List[BeerCap], List[AggregatedResult]]:
        """Query the FAISS index with an image."""
        results = self.querier.query(image_bytes=image_bytes, top_k=top_k, faiss_k=faiss_k)
        print(f"Queried {len(results)} results")
        caps = []

        async with self.session_maker() as session:
            for cap_id in results.keys():
                cap = await get_beer_cap_by_id(session, cap_id)
                assert cap is not None, f"Cap with ID {cap_id} not found"
                caps.append(cap)

        return caps, [result for result in results.values()]
