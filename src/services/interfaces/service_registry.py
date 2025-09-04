"""
Service Registry Implementation

Concrete implementation of service registry for dependency injection
and breaking circular dependencies between services.
"""

from typing import Dict, Any, Optional, List
from threading import Lock
import logging

from .coordinator_interface import IServiceRegistry

logger = logging.getLogger(__name__)


class ServiceRegistry(IServiceRegistry):
    """
    Concrete implementation of service registry.
    
    This registry enables services to find and interact with each other
    without creating direct circular dependencies through dependency injection.
    """
    
    def __init__(self):
        """Initialize the service registry."""
        self._services: Dict[str, Any] = {}
        self._lock = Lock()
        self._initialized = False
        
        logger.info("ServiceRegistry initialized")
    
    def register_service(self, service_name: str, service_instance: Any) -> None:
        """
        Register a service instance in the registry.
        
        Args:
            service_name: Unique name for the service
            service_instance: Service instance to register
        """
        with self._lock:
            if service_name in self._services:
                logger.warning(f"Overriding existing service: {service_name}")
            
            self._services[service_name] = service_instance
            logger.debug(f"Registered service: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """
        Get a service instance from the registry.
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance or None if not found
        """
        with self._lock:
            service = self._services.get(service_name)
            if service is None:
                logger.debug(f"Service not found: {service_name}")
            return service
    
    def list_services(self) -> List[str]:
        """
        List all registered service names.
        
        Returns:
            List of service names
        """
        with self._lock:
            return list(self._services.keys())
    
    def is_service_available(self, service_name: str) -> bool:
        """
        Check if a service is available in the registry.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is available, False otherwise
        """
        with self._lock:
            return service_name in self._services
    
    def unregister_service(self, service_name: str) -> bool:
        """
        Unregister a service from the registry.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if service was removed, False if not found
        """
        with self._lock:
            if service_name in self._services:
                del self._services[service_name]
                logger.debug(f"Unregistered service: {service_name}")
                return True
            return False
    
    def clear_registry(self) -> None:
        """Clear all services from the registry."""
        with self._lock:
            self._services.clear()
            logger.info("Service registry cleared")
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the service registry.
        
        Returns:
            Dictionary with registry statistics
        """
        with self._lock:
            return {
                'total_services': len(self._services),
                'service_names': list(self._services.keys()),
                'initialized': self._initialized
            }


# Global service registry instance
_global_registry = None
_registry_lock = Lock()


def get_service_registry() -> ServiceRegistry:
    """
    Get the global service registry instance.
    
    Returns:
        Global ServiceRegistry instance
    """
    global _global_registry
    
    with _registry_lock:
        if _global_registry is None:
            _global_registry = ServiceRegistry()
        return _global_registry


def register_global_service(service_name: str, service_instance: Any) -> None:
    """
    Register a service in the global registry.
    
    Args:
        service_name: Name of the service
        service_instance: Service instance to register
    """
    registry = get_service_registry()
    registry.register_service(service_name, service_instance)


def get_global_service(service_name: str) -> Optional[Any]:
    """
    Get a service from the global registry.
    
    Args:
        service_name: Name of the service to get
        
    Returns:
        Service instance or None if not found
    """
    registry = get_service_registry()
    return registry.get_service(service_name)


# Service name constants to avoid typos
class ServiceNames:
    """Constants for service names."""
    SIMILARITY_SEARCH_ENGINE = "similarity_search_engine"
    MULTI_VECTOR_COORDINATOR = "multi_vector_coordinator"
    TWELVELABS_SERVICE = "twelvelabs_service"
    BEDROCK_SERVICE = "bedrock_service"
    S3_VECTOR_STORAGE = "s3_vector_storage"
    VIDEO_STORAGE = "video_storage"
    TEXT_STORAGE = "text_storage"
    OPENSEARCH_INTEGRATION = "opensearch_integration"