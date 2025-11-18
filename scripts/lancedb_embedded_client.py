#!/usr/bin/env python3
"""Minimal embedded LanceDB client for S3 / EFS / EBS storage.

This module provides a thin, benchmark-friendly wrapper around the
LanceDBEmbeddedAdapter used by the benchmarking harness. It exposes a simple
Python API to:

- Connect to LanceDB via a URI (S3, EFS, EBS/local path)
- Index vectors + metadata into a table
- Run similarity search queries

Storage options are all expressed via the LanceDB URI:

- S3:  "s3://<bucket>[/optional/prefix]"
- EFS: "/mnt/<efs-mount>" (file system path)
- EBS: "/mnt/lancedb" (or any local path)

This client is intended for *embedding client level benchmarks* where you want
embedded LanceDB performance numbers without going through the FastAPI wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from scripts.backend_adapters import LanceDBEmbeddedAdapter


@dataclass
class LanceDBEmbeddedClient:
    """Minimal embedded LanceDB client.

    Parameters
    ----------
    uri:
        LanceDB connection URI. For example:
        - "s3://my-lancedb-bucket"
        - "/mnt/lancedb_efs"
        - "/mnt/lancedb" (EBS on the lancedb-ebs EC2 instance)
    backend_name:
        Logical backend label used only for benchmark metadata. Examples:
        - "lancedb-s3-embedded"
        - "lancedb-efs-embedded"
        - "lancedb-ebs-embedded"
    """

    uri: str
    backend_name: str = "lancedb-embedded"

    def __post_init__(self) -> None:
        # Reuse the existing adapter implementation so behavior stays in sync
        # with the benchmark harness.
        self._adapter = LanceDBEmbeddedAdapter(uri=self.uri, backend_name=self.backend_name)

    # ------------------------------------------------------------------
    # Convenience constructors for each storage option
    # ------------------------------------------------------------------
    @classmethod
    def for_s3(
        cls,
        bucket: str,
        prefix: str = "",
        backend_name: str = "lancedb-s3-embedded",
    ) -> "LanceDBEmbeddedClient":
        """Create a client for S3-backed LanceDB.

        Examples
        --------
        >>> client = LanceDBEmbeddedClient.for_s3("my-lancedb-bucket")
        >>> client = LanceDBEmbeddedClient.for_s3("my-bucket", prefix="lancedb/")
        """
        uri = f"s3://{bucket}"
        if prefix:
            # Avoid double slashes
            uri = uri.rstrip("/") + "/" + prefix.lstrip("/")
        return cls(uri=uri, backend_name=backend_name)

    @classmethod
    def for_local_path(
        cls,
        path: str,
        backend_name: str = "lancedb-embedded",
    ) -> "LanceDBEmbeddedClient":
        """Create a client for a local/posix path (EFS / EBS / local disk)."""
        return cls(uri=path, backend_name=backend_name)

    @classmethod
    def for_efs(
        cls,
        mount_path: str = "/mnt/lancedb_efs",
        backend_name: str = "lancedb-efs-embedded",
    ) -> "LanceDBEmbeddedClient":
        """Create a client for an EFS-backed LanceDB deployment."""
        return cls.for_local_path(path=mount_path, backend_name=backend_name)

    @classmethod
    def for_ebs(
        cls,
        mount_path: str = "/mnt/lancedb",
        backend_name: str = "lancedb-ebs-embedded",
    ) -> "LanceDBEmbeddedClient":
        """Create a client for an EBS-backed LanceDB deployment."""
        return cls.for_local_path(path=mount_path, backend_name=backend_name)

    # ------------------------------------------------------------------
    # Basic operations
    # ------------------------------------------------------------------
    def health_check(self) -> bool:
        """Return True if the underlying LanceDB connection is healthy."""
        return self._adapter.health_check()

    def index_vectors(
        self,
        table_name: str,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        *,
        mode: str = "overwrite",
    ) -> Dict[str, Any]:
        """Index vectors into a LanceDB table.

        Parameters
        ----------
        table_name:
            Name of the LanceDB table.
        vectors:
            List of embedding vectors (list of floats).
        metadata:
            List of metadata dicts aligned with `vectors`.
        mode:
            Currently the underlying adapter always overwrites the table to
            keep benchmarks deterministic; `mode` is accepted for future
            extension but ignored.
        """
        return self._adapter.index_vectors(vectors, metadata, collection=table_name)

    def search(
        self,
        table_name: str,
        query_vector: List[float],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Run a similarity search against a LanceDB table.

        Returns a list of dicts representing rows from the LanceDB table.
        """
        return self._adapter.search_vectors(query_vector, top_k, collection=table_name)

    # Convenience alias matching benchmark adapter naming
    search_vectors = search

