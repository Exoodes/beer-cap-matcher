from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    raw_data_dir: Path = Path("data/raw")
    augmented_data_dir: Path = Path("data/augmented")
    u2net_model_path: Path = Path("models/u2net.pth")
    augmentation_map_path: Path = Path("configs/augmentations.json")
    embeddings_output_path: Path = Path("data/embeddings.npy")
    faiss_index_path: Path = Path("data/faiss.index")
    faiss_metadata_path: Path = Path("data/faiss_meta.pkl")
    augmentations_per_image: int = 20

    minio_original_caps_bucket: str = "caps-original"
    minio_augmented_caps_bucket: str = "caps-augmented"
    minio_index_bucket: str = "caps-index"
    minio_index_file_name: str = "caps.index"
    minio_metadata_file_name: str = "caps.meta"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    postgres_database_url: str = (
        "postgresql+asyncpg://user:password@localhost:5432/appdb"
    )

    log_level: str = "INFO"

    test_minio_bucket_name: Optional[str] = None
    test_postgres_database_url: Optional[str] = None
    test_minio_url: Optional[str] = None
    test_minio_access_key: Optional[str] = None
    test_minio_secret_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
