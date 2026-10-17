import asyncio
import io
import logging
import uuid
from typing import BinaryIO, Callable, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.augmented_beer_cap.augmented_cap_create import (
    AugmentedCapCreateSchema,
)
from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.config import settings
from src.db.crud.augmented_cap_crud import create_augmented_cap, get_all_augmented_caps
from src.db.crud.beer_brand_crud import (
    create_beer_brand,
    get_beer_brand_by_id,
    get_beer_brand_by_name,
)
from src.db.crud.beer_cap_crud import create_beer_cap, get_beer_cap_by_id
from src.db.crud.beer_crud import (
    create_beer,
    get_beer_by_brand_and_name,
    get_beer_by_id,
)
from src.db.crud.country_crud import (
    create_country,
    get_country_by_id,
    get_country_by_name,
)
from src.db.database import GLOBAL_ASYNC_SESSION_MAKER
from src.db.entities.augmented_cap_entity import AugmentedCap
from src.db.entities.beer_brand_entity import BeerBrand
from src.db.entities.beer_cap_entity import BeerCap
from src.db.entities.country_entity import Country
from src.services.errors import NotFoundError
from src.storage.minio.minio_client import MinioClientWrapper
from src.utils.image_ingest import (
    THUMBNAIL_CONTENT_TYPE,
    InvalidImageError,
    make_thumbnail,
)

logger = logging.getLogger(__name__)

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


# Generated keys never change content, so browsers may cache them forever.
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"


def new_cap_object_name(content_type: str) -> str:
    """Generates a unique storage key; client filenames are never used as keys."""
    return f"caps/{uuid.uuid4().hex}{EXTENSIONS.get(content_type, '')}"


def thumbnail_object_name(original_key: str) -> str:
    """Thumbnail key derived from the original's (unique) key."""
    return f"thumbs/{original_key}.webp"


