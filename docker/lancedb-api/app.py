"""
LanceDB API Wrapper - FastAPI REST API for LanceDB operations
Supports both S3 and local filesystem storage backends
"""
import os
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import lancedb
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")  # "s3" or "local"
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")
LOCAL_DATA_PATH = os.getenv("DATA_PATH", "/data")

# Global database connection
db_connection = None


def get_db_uri() -> str:
    """Get LanceDB URI based on storage type"""
    if STORAGE_TYPE == "s3":
        if not S3_BUCKET:
            raise ValueError("S3_BUCKET environment variable must be set for S3 storage")
        uri = f"s3://{S3_BUCKET}/lancedb"
        logger.info(f"Using S3 storage: {uri}")
    else:
        uri = LOCAL_DATA_PATH
        logger.info(f"Using local storage: {uri}")
    return uri


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - initialize DB connection on startup"""
    global db_connection
    try:
        db_uri = get_db_uri()
        db_connection = lancedb.connect(db_uri)
        logger.info(f"LanceDB connection established to: {db_uri}")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize LanceDB: {e}")
        raise
    finally:
        # Cleanup if needed
        db_connection = None
        logger.info("LanceDB connection closed")


# Initialize FastAPI app
app = FastAPI(
    title="LanceDB API",
    description="REST API wrapper for LanceDB vector database operations",
    version="1.0.0",
    lifespan=lifespan
)


# Request/Response Models
class HealthResponse(BaseModel):
    status: str
    storage_type: str
    storage_uri: str
    tables_count: int


class TableInfo(BaseModel):
    name: str
    table_schema: Optional[Dict[str, Any]] = None


class CreateIndexRequest(BaseModel):
    table_name: str = Field(..., description="Name of the table to create/update")
    data: List[Dict[str, Any]] = Field(..., description="List of records to insert")
    mode: str = Field(default="overwrite", description="'create', 'overwrite', or 'append'")


class SearchRequest(BaseModel):
    table_name: str = Field(..., description="Name of the table to search")
    query_vector: List[float] = Field(..., description="Query embedding vector")
    limit: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    metric: str = Field(default="cosine", description="Distance metric: 'cosine', 'l2', or 'dot'")
    filter: Optional[str] = Field(default=None, description="SQL-like filter expression")


class SearchResult(BaseModel):
    results: List[Dict[str, Any]]
    count: int


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Fast health check endpoint for ECS/container orchestration
    Returns operational status without expensive operations
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")

        # Fast health check - just verify connection is alive
        # Avoid listing tables on every health check (expensive for S3/EFS)
        return HealthResponse(
            status="healthy",
            storage_type=STORAGE_TYPE,
            storage_uri=get_db_uri(),
            tables_count=0  # Set to 0 to avoid expensive table listing
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/tables", response_model=List[str])
async def list_tables():
    """
    List all available LanceDB tables
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")
        
        tables = list(db_connection.table_names())
        logger.info(f"Retrieved {len(tables)} tables")
        return tables
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")


@app.get("/tables/{table_name}", response_model=TableInfo)
async def get_table_info(table_name: str):
    """
    Get information about a specific table
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")
        
        if table_name not in db_connection.table_names():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        table = db_connection.open_table(table_name)
        schema = table.schema
        
        return TableInfo(
            name=table_name,
            table_schema={"fields": [{"name": field.name, "type": str(field.type)} for field in schema]}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {str(e)}")


@app.post("/index")
async def create_or_update_index(request: CreateIndexRequest):
    """
    Create or update a LanceDB table with vector data
    Supports create, overwrite, and append modes
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")
        
        if not request.data:
            raise HTTPException(status_code=400, detail="Data cannot be empty")
        
        # Convert data to DataFrame
        df = pd.DataFrame(request.data)
        
        # Validate that vector column exists
        if "vector" not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="Data must contain a 'vector' column with embedding vectors"
            )
        
        # Determine operation mode
        table_exists = request.table_name in db_connection.table_names()
        
        if request.mode == "create" and table_exists:
            raise HTTPException(
                status_code=409,
                detail=f"Table '{request.table_name}' already exists. Use 'overwrite' or 'append' mode."
            )
        
        if request.mode == "overwrite" or not table_exists:
            # Create new table or overwrite existing
            table = db_connection.create_table(request.table_name, data=df, mode="overwrite")
            operation = "created" if not table_exists else "overwritten"
        else:
            # Append to existing table
            table = db_connection.open_table(request.table_name)
            table.add(df)
            operation = "appended"
        
        logger.info(f"Table '{request.table_name}' {operation} with {len(df)} records")
        
        return {
            "status": "success",
            "operation": operation,
            "table_name": request.table_name,
            "records_processed": len(df)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create/update index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create/update index: {str(e)}")


@app.post("/search", response_model=SearchResult)
async def vector_search(request: SearchRequest):
    """Perform vector similarity search on a LanceDB table.

    Optimized for maximum performance - minimal validation, direct search execution.
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")

        # Fast path: open table and search immediately
        # Table existence check happens implicitly in open_table
        table = db_connection.open_table(request.table_name)

        # Build and execute search query in one go
        search = table.search(request.query_vector).limit(request.limit)

        # Apply filter if provided
        if request.filter:
            search = search.where(request.filter)

        # Execute search and convert to pandas
        results = search.to_pandas()

        # Fast conversion to dict records
        results_list = results.to_dict("records")

        # Minimal serialization - only handle numpy arrays
        def _to_serializable(value: Any):
            if isinstance(value, np.ndarray):
                return value.tolist()
            if hasattr(value, "item"):
                try:
                    return value.item()
                except Exception:
                    pass
            return value

        results_typed: List[Dict[str, Any]] = [
            {str(k): _to_serializable(v) for k, v in record.items()} for record in results_list
        ]

        return SearchResult(results=results_typed, count=len(results_typed))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Search failed on table '%s': %s", request.table_name, str(e)
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.delete("/tables/{table_name}")
async def delete_table(table_name: str):
    """
    Delete a LanceDB table
    """
    try:
        if db_connection is None:
            raise HTTPException(status_code=503, detail="Database connection not initialized")
        
        if table_name not in db_connection.table_names():
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
        
        db_connection.drop_table(table_name)
        logger.info(f"Table '{table_name}' deleted successfully")
        
        return {
            "status": "success",
            "message": f"Table '{table_name}' deleted",
            "table_name": table_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete table: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete table: {str(e)}")


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": "LanceDB API",
        "version": "1.0.0",
        "description": "REST API wrapper for LanceDB vector database",
        "storage_type": STORAGE_TYPE,
        "documentation": "/docs"
    }


# Error handler for global exception handling
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")