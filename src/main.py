import argparse
from pathlib import Path
from typing import List, Optional

from src.cap_detection.embedding_generator import EmbeddingGenerator
from src.cap_detection.image_querier import AggregatedResult, ImageQuerier
from src.cap_detection.index_builder import IndexBuilder
from src.cap_detection.indexer.index_loader import IndexLoader
from src.cap_detection.preprocessing.image_processor import ImageAugmenter
from src.config.settings import settings
from src.scripts.download_u2net import download_u2net_model
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BeerCapMatcherApp:
    def __init__(self, initialize_all: bool = True):
        logger.info("Initializing BeerCapMatcherApp...")

        self.raw_data_dir = settings.raw_data_dir
        self.augmented_data_dir = settings.augmented_data_dir
        self.u2net_model_path = settings.u2net_model_path
        self.augmentation_map_path = settings.augmentation_map_path
        self.embeddings_output_path = settings.embeddings_output_path
        self.faiss_index_path = settings.faiss_index_path
        self.faiss_metadata_path = settings.faiss_metadata_path
        self.augmentations_per_image = settings.augmentations_per_image

        self.augmenter: Optional[ImageAugmenter] = None
        self.embedding_generator: Optional[EmbeddingGenerator] = None
        self.index_loader: Optional[IndexLoader] = None
        self.querier: Optional[ImageQuerier] = None

        if initialize_all:
            self._initialize_augmenter()

    def _initialize_augmenter(self):
        if not Path(self.u2net_model_path).exists():
            logger.warning("U2NET model not found. Augmenter initialization skipped.")
            return

        self.augmenter = ImageAugmenter(
            input_dir=Path(self.raw_data_dir),
            output_dir=Path(self.augmented_data_dir),
            u2net_model_path=Path(self.u2net_model_path),
            augmentation_map_path=Path(self.augmentation_map_path),
            augmentations_per_image=self.augmentations_per_image,
        )

    def run_download_bg_model(self):
        download_u2net_model()

    def run_augmentation(self):
        if self.augmenter is None:
            self._initialize_augmenter()
        if self.augmenter:
            logger.info("Running augmentation pipeline...")
            self.augmenter.augment_and_save()
        else:
            logger.error("Cannot run augmentation. U2NET model is missing.")

    def run_embedding_generation(self):
        logger.info("Running embedding generation pipeline...")
        self.embedding_generator = EmbeddingGenerator(
            image_dir=self.augmented_data_dir,
            output_path=self.embeddings_output_path,
        )
        self.embedding_generator.generate_embeddings()

    def run_indexing(self):
        logger.info("Running index building pipeline...")
        builder = IndexBuilder(
            embedding_path=self.embeddings_output_path,
            index_path=self.faiss_index_path,
            metadata_path=self.faiss_metadata_path,
        )
        builder.build_index()

    def run_query(self, image_path: str, top_k: int = 5):
        logger.info(f"Running query for image: {image_path}")

        if self.index_loader is None:
            self.index_loader = IndexLoader(self.faiss_index_path, self.faiss_metadata_path)
            self.index_loader.load()

        if self.querier is None:
            self.querier = ImageQuerier(
                index=self.index_loader.index,
                metadata=self.index_loader.metadata,
                u2net_model_path=self.u2net_model_path,
                augmentation_map_path=self.augmentation_map_path,
            )

        results: List[AggregatedResult] = self.querier.query(image_path=image_path, top_k=top_k)
        self._print_results(results)
        return results

    def _print_results(self, results: List[AggregatedResult]):
        print("Aggregated Top Matches:")
        for r in results:
            print(
                f"{r.original_image}: mean={r.mean_distance:.4f}, "
                f"min={r.min_distance:.4f}, max={r.max_distance:.4f}, count={r.match_count}"
            )

    def repl(self):
        logger.info("Entering REPL mode. Type 'help' for commands.")
        while True:
            cmd = input("BeerCapMatcher> ").strip()
            if cmd in ["exit", "quit"]:
                break
            elif cmd == "help":
                print("Commands: augment, generate_embeddings, index, query <image_path>, exit")
            elif cmd == "augment":
                self.run_augmentation()
            elif cmd == "generate_embeddings":
                self.run_embedding_generation()
            elif cmd == "index":
                self.run_indexing()
            elif cmd.startswith("query "):
                _, path = cmd.split(" ", 1)
                self.run_query(path)
            else:
                print("Unknown command. Type 'help'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Beer cap matcher CLI.")
    parser.add_argument("--download-bg-model", action="store_true", help="Download the U²-Net background removal model")
    parser.add_argument("--augment", action="store_true", help="Generate augmented images")
    parser.add_argument("--generate-embeddings", action="store_true", help="Generate image embeddings")
    parser.add_argument("--index", action="store_true", help="Build the FAISS index")
    parser.add_argument("--query", type=str, help="Path to image for querying the index")
    parser.add_argument("--repl", action="store_true", help="Run in interactive REPL mode")
    args = parser.parse_args()

    initialize_all = not args.download_bg_model
    app = BeerCapMatcherApp(initialize_all=initialize_all)

    if args.download_bg_model:
        app.run_download_bg_model()
    if args.augment:
        app.run_augmentation()
    if args.generate_embeddings:
        app.run_embedding_generation()
    if args.index:
        app.run_indexing()
    if args.query:
        app.run_query(args.query)
    if args.repl:
        app.repl()
