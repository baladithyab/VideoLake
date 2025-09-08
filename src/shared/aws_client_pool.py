"""
Centralized AWS Client Management with Connection Pooling

This module provides enhanced AWS client management with connection pooling,
caching, and optimized resource utilization to eliminate client duplication
across services.
"""

import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
import logging

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

from src.config.unified_config_manager import get_unified_config_manager
from src.exceptions import ConfigurationError
from src.utils.logging_config import get_logger, get_structured_logger

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


class AWSService(Enum):
    """Supported AWS services."""
    S3 = "s3"
    S3_VECTORS = "s3vectors"
    BEDROCK_RUNTIME = "bedrock-runtime"
    OPENSEARCH = "opensearch"
    STS = "sts"
    IAM = "iam"
    CLOUDFORMATION = "cloudformation"


class ClientPoolStrategy(Enum):
    """Client pooling strategies."""
    SINGLETON = "singleton"  # One client per service
    PER_THREAD = "per_thread"  # One client per thread per service
    POOLED = "pooled"  # Pool of clients per service
    ON_DEMAND = "on_demand"  # Create clients as needed, no caching


@dataclass
class ClientPoolConfig:
    """Configuration for AWS client pool."""
    strategy: ClientPoolStrategy = ClientPoolStrategy.SINGLETON
    max_pool_size: int = 10
    min_pool_size: int = 2
    client_timeout_seconds: int = 300
    connection_timeout_seconds: int = 10
    read_timeout_seconds: int = 60
    max_retries: int = 3
    retry_mode: str = "adaptive"
    max_pool_connections: int = 50
    
    # Health check settings
    enable_health_checks: bool = True
    health_check_interval_seconds: int = 60
    max_idle_time_seconds: int = 300
    
    # Metrics and monitoring
    enable_metrics: bool = True
    metrics_collection_interval: int = 30
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.max_pool_size < self.min_pool_size:
            raise ConfigurationError(
                "max_pool_size must be >= min_pool_size",
                error_code="INVALID_POOL_CONFIG"
            )
        
        if self.client_timeout_seconds <= 0:
            raise ConfigurationError(
                "client_timeout_seconds must be positive",
                error_code="INVALID_TIMEOUT_CONFIG"
            )


@dataclass
class ClientMetrics:
    """Metrics for client usage."""
    service: AWSService
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    usage_count: int = 0
    error_count: int = 0
    total_request_time: float = 0.0
    
    @property
    def average_request_time(self) -> float:
        """Calculate average request time."""
        return self.total_request_time / max(self.usage_count, 1)
    
    @property
    def idle_time(self) -> float:
        """Calculate idle time since last use."""
        return time.time() - self.last_used
    
    def record_usage(self, request_time: float = 0.0, error: bool = False) -> None:
        """Record client usage."""
        self.last_used = time.time()
        self.usage_count += 1
        if error:
            self.error_count += 1
        if request_time > 0:
            self.total_request_time += request_time


class PooledClient:
    """Wrapper for pooled AWS clients with metrics and health checking."""
    
    def __init__(self, service: AWSService, client: Any, config: ClientPoolConfig):
        self.service = service
        self._client = client
        self.config = config
        self.metrics = ClientMetrics(service)
        self._lock = threading.RLock()
        self._healthy = True
        self._last_health_check = time.time()
    
    @property
    def client(self) -> Any:
        """Get the underlying boto3 client."""
        with self._lock:
            self.metrics.record_usage()
            return self._client
    
    def is_healthy(self) -> bool:
        """Check if client is healthy."""
        with self._lock:
            if not self.config.enable_health_checks:
                return True
            
            # Check if health check is needed
            now = time.time()
            if (now - self._last_health_check) < self.config.health_check_interval_seconds:
                return self._healthy
            
            # Perform health check
            try:
                self._perform_health_check()
                self._healthy = True
            except Exception as e:
                logger.warning(f"Health check failed for {self.service.value} client: {e}")
                self._healthy = False
                self.metrics.record_usage(error=True)
            
            self._last_health_check = now
            return self._healthy
    
    def _perform_health_check(self) -> None:
        """Perform service-specific health check."""
        if self.service == AWSService.S3:
            self._client.list_buckets()
        elif self.service == AWSService.S3_VECTORS:
            self._client.list_vector_buckets()
        elif self.service == AWSService.BEDROCK_RUNTIME:
            # Bedrock doesn't have a simple list operation, so we'll just check the client
            pass
        elif self.service == AWSService.OPENSEARCH:
            self._client.list_domain_names()
        elif self.service == AWSService.STS:
            self._client.get_caller_identity()
        else:
            # Generic health check - just ensure client is accessible
            pass
    
    def is_idle(self) -> bool:
        """Check if client has been idle too long."""
        return self.metrics.idle_time > self.config.max_idle_time_seconds
    
    def close(self) -> None:
        """Close the client connection."""
        with self._lock:
            if hasattr(self._client, 'close'):
                self._client.close()
            self._healthy = False


