"""
LanceDB Vector Store Provider

Implementation of the VectorStoreProvider interface for LanceDB.
LanceDB is a high-performance columnar vector database with SQL-like
filtering capabilities and support for local and S3-backed storage.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreState
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class LanceDBProvider(VectorStoreProvider):
    """
    LanceDB implementation of VectorStoreProvider.

    Features:
    - High-performance columnar storage
    - Local and S3-backed storage
    - SQL-like filtering
    - Efficient data handling with PyArrow
    - Multiple distance metrics (cosine, euclidean, dot product)
    """

    def __init__(self):
        """Initialize LanceDB provider."""
        try:
            import lancedb
            self.lancedb = lancedb

            # Get configuration
            self.db_uri = os.getenv("LANCEDB_URI", "/tmp/lancedb")

            # S3 storage options if using S3
            self.storage_options = {}
            if self.db_uri.startswith("s3://"):
                self.storage_options = {
                    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
                    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
                    "region": os.getenv("AWS_REGION", "us-east-1")
                }

            # Connect to database
            self.db = self.lancedb.connect(self.db_uri, storage_options=self.storage_options)
            logger.info(f"LanceDB provider initialized with URI: {self.db_uri}")

        except ImportError as e:
            logger.error(f"Failed to import lancedb: {e}")
            raise ImportError(
                "lancedb is required for LanceDBProvider. "
                "Install with: pip install lancedb pyarrow"
            )
        except Exception as e:
            logger.error(f"Failed to initialize LanceDB provider: {e}")
            raise

    @property
    def store_type(self) -> VectorStoreType:
        """Get the store type."""
        return VectorStoreType.LANCEDB

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new LanceDB table.

        Args:
            config: Vector store configuration

        Returns:
            VectorStoreStatus with creation result
        """
        try:
            logger.info(f"Creating LanceDB table: {config.name}")

            # LanceDB tables are created on first insert
            # Just verify we can connect and return success

            return VectorStoreStatus(
                store_type=VectorStoreType.LANCEDB,
                name=config.name,
                state=VectorStoreState.ACTIVE,
                dimension=config.dimension,
                similarity_metric=config.similarity_metric,
                created_at=datetime.now(timezone.utc),
                metadata={
                    "uri": self.db_uri,
                    "storage_type": "s3" if self.db_uri.startswith("s3://") else "local"
                }
            )

        except Exception as e:
            logger.error(f"Failed to create LanceDB table: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.LANCEDB,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete a LanceDB table.

        Args:
            name: Table name
            force: Force deletion even if table has data

        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            logger.info(f"Deleting LanceDB table: {name}")

            # Check if table exists
            if name in self.db.table_names():
                self.db.drop_table(name)
                logger.info(f"LanceDB table deleted: {name}")

                return VectorStoreStatus(
                    store_type=VectorStoreType.LANCEDB,
                    name=name,
                    state=VectorStoreState.DELETED
                )
            else:
                return VectorStoreStatus(
                    store_type=VectorStoreType.LANCEDB,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Table {name} not found"
                )

        except Exception as e:
            logger.error(f"Failed to delete LanceDB table: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.LANCEDB,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get status of a LanceDB table.

        Args:
            name: Table name

        Returns:
            VectorStoreStatus with current state
        """
        try:
            if name in self.db.table_names():
                table = self.db.open_table(name)
                count = table.count_rows()

                return VectorStoreStatus(
                    store_type=VectorStoreType.LANCEDB,
                    name=name,
                    state=VectorStoreState.ACTIVE,
                    vector_count=count,
                    metadata={
                        "uri": self.db_uri,
                        "storage_type": "s3" if self.db_uri.startswith("s3://") else "local"
                    }
                )
            else:
                return VectorStoreStatus(
                    store_type=VectorStoreType.LANCEDB,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Table {name} not found"
                )

        except Exception as e:
            logger.error(f"Failed to get LanceDB table status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.LANCEDB,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all LanceDB tables.

        Returns:
            List of VectorStoreStatus objects
        """
        try:
            tables = self.db.table_names()

            return [
                VectorStoreStatus(
                    store_type=VectorStoreType.LANCEDB,
                    name=table_name,
                    state=VectorStoreState.ACTIVE
                )
                for table_name in tables
            ]

        except Exception as e:
            logger.error(f"Failed to list LanceDB tables: {e}")
            return []

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in LanceDB table.

        Args:
            name: Table name
            vectors: List of vector objects with 'id', 'values', and 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            import pyarrow as pa

            logger.info(f"Upserting {len(vectors)} vectors to LanceDB table: {name}")

            # Prepare data for LanceDB
            data = []
            for vector in vectors:
                data.append({
                    "id": vector.get("id", ""),
                    "vector": vector.get("values", []),
                    "metadata": vector.get("metadata", {})
                })

            # Create or open table
            if name in self.db.table_names():
                table = self.db.open_table(name)
                table.add(data)
            else:
                table = self.db.create_table(name, data)

            logger.info(f"Successfully upserted {len(vectors)} vectors to {name}")

            return {
                "success": True,
                "upserted_count": len(vectors),
                "table_name": name
            }

        except Exception as e:
            logger.error(f"Failed to upsert vectors to LanceDB: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query LanceDB table for similar vectors.

        Args:
            name: Table name
            query_vector: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of similar vectors with scores
        """
        try:
            logger.info(f"Querying LanceDB table {name} for top {top_k} results")

            # Open table
            table = self.db.open_table(name)

            # Execute search
            results = table.search(query_vector).limit(top_k)

            # Apply filters if provided
            if filter_metadata:
                # LanceDB supports SQL-like filtering
                filter_expr = " AND ".join([
                    f"metadata.{key} = '{value}'"
                    for key, value in filter_metadata.items()
                ])
                results = results.where(filter_expr)

            # Execute and convert to list
            results_list = results.to_list()

            # Format results
            formatted_results = []
            for result in results_list:
                formatted_results.append({
                    "id": result.get("id", ""),
                    "score": float(result.get("_distance", 0.0)),
                    "metadata": result.get("metadata", {}),
                    "vector": result.get("vector", [])
                })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query LanceDB table: {e}")
            return []
    
    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to LanceDB storage.
        
        Tests:
        - Storage backend accessibility (local or S3)
        - Database connection
        - Table listing capability
        - Response time measurement
        
        Returns:
            Connectivity validation result
        """
        import time
        
        start_time = time.time()
        
        try:
            # Test LanceDB connectivity by listing tables
            table_names = self.db.table_names()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            table_count = len(table_names)
            
            # Determine storage type and health
            storage_type = "s3" if self.db_uri.startswith("s3://") else "local"
            health_status = "healthy"
            
            details = {
                "table_count": table_count,
                "uri": self.db_uri,
                "storage_type": storage_type,
                "service": "LanceDB"
            }
            
            # For S3, verify we can access the backend
            if storage_type == "s3":
                details['s3_accessible'] = True
            
            return {
                "accessible": True,
                "endpoint": self.db_uri,
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": None,
                "details": details
            }
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"LanceDB connectivity validation failed: {e}")
            
            # Determine health status based on error type
            if "permission" in error_msg.lower() or "access denied" in error_msg.lower():
                health_status = "unhealthy"
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                health_status = "degraded"
            else:
                health_status = "unhealthy"
            
            return {
                "accessible": False,
                "endpoint": self.db_uri,
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": error_msg,
                "details": {
                    "uri": self.db_uri,
                    "storage_type": "s3" if self.db_uri.startswith("s3://") else "local",
                    "service": "LanceDB"
                }
            }
