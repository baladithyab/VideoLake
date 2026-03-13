"""
MS MARCO Dataset Downloader.

Downloads MS MARCO Document Ranking dataset for text embedding benchmarking.
"""

import asyncio
import gzip
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Any
import time

from src.ingestion.datasets import register_dataset
from src.ingestion.datasets.base import DatasetDownloader, DownloadConfig, DatasetMetadata
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@register_dataset('msmarco')
class MSMARCODownloader(DatasetDownloader):
    """Downloader for MS MARCO Document Ranking dataset."""

    DATASET_NAME = "msmarco"
    MODALITY = "text"
    DESCRIPTION = "MS MARCO Document Ranking - Large-scale information retrieval dataset"
    LICENSE = "Microsoft Research License"
    RECOMMENDED_SIZE = 100000

    # Dataset URLs
    DOCUMENTS_URL = "https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docs.tsv.gz"
    DOCS_LOOKUP_URL = "https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docs-lookup.tsv.gz"
    QUERIES_URL = "https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docdev-queries.tsv.gz"

    def __init__(self, config: DownloadConfig):
        """Initialize MS MARCO downloader."""
        super().__init__(config)
        self.documents_path = self.output_dir / "msmarco-docs.tsv.gz"
        self.lookup_path = self.output_dir / "msmarco-docs-lookup.tsv.gz"
        self.queries_path = self.output_dir / "msmarco-docdev-queries.tsv.gz"

    async def download(self) -> DatasetMetadata:
        """Download MS MARCO dataset."""
        start_time = time.time()
        logger.info(f"Starting MS MARCO download to {self.output_dir}")

        # Download main files
        success = await asyncio.gather(
            self.download_file(self.DOCUMENTS_URL, self.documents_path),
            self.download_file(self.DOCS_LOOKUP_URL, self.lookup_path),
            self.download_file(self.QUERIES_URL, self.queries_path),
        )

        if not all(success):
            raise RuntimeError("Failed to download one or more MS MARCO files")

        # Count items
        total_items = await self._count_documents()
        downloaded_items = min(total_items, self.config.max_items or total_items)

        # Calculate total size
        total_size = sum(
            p.stat().st_size
            for p in [self.documents_path, self.lookup_path, self.queries_path]
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

        logger.info(f"MS MARCO download complete: {downloaded_items} documents in {download_time:.2f}s")
        return metadata

    async def _count_documents(self) -> int:
        """Count total documents in dataset."""
        count = 0
        try:
            with gzip.open(self.documents_path, 'rt', encoding='utf-8') as f:
                for _ in f:
                    count += 1
                    if count % 100000 == 0:
                        logger.info(f"Counted {count} documents...")
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0

        return count

    async def stream_items(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream MS MARCO documents.

        Yields:
            Dict with doc_id, url, title, body
        """
        if not self.documents_path.exists():
            raise FileNotFoundError(f"Documents file not found: {self.documents_path}")

        # Load lookup table for URLs
        lookup = {}
        try:
            with gzip.open(self.lookup_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        lookup[parts[0]] = parts[1]
        except Exception as e:
            logger.warning(f"Failed to load lookup table: {e}")

        # Stream documents
        count = 0
        max_items = self.config.max_items or float('inf')

        with gzip.open(self.documents_path, 'rt', encoding='utf-8') as f:
            for line in f:
                if count >= max_items:
                    break

                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    doc_id = parts[0]
                    url = lookup.get(doc_id, parts[1])
                    title = parts[2]
                    body = parts[3]

                    item = {
                        'doc_id': doc_id,
                        'url': url,
                        'title': title,
                        'body': body,
                        'text': f"{title}\n\n{body}",  # Combined text for embedding
                        'modality': 'text'
                    }

                    if self.validate_item(item):
                        yield item
                        count += 1

                    if count % 10000 == 0:
                        logger.info(f"Streamed {count} documents")

        logger.info(f"Finished streaming {count} documents")

    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate MS MARCO document."""
        if not item.get('doc_id') or not item.get('text'):
            return False

        # Check text length (should have meaningful content)
        if len(item['text'].strip()) < 50:
            return False

        return True

    async def stream_queries(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream MS MARCO queries.

        Yields:
            Dict with query_id and query_text
        """
        if not self.queries_path.exists():
            raise FileNotFoundError(f"Queries file not found: {self.queries_path}")

        count = 0
        with gzip.open(self.queries_path, 'rt', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    query_id = parts[0]
                    query_text = parts[1]

                    item = {
                        'query_id': query_id,
                        'query_text': query_text,
                        'text': query_text,
                        'modality': 'text'
                    }

                    yield item
                    count += 1

                    if count % 1000 == 0:
                        logger.info(f"Streamed {count} queries")

        logger.info(f"Finished streaming {count} queries")

    def get_chunking_strategy(self) -> Dict[str, Any]:
        """Get recommended chunking strategy for MS MARCO."""
        return {
            'method': 'semantic_paragraph',
            'chunk_size_tokens': 512,
            'overlap_tokens': 50,
            'expected_chunks_per_doc': 2.0,
            'description': 'Split documents into semantic paragraphs with overlap'
        }
