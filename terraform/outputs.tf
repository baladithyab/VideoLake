# Terraform Outputs for Videolake Infrastructure

#------------------------------------------------------------------------------
# SHARED MEDIA BUCKET (Always Created)
#------------------------------------------------------------------------------

output "shared_bucket" {
  description = "Shared S3 bucket for videos, TwelveLabs I/O, datasets, and async artifacts"
  value = {
    name = module.shared_bucket.bucket_name
    arn  = module.shared_bucket.bucket_arn
    region = var.aws_region
    purpose = "Shared media and artifact storage (always created)"
  }
}

#------------------------------------------------------------------------------
# S3VECTOR (Conditional)
#------------------------------------------------------------------------------

output "s3vector" {
  description = "S3Vector direct storage information"
  value = var.deploy_s3vector ? {
    deployed       = true
    bucket_name    = module.s3vector[0].vector_bucket_name
    bucket_arn     = module.s3vector[0].vector_bucket_arn
    index_name     = module.s3vector[0].default_index_name
    dimension      = module.s3vector[0].vector_dimension
    distance_metric = module.s3vector[0].distance_metric
    endpoint       = module.s3vector[0].endpoint
    iam_policy_arn = module.s3vector[0].iam_policy_arn
  } : {
    deployed = false
    message  = "S3Vector not deployed. Set var.deploy_s3vector=true to enable."
  }
}

#------------------------------------------------------------------------------
# OPENSEARCH (Conditional)
#------------------------------------------------------------------------------

output "opensearch" {
  description = "OpenSearch with S3Vector backend information"
  value = var.deploy_opensearch ? {
    deployed     = true
    domain_name  = var.opensearch_domain_name
    # Note: Add endpoint/ARN outputs once opensearch module has outputs defined
    message = "OpenSearch deployed. Add module outputs for endpoint details."
  } : {
    deployed = false
    message  = "OpenSearch not deployed. Set var.deploy_opensearch=true to enable."
  }
}

#------------------------------------------------------------------------------
# QDRANT (Conditional)
#------------------------------------------------------------------------------

output "qdrant" {
  description = "Qdrant ECS deployment information"
  value = var.deploy_qdrant ? {
    deployed        = true
    deployment_name = var.qdrant_deployment_name
    # Note: Add endpoint outputs once qdrant module has outputs defined
    message = "Qdrant deployed on ECS Fargate. Add module outputs for endpoint details."
  } : {
    deployed = false
    message  = "Qdrant not deployed. Set var.deploy_qdrant=true to enable."
  }
}

#------------------------------------------------------------------------------
# LANCEDB DEPLOYMENTS (Conditional)
#------------------------------------------------------------------------------

output "lancedb_s3" {
  description = "LanceDB S3 backend deployment"
  value = var.deploy_lancedb_s3 ? {
    deployed        = true
    deployment_name = "${var.lancedb_deployment_name}-s3"
    backend_type    = "s3"
    message = "LanceDB S3 backend deployed on ECS Fargate."
  } : {
    deployed = false
    message  = "LanceDB S3 not deployed. Set var.deploy_lancedb_s3=true to enable."
  }
}

output "lancedb_efs" {
  description = "LanceDB EFS backend deployment"
  value = var.deploy_lancedb_efs ? {
    deployed        = true
    deployment_name = "${var.lancedb_deployment_name}-efs"
    backend_type    = "efs"
    message = "LanceDB EFS backend deployed on ECS Fargate."
  } : {
    deployed = false
    message  = "LanceDB EFS not deployed. Set var.deploy_lancedb_efs=true to enable."
  }
}

output "lancedb_ebs" {
  description = "LanceDB EBS backend deployment"
  value = var.deploy_lancedb_ebs ? {
    deployed        = true
    deployment_name = "${var.lancedb_deployment_name}-ebs"
    backend_type    = "ebs"
    message = "LanceDB EBS backend deployed on ECS Fargate."
  } : {
    deployed = false
    message  = "LanceDB EBS not deployed. Set var.deploy_lancedb_ebs=true to enable."
  }
}

#------------------------------------------------------------------------------
# DEPLOYMENT SUMMARY
#------------------------------------------------------------------------------

output "deployment_summary" {
  description = "Summary of all deployed resources"
  value = {
    region = var.aws_region
    environment = var.environment
    project_name = var.project_name
    
    always_deployed = {
      shared_bucket = local.shared_bucket_name
    }
    
    vector_stores_deployed = {
      s3vector       = var.deploy_s3vector
      opensearch     = var.deploy_opensearch
      qdrant         = var.deploy_qdrant
      lancedb_s3     = var.deploy_lancedb_s3
      lancedb_efs    = var.deploy_lancedb_efs
      lancedb_ebs    = var.deploy_lancedb_ebs
    }
    
    total_vector_stores = (
      (var.deploy_s3vector ? 1 : 0) +
      (var.deploy_opensearch ? 1 : 0) +
      (var.deploy_qdrant ? 1 : 0) +
      (var.deploy_lancedb_s3 ? 1 : 0) +
      (var.deploy_lancedb_efs ? 1 : 0) +
      (var.deploy_lancedb_ebs ? 1 : 0)
    )
  }
}

#------------------------------------------------------------------------------
# LEGACY OUTPUTS (For Backward Compatibility)
#------------------------------------------------------------------------------

output "infrastructure_deployed" {
  description = "[DEPRECATED] Use deployment_summary instead"
  value = {
    shared_bucket = local.shared_bucket_name
    data_bucket = var.data_bucket_name != null ? var.data_bucket_name : "not_deployed"
    s3vector = var.deploy_s3vector ? var.s3vector_bucket_name : "not_deployed"
    opensearch_domain = var.deploy_opensearch ? var.opensearch_domain_name : "not_deployed"
    qdrant_deployment = var.deploy_qdrant ? var.qdrant_deployment_name : "not_deployed"
    lancedb_deployments = {
      s3 = var.deploy_lancedb_s3 ? "${var.lancedb_deployment_name}-s3" : "not_deployed"
      efs = var.deploy_lancedb_efs ? "${var.lancedb_deployment_name}-efs" : "not_deployed"
      ebs = var.deploy_lancedb_ebs ? "${var.lancedb_deployment_name}-ebs" : "not_deployed"
    }
  }
}
