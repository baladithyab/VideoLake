# Terraform Outputs for Videolake Infrastructure

#------------------------------------------------------------------------------
# SHARED MEDIA BUCKET (Always Created)
#------------------------------------------------------------------------------

output "shared_bucket" {
  description = "Shared S3 bucket for videos, TwelveLabs I/O, datasets, and async artifacts"
  value = {
    name    = module.shared_bucket.bucket_name
    arn     = module.shared_bucket.bucket_arn
    region  = var.aws_region
    purpose = "Shared media and artifact storage (always created)"
  }
}

#------------------------------------------------------------------------------
# S3VECTOR (Conditional)
#------------------------------------------------------------------------------

output "s3vector" {
  description = "S3Vector direct storage information"
  value = var.deploy_s3vector ? {
    deployed        = true
    bucket_name     = module.s3vector[0].vector_bucket_name
    bucket_arn      = module.s3vector[0].vector_bucket_arn
    index_name      = module.s3vector[0].default_index_name
    dimension       = module.s3vector[0].vector_dimension
    distance_metric = module.s3vector[0].distance_metric
    endpoint        = module.s3vector[0].endpoint
    iam_policy_arn  = module.s3vector[0].iam_policy_arn
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
    deployed           = true
    domain_id          = module.opensearch[0].domain_id
    domain_name        = module.opensearch[0].domain_name
    domain_arn         = module.opensearch[0].domain_arn
    endpoint           = module.opensearch[0].endpoint
    dashboard_endpoint = module.opensearch[0].dashboard_endpoint
    health_check_url   = module.opensearch[0].health_check_url
    engine_version     = module.opensearch[0].engine_version
    s3vector_enabled   = module.opensearch[0].s3vector_engine_enabled
    deployment_info    = module.opensearch[0].deployment_info
    message            = ""
    } : {
    deployed           = false
    domain_id          = ""
    domain_name        = ""
    domain_arn         = ""
    endpoint           = ""
    dashboard_endpoint = ""
    health_check_url   = ""
    engine_version     = ""
    s3vector_enabled   = false
    deployment_info    = {}
    message            = "OpenSearch not deployed. Set var.deploy_opensearch=true to enable."
  }
}

#------------------------------------------------------------------------------
# QDRANT (Conditional)
#------------------------------------------------------------------------------

output "qdrant" {
  description = "Qdrant ECS deployment information"
  value = var.deploy_qdrant ? {
    deployed           = true
    deployment_name    = var.qdrant_deployment_name
    cluster_arn        = module.qdrant[0].cluster_arn
    service_name       = module.qdrant[0].service_name
    security_group_id  = module.qdrant[0].security_group_id
    endpoint_discovery = module.qdrant[0].endpoint_discovery_command
    rest_api_port      = module.qdrant[0].rest_api_port
    grpc_port          = module.qdrant[0].grpc_port
    efs_id             = module.qdrant[0].efs_id
    deployment_info    = module.qdrant[0].deployment_info
    note               = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message            = ""
    } : {
    deployed           = false
    deployment_name    = ""
    cluster_arn        = ""
    service_name       = ""
    security_group_id  = ""
    endpoint_discovery = ""
    rest_api_port      = 0
    grpc_port          = 0
    efs_id             = ""
    deployment_info    = {}
    note               = ""
    message            = "Qdrant not deployed. Set var.deploy_qdrant=true to enable."
  }
}

output "qdrant_ebs" {
  description = "Qdrant EC2+EBS deployment information"
  value = var.deploy_qdrant_ebs ? {
    deployed        = true
    deployment_name = "${var.qdrant_deployment_name}-ebs"
    backend_type    = "ebs"
    message         = "Qdrant deployed on EC2 with attached EBS volume."
    } : {
    deployed        = false
    deployment_name = ""
    backend_type    = ""
    message         = "Qdrant EC2+EBS not deployed. Set var.deploy_qdrant_ebs=true to enable."
  }
}


#------------------------------------------------------------------------------
# LANCEDB DEPLOYMENTS (Conditional)
#------------------------------------------------------------------------------