class AWSClientPool:
    """Enhanced AWS client pool with connection pooling and management."""
    
    def __init__(self, config: Optional[ClientPoolConfig] = None):
        """Initialize the AWS client pool."""
        self.config = config or ClientPoolConfig()
        self.config.validate()
        
        self._pools: Dict[AWSService, List[PooledClient]] = {}
        self._thread_locals: Dict[AWSService, threading.local] = {}
        self._singletons: Dict[AWSService, PooledClient] = {}
        self._pool_locks: Dict[AWSService, threading.RLock] = {}
        self._session: Optional[boto3.Session] = None
        self._session_lock = threading.RLock()
        
        # Background maintenance
        self._maintenance_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="aws-pool-maintenance")
        self._shutdown = False
        
        # Start background tasks
        if self.config.enable_health_checks:
            self._maintenance_executor.submit(self._health_check_loop)
        
        if self.config.enable_metrics:
            self._maintenance_executor.submit(self._metrics_collection_loop)
        
        structured_logger.log_operation(
            "aws_client_pool_initialized",
            level="INFO",
            strategy=self.config.strategy.value,
            max_pool_size=self.config.max_pool_size
        )
    
    def _get_session(self) -> boto3.Session:
        """Get or create boto3 session."""
        with self._session_lock:
            if self._session is None:
                config_manager = get_unified_config_manager()
                aws_config = config_manager.config.aws
                
                session_kwargs = {'region_name': aws_config.region}
                
                if aws_config.access_key_id:
                    session_kwargs['aws_access_key_id'] = aws_config.access_key_id
                if aws_config.secret_access_key:
                    session_kwargs['aws_secret_access_key'] = aws_config.secret_access_key
                if aws_config.session_token:
                    session_kwargs['aws_session_token'] = aws_config.session_token
                
                self._session = boto3.Session(**session_kwargs)
            
            return self._session
    
    def _get_client_config(self) -> Config:
        """Get optimized client configuration."""
        config_manager = get_unified_config_manager()
        aws_config = config_manager.config.aws
        
        return Config(
            retries={
                'max_attempts': self.config.max_retries,
                'mode': self.config.retry_mode
            },
            read_timeout=self.config.read_timeout_seconds,
            connect_timeout=self.config.connection_timeout_seconds,
            max_pool_connections=self.config.max_pool_connections,
            region_name=aws_config.region
        )
    
    def _create_client(self, service: AWSService) -> PooledClient:
        """Create a new AWS client."""
        try:
            session = self._get_session()
            config = self._get_client_config()
            
            client = session.client(service.value, config=config)
            pooled_client = PooledClient(service, client, self.config)
            
            structured_logger.log_operation(
                "aws_client_created",
                level="DEBUG",
                service=service.value,
                strategy=self.config.strategy.value
            )
            
            return pooled_client
            
        except Exception as e:
            structured_logger.log_error("aws_client_creation_failed", e, service=service.value)
            raise ConfigurationError(
                f"Failed to create {service.value} client: {str(e)}",
                error_code="CLIENT_CREATION_ERROR",
                error_details={"service": service.value, "error": str(e)}
            )
    
    def get_client(self, service: AWSService) -> Any:
        """Get AWS client based on pooling strategy."""
        if self.config.strategy == ClientPoolStrategy.SINGLETON:
            return self._get_singleton_client(service)
        elif self.config.strategy == ClientPoolStrategy.PER_THREAD:
            return self._get_thread_local_client(service)
        elif self.config.strategy == ClientPoolStrategy.POOLED:
            return self._get_pooled_client(service)
        elif self.config.strategy == ClientPoolStrategy.ON_DEMAND:
            return self._create_client(service).client
        else:
            raise ConfigurationError(
                f"Unsupported pooling strategy: {self.config.strategy.value}",
                error_code="UNSUPPORTED_STRATEGY"
            )
    
    def _get_singleton_client(self, service: AWSService) -> Any:
        """Get singleton client for service."""
        if service not in self._singletons:
            self._singletons[service] = self._create_client(service)
        
        client = self._singletons[service]
        if not client.is_healthy():
            logger.warning(f"Singleton client for {service.value} is unhealthy, recreating")
            client.close()
            self._singletons[service] = self._create_client(service)
            client = self._singletons[service]
        
        return client.client
    
    def _get_thread_local_client(self, service: AWSService) -> Any:
        """Get thread-local client for service."""
        if service not in self._thread_locals:
            self._thread_locals[service] = threading.local()
        
        thread_local = self._thread_locals[service]
        
        if not hasattr(thread_local, 'client') or not thread_local.client.is_healthy():
            if hasattr(thread_local, 'client'):
                thread_local.client.close()
            thread_local.client = self._create_client(service)
        
        return thread_local.client.client
    
    def _get_pooled_client(self, service: AWSService) -> Any:
        """Get client from pool."""
        if service not in self._pool_locks:
            self._pool_locks[service] = threading.RLock()
        
        with self._pool_locks[service]:
            if service not in self._pools:
                self._pools[service] = []
            
            pool = self._pools[service]
            
            # Find healthy client
            for client in pool:
                if client.is_healthy():
                    return client.client
            
            # Create new client if pool is not full
            if len(pool) < self.config.max_pool_size:
                new_client = self._create_client(service)
                pool.append(new_client)
                return new_client.client
            
            # Pool is full, remove unhealthy clients and create new one
            pool[:] = [c for c in pool if c.is_healthy()]
            if len(pool) < self.config.max_pool_size:
                new_client = self._create_client(service)
                pool.append(new_client)
                return new_client.client
            
            # Use least recently used client
            lru_client = min(pool, key=lambda c: c.metrics.last_used)
            return lru_client.client
    
    def _health_check_loop(self) -> None:
        """Background health check loop."""
        while not self._shutdown:
            try:
                # Use shorter sleep intervals to check shutdown flag more frequently
                sleep_time = min(self.config.health_check_interval_seconds, 5)
                for _ in range(int(self.config.health_check_interval_seconds / sleep_time)):
                    if self._shutdown:
                        return
                    time.sleep(sleep_time)
                
                if not self._shutdown:
                    self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                if self._shutdown:
                    return
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all clients."""
        # Check singletons
        for service, client in list(self._singletons.items()):
            if not client.is_healthy():
                logger.warning(f"Singleton client for {service.value} failed health check")
        
        # Check pooled clients
        for service, pool in self._pools.items():
            with self._pool_locks.get(service, threading.RLock()):
                unhealthy_clients = [c for c in pool if not c.is_healthy()]
                for client in unhealthy_clients:
                    logger.warning(f"Pooled client for {service.value} failed health check")
                    client.close()
                    pool.remove(client)
    
    def _metrics_collection_loop(self) -> None:
        """Background metrics collection loop."""
        while not self._shutdown:
            try:
                # Use shorter sleep intervals to check shutdown flag more frequently
                sleep_time = min(self.config.metrics_collection_interval, 5)
                for _ in range(int(self.config.metrics_collection_interval / sleep_time)):
                    if self._shutdown:
                        return
                    time.sleep(sleep_time)
                
                if not self._shutdown:
                    self._collect_metrics()
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                if self._shutdown:
                    return
    
    def _collect_metrics(self) -> None:
        """Collect and log client metrics."""
        metrics_summary = {}
        
        # Collect singleton metrics
        for service, client in self._singletons.items():
            metrics_summary[f"singleton_{service.value}"] = {
                "usage_count": client.metrics.usage_count,
                "error_count": client.metrics.error_count,
                "average_request_time": client.metrics.average_request_time,
                "idle_time": client.metrics.idle_time
            }
        
        # Collect pooled metrics
        for service, pool in self._pools.items():
            pool_metrics = {
                "pool_size": len(pool),
                "healthy_clients": sum(1 for c in pool if c.is_healthy()),
                "total_usage": sum(c.metrics.usage_count for c in pool),
                "total_errors": sum(c.metrics.error_count for c in pool)
            }
            metrics_summary[f"pool_{service.value}"] = pool_metrics
        
        if metrics_summary:
            structured_logger.log_operation(
                "aws_client_pool_metrics",
                level="DEBUG",
                metrics=metrics_summary
            )
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics."""
        stats = {
            "config": {
                "strategy": self.config.strategy.value,
                "max_pool_size": self.config.max_pool_size,
                "health_checks_enabled": self.config.enable_health_checks
            },
            "singletons": {},
            "pools": {},
            "thread_locals": len(self._thread_locals)
        }
        
        # Singleton stats
        for service, client in self._singletons.items():
            stats["singletons"][service.value] = {
                "healthy": client.is_healthy(),
                "usage_count": client.metrics.usage_count,
                "error_count": client.metrics.error_count,
                "idle_time": client.metrics.idle_time
            }
        
        # Pool stats
        for service, pool in self._pools.items():
            stats["pools"][service.value] = {
                "size": len(pool),
                "healthy_count": sum(1 for c in pool if c.is_healthy()),
                "total_usage": sum(c.metrics.usage_count for c in pool),
                "total_errors": sum(c.metrics.error_count for c in pool)
            }
        
        return stats
    
    def cleanup_idle_clients(self) -> int:
        """Clean up idle clients and return count of cleaned clients."""
        cleaned_count = 0
        
        # Clean up pooled clients
        for service, pool in self._pools.items():
            with self._pool_locks.get(service, threading.RLock()):
                idle_clients = [c for c in pool if c.is_idle()]
                for client in idle_clients:
                    client.close()
                    pool.remove(client)
                    cleaned_count += 1
        
        if cleaned_count > 0:
            structured_logger.log_operation(
                "idle_clients_cleaned",
                level="INFO",
                cleaned_count=cleaned_count
            )
        
        return cleaned_count
    
    def reset_pool(self, service: Optional[AWSService] = None) -> None:
        """Reset client pool for specific service or all services."""
        if service:
            services_to_reset = [service]
        else:
            services_to_reset = list(AWSService)
        
        for svc in services_to_reset:
            # Reset singleton
            if svc in self._singletons:
                self._singletons[svc].close()
                del self._singletons[svc]
            
            # Reset pool
            if svc in self._pools:
                with self._pool_locks.get(svc, threading.RLock()):
                    for client in self._pools[svc]:
                        client.close()
                    self._pools[svc].clear()
            
            # Reset thread locals
            if svc in self._thread_locals:
                del self._thread_locals[svc]
        
        # Reset session
        with self._session_lock:
            self._session = None
        
        structured_logger.log_operation(
            "client_pool_reset",
            level="INFO",
            services=service.value if service else "all"
        )
    
    def shutdown(self) -> None:
        """Shutdown the client pool."""
        self._shutdown = True
        
        # Close all clients
        for client in self._singletons.values():
            client.close()
        
        for pool in self._pools.values():
            for client in pool:
                client.close()
        
        # Shutdown maintenance executor - don't wait to prevent hanging
        try:
            self._maintenance_executor.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"Error during executor shutdown: {e}")
        
        structured_logger.log_operation("aws_client_pool_shutdown", level="INFO")


