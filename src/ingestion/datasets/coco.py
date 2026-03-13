"""
COCO Dataset Downloader.

Downloads COCO (Common Objects in Context) dataset for image embedding benchmarking.
"""

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List
import time

from PIL import Image

from src.ingestion.datasets import register_dataset
from src.ingestion.datasets.base import DatasetDownloader, DownloadConfig, DatasetMetadata
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@register_dataset('coco')
class COCODownloader(DatasetDownloader):
    """Downloader for COCO dataset."""

    DATASET_NAME = "coco"
    MODALITY = "image"
    DESCRIPTION = "COCO - Common Objects in Context image dataset"
    LICENSE = "CC-BY 4.0"
    RECOMMENDED_SIZE = 100000

    # Dataset URLs
    TRAIN_IMAGES_URL = "http://images.cocodataset.org/zips/train2017.zip"
    VAL_IMAGES_URL = "http://images.cocodataset.org/zips/val2017.zip"
    ANNOTATIONS_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"

    def __init__(self, config: DownloadConfig):
        """Initialize COCO downloader."""
        super().__init__(config)
        self.train_images_path = self.output_dir / "train2017.zip"
        self.val_images_path = self.output_dir / "val2017.zip"
        self.annotations_path = self.output_dir / "annotations_trainval2017.zip"
        self.train_dir = self.output_dir / "train2017"
        self.val_dir = self.output_dir / "val2017"
        self.annotations_dir = self.output_dir / "annotations"

    async def download(self) -> DatasetMetadata:
        """Download COCO dataset."""
        start_time = time.time()
        logger.info(f"Starting COCO download to {self.output_dir}")

        # Determine which split to download based on max_items
        max_items = self.config.max_items or 100000

        # Download strategy:
        # - If max_items <= 5000: download val only (5K images)
        # - If max_items > 5000: download train (118K images)
        # - Always download annotations

        download_tasks = [
            self.download_file(self.ANNOTATIONS_URL, self.annotations_path)
        ]

        if max_items <= 5000:
            logger.info("Downloading validation set only (5K images)")
            download_tasks.append(
                self.download_file(self.VAL_IMAGES_URL, self.val_images_path)
            )
            primary_split = "val"
        else:
            logger.info("Downloading training set (118K images)")
            download_tasks.append(
                self.download_file(self.TRAIN_IMAGES_URL, self.train_images_path)
            )
            primary_split = "train"

        success = await asyncio.gather(*download_tasks)

        if not all(success):
            raise RuntimeError("Failed to download one or more COCO files")

        # Extract archives
        logger.info("Extracting archives...")
        self.extract_archive(self.annotations_path, self.output_dir)

        if primary_split == "val":
            self.extract_archive(self.val_images_path, self.output_dir)
            images_dir = self.val_dir
        else:
            self.extract_archive(self.train_images_path, self.output_dir)
            images_dir = self.train_dir

        # Count images
        total_items = sum(1 for _ in images_dir.glob('*.jpg'))
        downloaded_items = min(total_items, max_items)

        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in images_dir.glob('*.jpg')
        )

        download_time = time.time() - start_time

        metadata = DatasetMetadata(
            dataset_name=self.DATASET_NAME,
            modality=self.MODALITY,
            total_items=total_items,
            downloaded_items=downloaded_items,
            failed_items=0,
            total_size_bytes=total_size,
            download_time_seconds=download_time,
            output_directory=self.output_dir
        )

        logger.info(f"COCO download complete: {downloaded_items} images in {download_time:.2f}s")
        return metadata

    async def stream_items(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream COCO images with annotations.

        Yields:
            Dict with image_path, image_id, captions, annotations
        """
        # Load annotations
        annotations = self._load_annotations()

        # Determine which split to use
        if self.val_dir.exists() and list(self.val_dir.glob('*.jpg')):
            images_dir = self.val_dir
            split = "val"
        else:
            images_dir = self.train_dir
            split = "train"

        logger.info(f"Streaming COCO {split} split from {images_dir}")

        count = 0
        max_items = self.config.max_items or float('inf')

        for image_path in sorted(images_dir.glob('*.jpg')):
            if count >= max_items:
                break

            image_id = int(image_path.stem)

            # Get annotations for this image
            image_annotations = annotations['images'].get(image_id, {})
            captions = annotations['captions'].get(image_id, [])
            objects = annotations['objects'].get(image_id, [])

            item = {
                'image_path': str(image_path),
                'image_id': image_id,
                'file_name': image_path.name,
                'width': image_annotations.get('width', 0),
                'height': image_annotations.get('height', 0),
                'captions': captions,
                'objects': objects,
                'split': split,
                'modality': 'image'
            }

            if self.validate_item(item):
                yield item
                count += 1

                if count % 1000 == 0:
                    logger.info(f"Streamed {count} images")

        logger.info(f"Finished streaming {count} images")

    def _load_annotations(self) -> Dict[str, Any]:
        """Load COCO annotations."""
        annotations = {
            'images': {},
            'captions': {},
            'objects': {}
        }

        # Determine annotation files to load
        captions_file = self.annotations_dir / "captions_train2017.json"
        instances_file = self.annotations_dir / "instances_train2017.json"

        if not captions_file.exists():
            captions_file = self.annotations_dir / "captions_val2017.json"
            instances_file = self.annotations_dir / "instances_val2017.json"

        # Load captions
        if captions_file.exists():
            logger.info(f"Loading captions from {captions_file}")
            with open(captions_file, 'r') as f:
                data = json.load(f)

                # Index images
                for img in data.get('images', []):
                    annotations['images'][img['id']] = img

                # Index captions by image_id
                for ann in data.get('annotations', []):
                    image_id = ann['image_id']
                    if image_id not in annotations['captions']:
                        annotations['captions'][image_id] = []
                    annotations['captions'][image_id].append(ann['caption'])

        # Load instance annotations (object detections)
        if instances_file.exists():
            logger.info(f"Loading instances from {instances_file}")
            with open(instances_file, 'r') as f:
                data = json.load(f)

                # Build category lookup
                categories = {cat['id']: cat['name'] for cat in data.get('categories', [])}

                # Index objects by image_id
                for ann in data.get('annotations', []):
                    image_id = ann['image_id']
                    if image_id not in annotations['objects']:
                        annotations['objects'][image_id] = []

                    annotations['objects'][image_id].append({
                        'category': categories.get(ann['category_id'], 'unknown'),
                        'bbox': ann.get('bbox', []),
                        'area': ann.get('area', 0)
                    })

        logger.info(f"Loaded annotations for {len(annotations['images'])} images")
        return annotations

    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate COCO image."""
        image_path = Path(item['image_path'])

        # Check file exists
        if not image_path.exists():
            return False

        # Check file size (should be at least 1KB)
        if image_path.stat().st_size < 1024:
            return False

        # Optional: Verify image can be opened
        try:
            with Image.open(image_path) as img:
                # Check dimensions
                if img.width < 64 or img.height < 64:
                    return False
        except Exception as e:
            logger.warning(f"Failed to validate image {image_path}: {e}")
            return False

        return True

    def get_preprocessing_config(self) -> Dict[str, Any]:
        """Get recommended preprocessing configuration."""
        return {
            'resize_dimensions': (384, 384),
            'resize_mode': 'pad',  # Maintain aspect ratio with padding
            'normalization': 'imagenet',  # ImageNet mean/std
            'format': 'RGB',
            'description': 'Resize to 384x384 with padding, ImageNet normalization'
        }

    def get_embedding_strategy(self) -> Dict[str, Any]:
        """Get recommended embedding strategy."""
        return {
            'model': 'amazon.titan-embed-image-v1',
            'dimension': 1024,
            'input_format': 'jpeg',
            'batch_size': 32,
            'description': 'Amazon Titan Multimodal Embeddings'
        }