output "lancedb_s3" {
  description = "LanceDB S3 backend deployment"
  value = var.deploy_lancedb_s3 ? {
    deployed           = true
    deployment_name    = "${var.lancedb_deployment_name}-s3"
    backend_type       = "s3"
    cluster_arn        = module.lancedb_s3[0].cluster_arn
    service_name       = module.lancedb_s3[0].service_name
    security_group_id  = module.lancedb_s3[0].security_group_id
    s3_bucket_name     = module.lancedb_s3[0].s3_bucket_name
    endpoint_discovery = module.lancedb_s3[0].endpoint_discovery_command
    deployment_info    = module.lancedb_s3[0].deployment_info
    note               = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message            = ""
    } : {
    deployed           = false
    deployment_name    = ""
    backend_type       = ""
    cluster_arn        = ""
    service_name       = ""
    security_group_id  = ""
    s3_bucket_name     = ""
    endpoint_discovery = ""
    deployment_info    = {}
    note               = ""
    message            = "LanceDB S3 not deployed. Set var.deploy_lancedb_s3=true to enable."
  }
}

output "lancedb_efs" {
  description = "LanceDB EFS backend deployment"
  value = var.deploy_lancedb_efs ? {
    deployed           = true
    deployment_name    = "${var.lancedb_deployment_name}-efs"
    backend_type       = "efs"
    cluster_arn        = module.lancedb_efs[0].cluster_arn
    service_name       = module.lancedb_efs[0].service_name
    security_group_id  = module.lancedb_efs[0].security_group_id
    efs_id             = module.lancedb_efs[0].efs_id
    endpoint_discovery = module.lancedb_efs[0].endpoint_discovery_command
    deployment_info    = module.lancedb_efs[0].deployment_info
    note               = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message            = ""
    } : {
    deployed           = false
    deployment_name    = ""
    backend_type       = ""
    cluster_arn        = ""
    service_name       = ""
    security_group_id  = ""
    efs_id             = ""
    endpoint_discovery = ""
    deployment_info    = {}
    note               = ""
    message            = "LanceDB EFS not deployed. Set var.deploy_lancedb_efs=true to enable."
  }
}

output "lancedb_ebs" {
  description = "LanceDB EBS backend deployment (EC2 with dedicated EBS volume)"
  value = var.deploy_lancedb_ebs ? {
    deployed          = true
    deployment_name   = "${var.lancedb_deployment_name}-ebs"
    backend_type      = "ebs"
    deployment_type   = "ec2"
    instance_id       = module.lancedb_ebs[0].instance_id
    public_ip         = module.lancedb_ebs[0].public_ip
    private_ip        = module.lancedb_ebs[0].private_ip
    endpoint          = module.lancedb_ebs[0].endpoint
    lancedb_api_url   = module.lancedb_ebs[0].lancedb_api_url
    ebs_volume_id     = module.lancedb_ebs[0].ebs_volume_id
    security_group_id = module.lancedb_ebs[0].security_group_id
    deployment_info   = module.lancedb_ebs[0].deployment_info
    note              = "True EC2+EBS deployment with direct endpoint access"
    message           = ""
    } : {
    deployed          = false
    deployment_name   = ""
    backend_type      = ""
    deployment_type   = ""
    instance_id       = ""
    public_ip         = ""
    private_ip        = ""
    endpoint          = ""
    lancedb_api_url   = ""
    ebs_volume_id     = ""
    security_group_id = ""
    deployment_info   = {}
    note              = ""
    message           = "LanceDB EBS not deployed. Set var.deploy_lancedb_ebs=true to enable."
  }
}

output "videolake_backend" {
  description = "VideoLake Backend ECS Service"
  value = {
    alb_dns_name       = module.videolake_backend.alb_dns_name
    ecr_repository_url = module.videolake_backend.ecr_repository_url
    ecs_cluster_name   = module.videolake_backend.ecs_cluster_name
    ecs_service_name   = module.videolake_backend.ecs_service_name
  }
}

output "videolake_frontend" {
  description = "VideoLake Frontend Hosting"
  value = {
    cloudfront_domain_name = module.videolake_frontend.cloudfront_domain_name
    s3_bucket_name         = module.videolake_frontend.s3_bucket_name
  }
}

#------------------------------------------------------------------------------
# DEPLOYMENT SUMMARY
#------------------------------------------------------------------------------

