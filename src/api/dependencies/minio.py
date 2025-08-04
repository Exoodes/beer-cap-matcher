from src.storage.minio.minio_client import MinioClientWrapper


def get_minio_client() -> MinioClientWrapper:
    """Gets a Minio client wrapper instance.

    This function serves as a dependency injector. It creates and returns
    a singleton instance of the `MinioClientWrapper`, which is used to interact
    with the Minio object storage service.

    Returns:
        MinioClientWrapper: An initialized Minio client wrapper instance.
    """
    return MinioClientWrapper()
