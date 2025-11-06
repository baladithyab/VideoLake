"""
Terraform Operation Tracker

Tracks active Terraform operations and stores their logs for real-time streaming.
Enables UI to monitor deploy/destroy operations in real-time via SSE.

Architecture:
- Each operation gets a unique ID
- Logs are stored in memory (queue per operation)
- SSE endpoint streams logs to UI
- Operations auto-cleanup after completion

Example:
    tracker = TerraformOperationTracker()
    
    # Start operation
    op_id = tracker.start_operation("deploy", "qdrant")
    
    # Add logs
    tracker.add_log(op_id, "Initializing Terraform...")
    tracker.add_log(op_id, "Creating ECS cluster...")
    
    # Complete operation
    tracker.complete_operation(op_id, success=True)
    
    # Stream logs (in SSE endpoint)
    for log in tracker.stream_logs(op_id):
        yield log
"""

import uuid
import time
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from threading import Lock
import asyncio

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TerraformOperation:
    """Represents a Terraform operation (deploy/destroy)."""
    operation_id: str
    operation_type: str  # "deploy", "destroy", "init"
    vector_store: Optional[str]
    status: str  # "running", "completed", "failed"
    start_time: float
    end_time: Optional[float] = None
    logs: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000 logs
    error: Optional[str] = None
    lock: Lock = field(default_factory=Lock)


class TerraformOperationTracker:
    """
    Tracks active Terraform operations and their logs.
    
    Thread-safe singleton for managing operation state across API requests.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure single tracker instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the tracker."""
        if self._initialized:
            return
            
        self.operations: Dict[str, TerraformOperation] = {}
        self.operations_lock = Lock()
        self._initialized = True
        
        logger.info("TerraformOperationTracker initialized")
    
    def start_operation(
        self,
        operation_type: str,
        vector_store: Optional[str] = None
    ) -> str:
        """
        Start tracking a new Terraform operation.
        
        Args:
            operation_type: Type of operation (deploy, destroy, init)
            vector_store: Vector store being operated on (optional)
            
        Returns:
            Unique operation ID
        """
        operation_id = str(uuid.uuid4())
        
        operation = TerraformOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            vector_store=vector_store,
            status="running",
            start_time=time.time()
        )
        
        with self.operations_lock:
            self.operations[operation_id] = operation
        
        logger.info(
            f"Started operation {operation_id}: {operation_type} "
            f"{vector_store or 'all'}"
        )
        
        # Add initial log
        self.add_log(
            operation_id,
            f"🚀 Starting {operation_type} operation for {vector_store or 'infrastructure'}",
            level="INFO"
        )
        
        return operation_id
    
    def add_log(
        self,
        operation_id: str,
        message: str,
        level: str = "INFO"
    ) -> None:
        """
        Add a log message to an operation.
        
        Args:
            operation_id: Operation to add log to
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
        """
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            
        if not operation:
            logger.warning(f"Operation {operation_id} not found")
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
        
        with operation.lock:
            operation.logs.append(log_entry)
    
    def complete_operation(
        self,
        operation_id: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: Operation to complete
            success: Whether operation succeeded
            error: Error message if failed
        """
        with self.operations_lock:
            operation = self.operations.get(operation_id)
            
        if not operation:
            logger.warning(f"Operation {operation_id} not found")
            return
        
        with operation.lock:
            operation.status = "completed" if success else "failed"
            operation.end_time = time.time()
            operation.error = error
        
        duration = operation.end_time - operation.start_time
        
        if success:
            self.add_log(
                operation_id,
                f"✅ Operation completed successfully in {duration:.1f}s",
                level="INFO"
            )
        else:
            self.add_log(
                operation_id,
                f"❌ Operation failed after {duration:.1f}s: {error}",
                level="ERROR"
            )
        
        logger.info(
            f"Completed operation {operation_id}: "
            f"{'success' if success else 'failed'} in {duration:.1f}s"
        )
    
    def get_operation(self, operation_id: str) -> Optional[TerraformOperation]:
        """
        Get an operation by ID.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            TerraformOperation or None
        """
        with self.operations_lock:
            return self.operations.get(operation_id)
    
    def get_logs(self, operation_id: str) -> List[Dict]:
        """
        Get all logs for an operation.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            List of log entries
        """
        operation = self.get_operation(operation_id)
        
        if not operation:
            return []
        
        with operation.lock:
            return list(operation.logs)
    
    def stream_logs(
        self,
        operation_id: str,
        from_index: int = 0
    ) -> Generator[Dict, None, None]:
        """
        Stream logs from an operation starting from a specific index.
        
        Used for SSE streaming - yields new logs as they arrive.
        
        Args:
            operation_id: Operation ID
            from_index: Start streaming from this log index
            
        Yields:
            Log entries as they arrive
        """
        operation = self.get_operation(operation_id)
        
        if not operation:
            logger.warning(f"Operation {operation_id} not found for streaming")
            return
        
        current_index = from_index
        
        # Stream existing logs first
        with operation.lock:
            logs = list(operation.logs)
            
        for i in range(from_index, len(logs)):
            yield logs[i]
            current_index = i + 1
        
        # Then stream new logs as they arrive (if operation still running)
        while operation.status == "running":
            time.sleep(0.1)  # Poll every 100ms
            
            with operation.lock:
                logs = list(operation.logs)
            
            # Yield any new logs
            for i in range(current_index, len(logs)):
                yield logs[i]
                current_index = i + 1
        
        # Stream final logs after completion
        with operation.lock:
            logs = list(operation.logs)
            
        for i in range(current_index, len(logs)):
            yield logs[i]
    
    def cleanup_old_operations(self, max_age_seconds: int = 3600) -> int:
        """
        Remove operations older than max_age_seconds.
        
        Args:
            max_age_seconds: Max age in seconds (default: 1 hour)
            
        Returns:
            Number of operations removed
        """
        current_time = time.time()
        removed = 0
        
        with self.operations_lock:
            to_remove = [
                op_id for op_id, op in self.operations.items()
                if op.end_time and (current_time - op.end_time) > max_age_seconds
            ]
            
            for op_id in to_remove:
                del self.operations[op_id]
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old operations")
        
        return removed
    
    def get_active_operations(self) -> List[str]:
        """
        Get list of currently running operation IDs.
        
        Returns:
            List of operation IDs
        """
        with self.operations_lock:
            return [
                op_id for op_id, op in self.operations.items()
                if op.status == "running"
            ]


# Global singleton instance
operation_tracker = TerraformOperationTracker()