output "deployment_summary" {
  description = "Summary of all deployed resources"
  value = {
    region       = var.aws_region
    environment  = var.environment
    project_name = var.project_name

    always_deployed = {
      shared_bucket = local.shared_bucket_name
    }

    vector_stores_deployed = {
      s3vector    = var.deploy_s3vector
      opensearch  = var.deploy_opensearch
      qdrant      = var.deploy_qdrant
      qdrant_ebs  = var.deploy_qdrant_ebs
      lancedb_s3  = var.deploy_lancedb_s3
      lancedb_efs = var.deploy_lancedb_efs
      lancedb_ebs = var.deploy_lancedb_ebs
    }

    total_vector_stores = (
      (var.deploy_s3vector ? 1 : 0) +
      (var.deploy_opensearch ? 1 : 0) +
      (var.deploy_qdrant ? 1 : 0) +
      (var.deploy_qdrant_ebs ? 1 : 0) +
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
    shared_bucket         = local.shared_bucket_name
    data_bucket           = var.data_bucket_name != null ? var.data_bucket_name : "not_deployed"
    s3vector              = var.deploy_s3vector ? var.s3vector_bucket_name : "not_deployed"
    opensearch_domain     = var.deploy_opensearch ? var.opensearch_domain_name : "not_deployed"
    qdrant_deployment     = var.deploy_qdrant ? var.qdrant_deployment_name : "not_deployed"
    qdrant_ebs_deployment = var.deploy_qdrant_ebs ? "${var.qdrant_deployment_name}-ebs" : "not_deployed"
    lancedb_deployments = {
      s3  = var.deploy_lancedb_s3 ? "${var.lancedb_deployment_name}-s3" : "not_deployed"
      efs = var.deploy_lancedb_efs ? "${var.lancedb_deployment_name}-efs" : "not_deployed"
      ebs = var.deploy_lancedb_ebs ? "${var.lancedb_deployment_name}-ebs" : "not_deployed"
    }
  }
}

#------------------------------------------------------------------------------
# INGESTION PIPELINE (Conditional)
#------------------------------------------------------------------------------

output "ingestion_pipeline_arn" {
  description = "ARN of the ingestion pipeline Step Function"
  value       = length(module.ingestion_pipeline) > 0 ? module.ingestion_pipeline[0].state_machine_arn : null
}

output "embeddings_bucket_name" {
  description = "Name of the embeddings S3 bucket"
  value       = length(module.ingestion_pipeline) > 0 ? module.ingestion_pipeline[0].embeddings_bucket_name : null
}

output "ingestion_lambda_functions" {
  description = "ARNs of the ingestion Lambda functions"
  value       = length(module.ingestion_pipeline) > 0 ? module.ingestion_pipeline[0].lambda_function_arns : {}
}

#------------------------------------------------------------------------------
# LANCEDB BENCHMARK RUNNER (Conditional)
#------------------------------------------------------------------------------

output "lancedb_benchmark_runner" {
  description = "LanceDB Benchmark Runner EC2 information"
  value = var.deploy_lancedb_benchmark_ec2 ? {
    deployed    = true
    public_ip   = module.lancedb_benchmark_ec2[0].public_ip
    instance_id = module.lancedb_benchmark_ec2[0].instance_id
    message     = "Benchmark runner deployed. Connect via SSM or SSH (if key provided)."
    } : {
    deployed    = false
    public_ip   = ""
    instance_id = ""
    message     = "Benchmark runner not deployed. Set var.deploy_lancedb_benchmark_ec2=true to enable."
  }
}

# =============================================================================
# EMBEDDING PROVIDERS OUTPUTS
# =============================================================================

output "bedrock_native_enabled" {
  description = "Whether Bedrock native provider is enabled"
  value       = var.deploy_bedrock_native
}

output "bedrock_embedding_role_arn" {
  description = "IAM role ARN for Bedrock embedding access"
  value       = var.deploy_bedrock_native ? module.bedrock_native[0].embedding_role_arn : ""
}

output "bedrock_text_model_id" {
  description = "Bedrock text embedding model ID"
  value       = var.deploy_bedrock_native ? module.bedrock_native[0].text_model_id : ""
}

output "marketplace_provider_enabled" {
  description = "Whether AWS Marketplace provider is enabled"
  value       = var.deploy_marketplace_provider
}

output "marketplace_endpoint_name" {
  description = "SageMaker endpoint name for marketplace provider"
  value       = var.deploy_marketplace_provider ? module.marketplace_provider[0].endpoint_name : ""
}

output "sagemaker_custom_enabled" {
  description = "Whether SageMaker custom provider is enabled"
  value       = var.deploy_sagemaker_custom
}

output "sagemaker_custom_endpoint_name" {
  description = "SageMaker endpoint name for custom provider"
  value       = var.deploy_sagemaker_custom ? module.sagemaker_custom[0].endpoint_name : ""
}

output "sagemaker_model_artifacts_bucket" {
  description = "S3 bucket for SageMaker model artifacts"
  value       = var.deploy_sagemaker_custom ? module.sagemaker_custom[0].model_artifacts_bucket : ""
}

# =============================================================================
# PGVECTOR AURORA OUTPUTS
# =============================================================================

output "pgvector_enabled" {
  description = "Whether pgvector Aurora is deployed"
  value       = var.deploy_pgvector
}

output "pgvector_cluster_endpoint" {
  description = "pgvector Aurora cluster endpoint"
  value       = var.deploy_pgvector ? module.pgvector[0].cluster_endpoint : ""
  sensitive   = true
}

output "pgvector_database_name" {
  description = "pgvector database name"
  value       = var.deploy_pgvector ? module.pgvector[0].database_name : ""
}

output "pgvector_secret_arn" {
  description = "Secrets Manager ARN for pgvector credentials"
  value       = var.deploy_pgvector ? module.pgvector[0].secret_arn : ""
}

output "pgvector_connection_string" {
  description = "pgvector connection string (password from Secrets Manager)"
  value       = var.deploy_pgvector ? module.pgvector[0].connection_string : ""
  sensitive   = true
}

# =============================================================================
# SAMPLE DATASETS OUTPUTS
# =============================================================================

output "sample_datasets_enabled" {
  description = "Whether sample datasets are deployed"
  value       = var.deploy_sample_datasets
}

output "sample_datasets_bucket_name" {
  description = "S3 bucket name for sample datasets"
  value       = var.deploy_sample_datasets ? module.sample_datasets[0].bucket_name : ""
}

output "sample_datasets_text_path" {
  description = "S3 path for text dataset"
  value       = var.deploy_sample_datasets ? module.sample_datasets[0].text_dataset_path : ""
}

output "sample_datasets_image_path" {
  description = "S3 path for image dataset"
  value       = var.deploy_sample_datasets ? module.sample_datasets[0].image_dataset_path : ""
}

output "sample_datasets_populate_function" {
  description = "Lambda function name for populating datasets"
  value       = var.deploy_sample_datasets ? module.sample_datasets[0].populate_lambda_function_name : ""
}

# =============================================================================
# COST ESTIMATOR OUTPUTS
# =============================================================================

output "cost_estimator_enabled" {
  description = "Whether cost estimator is deployed"
  value       = var.deploy_cost_estimator
}

output "cost_estimator_api_url" {
  description = "Cost estimator API Gateway endpoint URL"
  value       = var.deploy_cost_estimator ? module.cost_estimator[0].api_gateway_url : ""
}

output "cost_estimator_lambda_function" {
  description = "Cost estimator Lambda function name"
  value       = var.deploy_cost_estimator ? module.cost_estimator[0].lambda_function_name : ""
}

output "cost_estimator_example_curl" {
  description = "Example curl command to test cost estimator API"
  value       = var.deploy_cost_estimator ? module.cost_estimator[0].example_curl_command : ""
}

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

output "multimodal_platform_summary" {
  description = "Summary of deployed multimodal platform components"
  value = {
    embedding_providers = {
      bedrock_native = var.deploy_bedrock_native
      marketplace    = var.deploy_marketplace_provider
      sagemaker      = var.deploy_sagemaker_custom
    }
    vector_stores = {
      s3vector    = var.deploy_s3vector
      opensearch  = var.deploy_opensearch
      qdrant_ecs  = var.deploy_qdrant
      qdrant_ebs  = var.deploy_qdrant_ebs
      lancedb_s3  = var.deploy_lancedb_s3
      lancedb_efs = var.deploy_lancedb_efs
      lancedb_ebs = var.deploy_lancedb_ebs
      pgvector    = var.deploy_pgvector
    }
    support_services = {
      sample_datasets = var.deploy_sample_datasets
      cost_estimator  = var.deploy_cost_estimator
      monitoring      = var.deploy_monitoring
    }
  }
}

# =============================================================================
# MONITORING OUTPUTS
# =============================================================================

output "monitoring_enabled" {
  description = "Whether CloudWatch monitoring is deployed"
  value       = var.deploy_monitoring
}

output "monitoring_alarms_topic_arn" {
  description = "SNS topic ARN for monitoring alarms"
  value       = var.deploy_monitoring ? module.monitoring[0].alarms_topic_arn : ""
}

output "monitoring_dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = var.deploy_monitoring ? module.monitoring[0].dashboard_name : null
}

output "monitoring_dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = var.deploy_monitoring ? module.monitoring[0].dashboard_url : null
}

output "monitoring_application_log_group" {
  description = "CloudWatch log group for application logs"
  value       = var.deploy_monitoring ? module.monitoring[0].application_log_group_name : ""
}
