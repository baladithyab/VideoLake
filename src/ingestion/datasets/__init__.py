"""
Dataset Downloaders for Benchmark Data Ingestion.

Provides downloaders for recommended datasets:
- MS MARCO (text)
- COCO (image)
- LibriSpeech (audio)
- MSR-VTT (video)
"""

from typing import Dict, Type
from src.ingestion.datasets.base import DatasetDownloader

# Registry will be populated after importing specific downloaders
DATASET_REGISTRY: Dict[str, Type[DatasetDownloader]] = {}


def register_dataset(name: str):
    """Decorator to register dataset downloader."""
    def decorator(cls):
        DATASET_REGISTRY[name] = cls
        return cls
    return decorator


def get_downloader(dataset_name: str) -> Type[DatasetDownloader]:
    """Get downloader class by name."""
    if dataset_name not in DATASET_REGISTRY:
        raise ValueError(
            f"Unknown dataset: {dataset_name}. "
            f"Available: {list(DATASET_REGISTRY.keys())}"
        )
    return DATASET_REGISTRY[dataset_name]


def list_datasets() -> Dict[str, Dict[str, str]]:
    """List all available datasets with metadata."""
    datasets = {}
    for name, downloader_cls in DATASET_REGISTRY.items():
        datasets[name] = {
            'name': name,
            'modality': downloader_cls.MODALITY,
            'description': downloader_cls.DESCRIPTION,
            'license': downloader_cls.LICENSE
        }
    return datasets


# Import specific downloaders to populate registry
from src.ingestion.datasets.msmarco import MSMARCODownloader
from src.ingestion.datasets.coco import COCODownloader
from src.ingestion.datasets.librispeech import LibriSpeechDownloader
from src.ingestion.datasets.msrvtt import MSRVTTDownloader

__all__ = [
    'DatasetDownloader',
    'MSMARCODownloader',
    'COCODownloader',
    'LibriSpeechDownloader',
    'MSRVTTDownloader',
    'get_downloader',
    'list_datasets',
    'register_dataset',
    'DATASET_REGISTRY'
]
