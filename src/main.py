import argparse
from dotenv import load_dotenv
from src.preprocessing.image_processor import ImageAugmenter
from src.embeddings.embedding_generator import EmbeddingGenerator
import os

load_dotenv()


def run_augmentation():
    raw_data_dir = os.getenv("RAW_DATA_DIR")
    augmented_data_dir = os.getenv("AUGMENTED_DATA_DIR")
    if raw_data_dir is None or augmented_data_dir is None:
        raise ValueError("RAW_DATA_DIR and AUGMENTED_DATA_DIR environment variables must be set.")

    augmenter = ImageAugmenter(
        input_dir=raw_data_dir,
        output_dir=augmented_data_dir,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beer cap matcher CLI.")
    parser.add_argument("--augment", action="store_true", help="Enable generation of augmented pictures")
    parser.add_argument("--generate-embeddings", action="store_true", help="Enable generation of embeddings")
    parser.add_argument("--index", action="store_true", help="Enable indexing of pictures")
    parser.add_argument("--update", action="store_true", help="Enable updating of the index")
    args = parser.parse_args()

    if args.augment:
        run_augmentation()

    if args.generate_embeddings:
        run_embedding_generation()
