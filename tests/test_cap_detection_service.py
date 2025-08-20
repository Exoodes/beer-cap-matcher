import sys
from unittest.mock import MagicMock, patch

import pytest
import torch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

sys.modules["cv2"] = MagicMock()

from src.api.schemas.beer_cap.beer_cap_create import BeerCapCreateSchema
from src.api.schemas.country.country_create import CountryCreateSchema
from src.config import settings
from src.db.crud.augmented_cap_crud import create_augmented_cap, get_all_augmented_caps
from src.db.crud.beer_brand_crud import create_beer_brand
from src.db.crud.beer_cap_crud import create_beer_cap
from src.db.crud.beer_crud import create_beer
from src.db.crud.country_crud import create_country
from src.services.cap_detection_service import CapDetectionService


@pytest.mark.asyncio
async def test_preprocess_creates_augmented_caps(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    brand = await create_beer_brand(db_session, "Brand")
    country = await create_country(db_session, CountryCreateSchema(name="Country"))
    beer = await create_beer(
        db_session, "Beer", brand.id, rating=5, country_id=country.id
    )
    await create_beer_cap(
        db_session,
        beer.id,
        "original.png",
        BeerCapCreateSchema(filename="original.png"),
    )

    session_maker = sessionmaker(
        bind=db_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    with patch("src.services.cap_detection_service.ImageAugmenter") as MockAug, patch(
        "src.services.cap_detection_service.EmbeddingGenerator"
    ), patch("src.services.cap_detection_service.IndexBuilder"):
        MockAug.return_value.augment_image_bytes.return_value = [b"aug"]
        service = CapDetectionService(
            mock_minio_client_wrapper, session_maker=session_maker
        )
        created = await service.preprocess(augmentations_per_image=1)

    assert created == 1
    mock_minio_client_wrapper.upload_file.assert_called_once()
    augmented_caps = await get_all_augmented_caps(db_session)
    assert len(augmented_caps) == 1


@pytest.mark.asyncio
async def test_generate_embeddings_stores_vectors(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    brand = await create_beer_brand(db_session, "Brand")
    country = await create_country(db_session, CountryCreateSchema(name="Country"))
    beer = await create_beer(
        db_session, "Beer", brand.id, rating=5, country_id=country.id
    )
    cap = await create_beer_cap(
        db_session,
        beer.id,
        "cap.png",
        BeerCapCreateSchema(filename="cap.png"),
    )
    await create_augmented_cap(db_session, cap.id, "aug.png")

    session_maker = sessionmaker(
        bind=db_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    with patch(
        "src.services.cap_detection_service.EmbeddingGenerator"
    ) as MockEmb, patch("src.services.cap_detection_service.IndexBuilder"):
        MockEmb.return_value.generate_embeddings.return_value = torch.tensor([0.1, 0.2])
        service = CapDetectionService(
            mock_minio_client_wrapper, session_maker=session_maker
        )
        result = await service.generate_embeddings()

    assert result["updated_embeddings"] == 1
    aug_caps = await get_all_augmented_caps(db_session)
    assert aug_caps[0].embedding_vector == [0.1, 0.2]


@pytest.mark.asyncio
async def test_generate_index_uploads_files(
    db_session: AsyncSession, mock_minio_client_wrapper: MagicMock
) -> None:
    brand = await create_beer_brand(db_session, "Brand")
    country = await create_country(db_session, CountryCreateSchema(name="Country"))
    beer = await create_beer(
        db_session, "Beer", brand.id, rating=5, country_id=country.id
    )
    cap = await create_beer_cap(
        db_session,
        beer.id,
        "cap.png",
        BeerCapCreateSchema(filename="cap.png"),
    )
    aug = await create_augmented_cap(db_session, cap.id, "aug.png")
    aug.embedding_vector = [0.1, 0.2]
    await db_session.commit()

    session_maker = sessionmaker(
        bind=db_session.bind, class_=AsyncSession, expire_on_commit=False
    )

    with patch(
        "src.services.cap_detection_service.IndexBuilder"
    ) as MockIndexBuilder, patch(
        "src.services.cap_detection_service.EmbeddingGenerator"
    ), patch(
        "src.services.cap_detection_service.faiss.write_index"
    ) as mock_write_index:
        MockIndexBuilder.return_value.build_index.return_value = (
            MagicMock(name="faiss_index"),
            b"meta",
        )
        mock_write_index.side_effect = lambda index, fname: open(fname, "wb").write(
            b"index"
        )

        service = CapDetectionService(
            mock_minio_client_wrapper, session_maker=session_maker
        )
        count = await service.generate_index()

    assert count == 1
    assert mock_minio_client_wrapper.upload_file.call_count == 2
    uploaded = [
        call.args[1] for call in mock_minio_client_wrapper.upload_file.call_args_list
    ]
    assert settings.minio_index_file_name in uploaded
    assert settings.minio_metadata_file_name in uploaded

    args, _ = MockIndexBuilder.return_value.build_index.call_args
    assert args[0] == [[0.1, 0.2]]
    assert args[1] == [aug.id]
