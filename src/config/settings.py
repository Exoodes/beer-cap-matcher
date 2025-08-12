from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    raw_data_dir: Path
    augmented_data_dir: Path
    u2net_model_path: Path
    augmentation_map_path: Path
    embeddings_output_path: Path
    faiss_index_path: Path
    faiss_metadata_path: Path
    augmentations_per_image: int = 20

    minio_original_caps_bucket: str
    minio_augmented_caps_bucket: str
    minio_index_bucket: str
    minio_index_file_name: str
    minio_metadata_file_name: str
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    postgres_database_url: str

    log_level: str = "INFO"

    test_minio_bucket_name: Optional[str] = None
    test_postgres_database_url: Optional[str] = None
    test_minio_url: Optional[str] = None
    test_minio_access_key: Optional[str] = None
    test_minio_secret_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
