"""
Resource Registry - DEPRECATED

This module is deprecated in favor of Terraform tfstate.
Kept as a stub for backward compatibility.

All resource tracking is now done via:
- Terraform tfstate (infrastructure)
- TerraformStateParser (Python integration)
"""

class ResourceRegistryStub:
    """Stub for backward compatibility. Does nothing."""
    
    def log_vector_bucket_created(self, *args, **kwargs):
        pass
    
    def log_opensearch_collection_created(self, *args, **kwargs):
        pass
    
    def log_opensearch_domain_created(self, *args, **kwargs):
        pass
    
    def log_opensearch_pipeline_created(self, *args, **kwargs):
        pass
    
    def log_opensearch_index_created(self, *args, **kwargs):
        pass
    
    def log_iam_role_created(self, *args, **kwargs):
        pass
    
    def log_custom_resource(self, *args, **kwargs):
        pass
    
    def list_opensearch_collections(self):
        return []
    
    def list_opensearch_domains(self):
        return []
    
    def list_opensearch_pipelines(self):
        return []
    
    def list_opensearch_indexes(self):
        return []
    
    def list_iam_roles(self):
        return []
    
    def list_custom_resources(self, resource_type=None):
        return []
    
    def get_resource_summary(self):
        return {}

# Global stub instance
resource_registry = ResourceRegistryStub()