class BeerCapFacade:
    def __init__(
        self,
        minio_wrapper: MinioClientWrapper,
        session_maker: Callable[[], AsyncSession] = GLOBAL_ASYNC_SESSION_MAKER,
    ):
        self.minio_wrapper = minio_wrapper
        self.session_maker = session_maker

        self.original_caps_bucket = settings.minio_original_caps_bucket
        self.augmented_caps_bucket = settings.minio_augmented_caps_bucket

        if not self.original_caps_bucket or not self.augmented_caps_bucket:
            raise ValueError(
                "MINIO_ORIGINAL_CAPS_BUCKET and MINIO_AUGMENTED_CAPS_BUCKET must be set in .env"
            )

    async def get_or_create_beer_brand(
        self,
        session: AsyncSession,
        beer_brand_id: Optional[int],
        beer_brand_name: Optional[str],
    ) -> BeerBrand:
        if beer_brand_id:
            beer_brand = await get_beer_brand_by_id(session, beer_brand_id)
            if not beer_brand:
                raise NotFoundError("Beer brand not found.")
        elif beer_brand_name:
            beer_brand = await get_beer_brand_by_name(session, beer_brand_name)
            if not beer_brand:
                beer_brand = await create_beer_brand(
                    session, beer_brand_name, commit=False
                )
        else:
            raise ValueError("Beer brand ID or name is required.")
        return beer_brand

    async def get_or_create_country(
        self,
        session: AsyncSession,
        country_id: Optional[int],
        country_name: Optional[str],
    ) -> Optional[Country]:
        if country_id:
            country = await get_country_by_id(session, country_id)
            if not country:
                raise NotFoundError("Country not found.")
            return country
        elif country_name:
            country = await get_country_by_name(session, country_name)
            if not country:
                country = await create_country(
                    session,
                    CountryCreateSchema(name=country_name, description=""),
                    commit=False,
                )
            return country
        return None

    async def create_cap_and_related_entities(
        self,
        cap_metadata: BeerCapCreateSchema,
        image_data: BinaryIO,
        image_length: int,
        content_type: str = "image/png",
    ) -> Optional[BeerCap]:
        async with self.session_maker() as session:
            if cap_metadata.beer_id:
                beer = await get_beer_by_id(session, cap_metadata.beer_id)
                if not beer:
                    return None
            elif cap_metadata.beer_name:
                beer_brand = await self.get_or_create_beer_brand(
                    session, cap_metadata.beer_brand_id, cap_metadata.beer_brand_name
                )
                country = await self.get_or_create_country(
                    session, cap_metadata.country_id, cap_metadata.country_name
                )

                await session.flush()

                # The brand already has this beer: add the cap to it instead of
                # creating a duplicate.
                existing = await get_beer_by_brand_and_name(
                    session, beer_brand.id, cap_metadata.beer_name
                )
                beer = existing or await create_beer(
                    session,
                    name=cap_metadata.beer_name,
                    beer_brand_id=beer_brand.id,
                    country_id=country.id if country else None,
                    rating=cap_metadata.rating or 0,
                    commit=False,
                )

                await session.flush()

            else:
                return None

            created_cap = await self._insert_cap_and_upload(
                session, beer.id, cap_metadata, image_data, image_length, content_type
            )

            fetched_cap = await get_beer_cap_by_id(
                session, created_cap.id, load_beer=True
            )
            return fetched_cap

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

            created_cap = await self._insert_cap_and_upload(
                session, beer.id, cap_metadata, image_data, image_length, content_type
            )
            fetched_cap = await get_beer_cap_by_id(
                session, created_cap.id, load_beer=True
            )
            return fetched_cap

    async def _insert_cap_and_upload(
        self,
        session: AsyncSession,
        beer_id: int,
        cap_metadata: BeerCapCreateSchema,
        image_data: BinaryIO,
        image_length: int,
        content_type: str,
    ) -> BeerCap:
        """Inserts the cap row, uploads its image and thumbnail, then commits.

        If the insert fails nothing is uploaded; if the commit fails the
        uploaded objects are removed again. A thumbnail that can't be made
        is skipped (the cap then shows its original image).
        """
        object_name = new_cap_object_name(content_type)
        image_bytes = image_data.read()
        image_data.seek(0)
        thumbnail = await self._make_thumbnail(image_bytes, object_name)
        thumbnail_name = thumbnail_object_name(object_name) if thumbnail else None

        created_cap = await create_beer_cap(
            session,
            beer_id,
            object_name,
            cap_metadata,
            commit=False,
            thumbnail_s3_key=thumbnail_name,
        )
        uploaded = [object_name]
        try:
            await asyncio.to_thread(
                self.minio_wrapper.upload_file,
                self.original_caps_bucket,
                object_name,
                image_data,
                image_length,
                content_type,
                IMMUTABLE_CACHE_CONTROL,
            )
            if thumbnail and thumbnail_name:
                await self._upload_thumbnail(thumbnail_name, thumbnail)
                uploaded.append(thumbnail_name)
            await session.commit()
        except Exception:
            await self._delete_objects(self.original_caps_bucket, uploaded)
            raise
        return created_cap

    async def replace_cap_image(
        self,
        beer_cap_id: int,
        image_data: BinaryIO,
        image_length: int,
        content_type: str,
    ) -> Optional[BeerCap]:
        """Gives a cap a new photo and thumbnail under a new key.

        The cap's augmented images described the old photo, so they are
        deleted. Old objects are removed only after the commit; if the
        upload or commit fails, the new objects are removed instead.

        Returns:
            The updated cap, or None if it doesn't exist.
        """
        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(
                session, beer_cap_id, load_augmented_caps=True
            )
            if not beer_cap:
                return None
            old_keys = [beer_cap.s3_key]
            if beer_cap.thumbnail_s3_key:
                old_keys.append(beer_cap.thumbnail_s3_key)
            augmented_keys = [aug.s3_key for aug in beer_cap.augmented_caps]

            object_name = new_cap_object_name(content_type)
            image_bytes = image_data.read()
            image_data.seek(0)
            thumbnail = await self._make_thumbnail(image_bytes, object_name)
            thumbnail_name = thumbnail_object_name(object_name) if thumbnail else None

            uploaded = [object_name]
            try:
                await asyncio.to_thread(
                    self.minio_wrapper.upload_file,
                    self.original_caps_bucket,
                    object_name,
                    image_data,
                    image_length,
                    content_type,
                    IMMUTABLE_CACHE_CONTROL,
                )
                if thumbnail and thumbnail_name:
                    await self._upload_thumbnail(thumbnail_name, thumbnail)
                    uploaded.append(thumbnail_name)

                await self._delete_augmented_caps_helper(session, beer_cap_id)
                beer_cap.s3_key = object_name
                beer_cap.thumbnail_s3_key = thumbnail_name
                await session.commit()
            except Exception:
                await self._delete_objects(self.original_caps_bucket, uploaded)
                raise

            updated = await get_beer_cap_by_id(session, beer_cap_id, load_beer=True)

        await self._delete_objects(self.augmented_caps_bucket, augmented_keys)
        await self._delete_objects(self.original_caps_bucket, old_keys)
        return updated

    async def _make_thumbnail(self, image_bytes: bytes, key: str) -> Optional[bytes]:
        try:
            return await asyncio.to_thread(
                make_thumbnail, image_bytes, settings.thumbnail_max_side
            )
        except InvalidImageError as e:
            logger.warning("No thumbnail for %s: %s", key, e)
            return None

    async def _upload_thumbnail(self, name: str, thumbnail: bytes) -> None:
        await asyncio.to_thread(
            self.minio_wrapper.upload_file,
            self.original_caps_bucket,
            name,
            io.BytesIO(thumbnail),
            len(thumbnail),
            THUMBNAIL_CONTENT_TYPE,
            IMMUTABLE_CACHE_CONTROL,
        )

    async def backfill_thumbnails(self) -> int:
        """Creates thumbnails for caps that don't have one yet.

        Safe to run repeatedly; caps whose image can't be read are skipped and
        retried next time.

        Returns:
            The number of thumbnails created.
        """
        async with self.session_maker() as session:
            result = await session.execute(
                select(BeerCap).where(BeerCap.thumbnail_s3_key.is_(None))
            )
            caps = list(result.scalars().all())
            created = 0
            for cap in caps:
                try:
                    original = await asyncio.to_thread(
                        self.minio_wrapper.download_bytes,
                        self.original_caps_bucket,
                        cap.s3_key,
                    )
                    thumbnail = await self._make_thumbnail(original, cap.s3_key)
                    if thumbnail is None:
                        continue
                    name = thumbnail_object_name(cap.s3_key)
                    await self._upload_thumbnail(name, thumbnail)
                except Exception as e:
                    logger.warning(
                        "Thumbnail backfill failed for %s: %s", cap.s3_key, e
                    )
                    continue
                cap.thumbnail_s3_key = name
                await session.commit()
                created += 1
        return created

    async def _delete_objects(self, bucket: str, object_names: list[str]) -> None:
        """Best-effort removal of stored objects after the DB has committed.

        A leftover object is harmless, so failures are logged, not raised.
        """
        for name in object_names:
            try:
                await asyncio.to_thread(self.minio_wrapper.delete_file, bucket, name)
            except Exception as e:
                logger.warning("Failed to delete %s/%s: %s", bucket, name, e)

    async def _delete_augmented_caps_helper(
        self, session: AsyncSession, beer_cap_id: int
    ) -> Optional[BeerCap]:
        beer_cap = await get_beer_cap_by_id(
            session, beer_cap_id, load_augmented_caps=True
        )
        if not beer_cap:
            return None

        for aug in beer_cap.augmented_caps:
            await session.delete(aug)

        await session.flush()
        return beer_cap

    async def delete_beer_cap_and_its_augmented_caps(self, beer_cap_id: int) -> bool:
        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(
                session, beer_cap_id, load_augmented_caps=True
            )
            if not beer_cap:
                return False

            augmented_keys = [aug.s3_key for aug in beer_cap.augmented_caps]
            original_keys = [beer_cap.s3_key]
            if beer_cap.thumbnail_s3_key:
                original_keys.append(beer_cap.thumbnail_s3_key)

            await session.delete(beer_cap)
            await session.commit()

        await self._delete_objects(self.augmented_caps_bucket, augmented_keys)
        await self._delete_objects(self.original_caps_bucket, original_keys)
        return True

    async def delete_augmented_caps(self, beer_cap_id: int) -> bool:
        async with self.session_maker() as session:
            beer_cap = await get_beer_cap_by_id(
                session, beer_cap_id, load_augmented_caps=True
            )
            if not beer_cap:
                return False
            augmented_keys = [aug.s3_key for aug in beer_cap.augmented_caps]

            await self._delete_augmented_caps_helper(session, beer_cap_id)
            await session.commit()

        await self._delete_objects(self.augmented_caps_bucket, augmented_keys)
        return True

    async def delete_all_augmented_caps(self) -> int:
        async with self.session_maker() as session:
            augmented_caps = await get_all_augmented_caps(session)
            s3_keys = [aug.s3_key for aug in augmented_caps]

            await session.execute(delete(AugmentedCap))
            await session.commit()

        if s3_keys:
            try:
                await asyncio.to_thread(
                    self.minio_wrapper.delete_files, self.augmented_caps_bucket, s3_keys
                )
            except Exception as e:
                logger.warning("Failed to delete augmented objects: %s", e)

        return len(s3_keys)

    async def delete_beer_and_caps(self, beer_id: int) -> bool:
        async with self.session_maker() as session:
            beer = await get_beer_by_id(session, beer_id, load_caps=True)
            if not beer:
                return False

            original_keys: list[str] = []
            augmented_keys: list[str] = []
            for cap in beer.caps:
                with_augmented = await get_beer_cap_by_id(
                    session, cap.id, load_augmented_caps=True
                )
                if with_augmented:
                    augmented_keys += [a.s3_key for a in with_augmented.augmented_caps]
                await self._delete_augmented_caps_helper(session, cap.id)
                original_keys.append(cap.s3_key)
                if cap.thumbnail_s3_key:
                    original_keys.append(cap.thumbnail_s3_key)
                await session.delete(cap)

            await session.delete(beer)
            await session.commit()

        await self._delete_objects(self.augmented_caps_bucket, augmented_keys)
        await self._delete_objects(self.original_caps_bucket, original_keys)
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
                self.augmented_caps_bucket,
                object_name,
                image_data,
                image_length,
                content_type,
            )

            aug_cap = await create_augmented_cap(session, beer_cap_id, object_name)

            return aug_cap

    def get_image_url(self, object_name: str, is_augmented: bool = False) -> str:
        """Browser URL of a stored image.

        Cap images get plain URLs (the bucket is public-read), which stay the
        same between requests so browsers cache them. Augmented images, and
        everything when PUBLIC_IMAGE_URLS is off, get presigned URLs.
        """
        if is_augmented:
            return self.minio_wrapper.generate_presigned_url(
                self.augmented_caps_bucket, object_name
            )
        if settings.public_image_urls:
            return self.minio_wrapper.public_url(self.original_caps_bucket, object_name)
        return self.minio_wrapper.generate_presigned_url(
            self.original_caps_bucket, object_name
        )
