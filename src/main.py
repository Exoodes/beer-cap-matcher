import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.embeddings.embedding_generator import EmbeddingGenerator
from src.indexer.index_loader import IndexLoader
from src.preprocessing.image_processor import ImageAugmenter
from src.scripts.download_u2net import download_u2net_model
from src.similarity.image_querier import ImageQuerier

load_dotenv()


def run_augmentation():
    raw_data_dir = os.getenv("RAW_DATA_DIR")
    augmented_data_dir = os.getenv("AUGMENTED_DATA_DIR")
    u2net_model_path = os.getenv("U2NET_MODEL_PATH")
    augmentation_map_path = os.getenv("AUGMENTATION_MAP_PATH")

    if raw_data_dir is None or augmented_data_dir is None or u2net_model_path is None or augmentation_map_path is None:
        raise ValueError(
            "RAW_DATA_DIR, AUGMENTED_DATA_DIR, U2NET_MODEL_PATH, and AUGMENTATION_MAP_PATH environment variables must be set."
        )

    augmenter = ImageAugmenter(
        input_dir=Path(raw_data_dir),
        output_dir=Path(augmented_data_dir),
        u2net_model_path=Path(u2net_model_path),
        augmentation_map_path=Path(augmentation_map_path),
        augmentations_per_image=int(os.getenv("AUGMENTATIONS_PER_IMAGE", 20)),
    )
    augmenter.augment_and_save()


def run_embedding_generation():
    image_dir = os.getenv("AUGMENTED_DATA_DIR")
    output_path = os.getenv("EMBEDDINGS_OUTPUT_PATH")
    if image_dir is None or output_path is None:
        raise ValueError("AUGMENTED_DATA_DIR and EMBEDDINGS_OUTPUT_PATH environment variables must be set.")

    generator = EmbeddingGenerator(image_dir=image_dir, output_path=output_path)
    generator.generate_embeddings()


def run_indexing():
    from src.indexer.index_builder import IndexBuilder

    embedding_path = os.getenv("EMBEDDINGS_OUTPUT_PATH")
    index_path = os.getenv("FAISS_INDEX_PATH")
    metadata_path = os.getenv("FAISS_METADATA_PATH")

    if embedding_path is None or index_path is None or metadata_path is None:
        raise ValueError(
            "EMBEDDINGS_OUTPUT_PATH, FAISS_INDEX_PATH, and FAISS_METADATA_PATH environment variables must be set."
        )

    builder = IndexBuilder(embedding_path, index_path, metadata_path)
    builder.build_index()


def run_query(image_path: str) -> None:
    index_path = os.getenv("FAISS_INDEX_PATH")
    metadata_path = os.getenv("FAISS_METADATA_PATH")
    u2net_model_path = os.getenv("U2NET_MODEL_PATH")
    augmentation_map_path = os.getenv("AUGMENTATION_MAP_PATH")

    if not index_path or not metadata_path or not u2net_model_path or not augmentation_map_path:
        raise ValueError(
            "FAISS_INDEX_PATH, FAISS_METADATA_PATH, U2NET_MODEL_PATH, and AUGMENTATION_MAP_PATH environment variables must be set."
        )

    loader = IndexLoader(index_path, metadata_path)
    loader.load()

    querier = ImageQuerier(
        index=loader.index,
        metadata=loader.metadata,
        u2net_model_path=u2net_model_path,
        augmentation_map_path=augmentation_map_path,
    )

    results = querier.query(image_path=image_path)

    print("Aggregated Top Matches:")
    for result in results:
        print(
            f"Original: {result['original_image']}, "
            f"Count: {result['match_count']}, "
            f"Mean Distance: {result['mean_distance']:.4f}, "
            f"Min Distance: {result['min_distance']:.4f}"
        )


def run_download_bg_model():
    download_u2net_model()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beer cap matcher CLI.")
    parser.add_argument("--download-bg-model", action="store_true", help="Download the U²-Net background removal model")
    parser.add_argument("--augment", action="store_true", help="Enable generation of augmented pictures")
    parser.add_argument("--generate-embeddings", action="store_true", help="Enable generation of embeddings")
    parser.add_argument("--index", action="store_true", help="Enable indexing of pictures")
    parser.add_argument("--query", type=str, help="Path to image for querying the index")
    args = parser.parse_args()

    if args.download_bg_model:
        run_download_bg_model()

    if args.augment:
        run_augmentation()

    if args.generate_embeddings:
        run_embedding_generation()

    if args.index:
        run_indexing()

    if args.query:
        run_query(args.query)
