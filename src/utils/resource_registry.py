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

    def list_vector_buckets(self):
        return []
    
    def list_s3_buckets(self):
        return []

    def list_indexes(self):
        return []
    
    def log_index_created(self, *args, **kwargs):
        pass
    
    def log_index_deleted(self, *args, **kwargs):
        pass
    
    def log_vector_bucket_deleted(self, *args, **kwargs):
        pass

    def get_registry(self):
        return {
            "version": "stub",
            "deprecated": True,
            "message": "Resource tracking moved to Terraform tfstate"
        }

    def get_active_resources(self):
        return {
            "s3_bucket": None,
            "vector_bucket": None,
            "index_arn": None,
            "opensearch_collection": None,
            "opensearch_domain": None
        }

    def get_resource_summary(self):
        return {
            "s3_buckets": 0,
            "vector_buckets": 0,
            "vector_indexes": 0,
            "opensearch_collections": 0,
            "opensearch_domains": 0,
            "opensearch_pipelines": 0,
            "opensearch_indexes": 0,
            "iam_roles": 0,
            "last_updated": None,
            "active_resources": {}
        }

# Global stub instance
resource_registry = ResourceRegistryStub()