# Global client pool instance
_client_pool: Optional[AWSClientPool] = None
_pool_lock = threading.RLock()


def get_pooled_client(service: AWSService) -> Any:
    """Get AWS client from the global pool."""
    global _client_pool
    
    with _pool_lock:
        if _client_pool is None:
            _client_pool = AWSClientPool()
        
        return _client_pool.get_client(service)


def configure_client_pool(config: ClientPoolConfig) -> None:
    """Configure the global client pool."""
    global _client_pool
    
    with _pool_lock:
        if _client_pool is not None:
            _client_pool.shutdown()
        
        _client_pool = AWSClientPool(config)


def get_pool_statistics() -> Dict[str, Any]:
    """Get statistics from the global client pool."""
    global _client_pool
    
    with _pool_lock:
        if _client_pool is None:
            return {"status": "not_initialized"}
        
        return _client_pool.get_pool_statistics()


def reset_client_pool(service: Optional[AWSService] = None) -> None:
    """Reset the global client pool."""
    global _client_pool
    
    with _pool_lock:
        if _client_pool is not None:
            _client_pool.reset_pool(service)


def shutdown_client_pool() -> None:
    """Shutdown the global client pool."""
    global _client_pool
    
    with _pool_lock:
        if _client_pool is not None:
            _client_pool.shutdown()
            _client_pool = None