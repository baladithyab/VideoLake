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
    deployed                 = true
    deployment_name          = var.qdrant_deployment_name
    cluster_arn              = module.qdrant[0].cluster_arn
    service_name             = module.qdrant[0].service_name
    security_group_id        = module.qdrant[0].security_group_id
    endpoint_discovery       = module.qdrant[0].endpoint_discovery_command
    rest_api_port            = module.qdrant[0].rest_api_port
    grpc_port                = module.qdrant[0].grpc_port
    efs_id                   = module.qdrant[0].efs_id
    deployment_info          = module.qdrant[0].deployment_info
    note                     = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message                  = ""
  } : {
    deployed                 = false
    deployment_name          = ""
    cluster_arn              = ""
    service_name             = ""
    security_group_id        = ""
    endpoint_discovery       = ""
    rest_api_port            = 0
    grpc_port                = 0
    efs_id                   = ""
    deployment_info          = {}
    note                     = ""
    message                  = "Qdrant not deployed. Set var.deploy_qdrant=true to enable."
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
    deployed              = true
    deployment_name       = "${var.lancedb_deployment_name}-s3"
    backend_type          = "s3"
    cluster_arn           = module.lancedb_s3[0].cluster_arn
    service_name          = module.lancedb_s3[0].service_name
    security_group_id     = module.lancedb_s3[0].security_group_id
    s3_bucket_name        = module.lancedb_s3[0].s3_bucket_name
    endpoint_discovery    = module.lancedb_s3[0].endpoint_discovery_command
    deployment_info       = module.lancedb_s3[0].deployment_info
    note                  = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message               = ""
  } : {
    deployed              = false
    deployment_name       = ""
    backend_type          = ""
    cluster_arn           = ""
    service_name          = ""
    security_group_id     = ""
    s3_bucket_name        = ""
    endpoint_discovery    = ""
    deployment_info       = {}
    note                  = ""
    message               = "LanceDB S3 not deployed. Set var.deploy_lancedb_s3=true to enable."
  }
}

output "lancedb_efs" {
  description = "LanceDB EFS backend deployment"
  value = var.deploy_lancedb_efs ? {
    deployed              = true
    deployment_name       = "${var.lancedb_deployment_name}-efs"
    backend_type          = "efs"
    cluster_arn           = module.lancedb_efs[0].cluster_arn
    service_name          = module.lancedb_efs[0].service_name
    security_group_id     = module.lancedb_efs[0].security_group_id
    efs_id                = module.lancedb_efs[0].efs_id
    endpoint_discovery    = module.lancedb_efs[0].endpoint_discovery_command
    deployment_info       = module.lancedb_efs[0].deployment_info
    note                  = "Use endpoint_discovery_command to get the current task IP (dynamic IP on ECS)"
    message               = ""
  } : {
    deployed              = false
    deployment_name       = ""
    backend_type          = ""
    cluster_arn           = ""
    service_name          = ""
    security_group_id     = ""
    efs_id                = ""
    endpoint_discovery    = ""
    deployment_info       = {}
    note                  = ""
    message               = "LanceDB EFS not deployed. Set var.deploy_lancedb_efs=true to enable."
  }
}

output "lancedb_ebs" {
  description = "LanceDB EBS backend deployment (EC2 with dedicated EBS volume)"
  value = var.deploy_lancedb_ebs ? {
    deployed              = true
    deployment_name       = "${var.lancedb_deployment_name}-ebs"
    backend_type          = "ebs"
    deployment_type       = "ec2"
    instance_id           = module.lancedb_ebs[0].instance_id
    public_ip             = module.lancedb_ebs[0].public_ip
    private_ip            = module.lancedb_ebs[0].private_ip
    endpoint              = module.lancedb_ebs[0].endpoint
    lancedb_api_url       = module.lancedb_ebs[0].lancedb_api_url
    ebs_volume_id         = module.lancedb_ebs[0].ebs_volume_id
    security_group_id     = module.lancedb_ebs[0].security_group_id
    deployment_info       = module.lancedb_ebs[0].deployment_info
    note                  = "True EC2+EBS deployment with direct endpoint access"
    message               = ""
  } : {
    deployed              = false
    deployment_name       = ""
    backend_type          = ""
    deployment_type       = ""
    instance_id           = ""
    public_ip             = ""
    private_ip            = ""
    endpoint              = ""
    lancedb_api_url       = ""
    ebs_volume_id         = ""
    security_group_id     = ""
    deployment_info       = {}
    note                  = ""
    message               = "LanceDB EBS not deployed. Set var.deploy_lancedb_ebs=true to enable."
  }
}

output "lancedb_benchmark_ec2" {
  description = "LanceDB benchmark EC2 host for embedded vs API testing"
  value = var.deploy_lancedb_benchmark_ec2 ? {
    deployed        = true
    deployment_name = "${var.lancedb_deployment_name}-benchmark"
    instance_id     = module.lancedb_benchmark_ec2[0].instance_id
    public_ip       = module.lancedb_benchmark_ec2[0].public_ip
    private_ip      = module.lancedb_benchmark_ec2[0].private_ip
    security_group  = module.lancedb_benchmark_ec2[0].security_group_id
    note            = "SSH to this instance to run scripts/run_lancedb_embedded_vs_api_benchmarks.sh"
  } : {
    deployed        = false
    deployment_name = ""
    instance_id     = ""
    public_ip       = ""
    private_ip      = ""
    security_group  = ""
    note            = "Set var.deploy_lancedb_benchmark_ec2=true to create the EC2 benchmark host."
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
      qdrant_ebs     = var.deploy_qdrant_ebs
      lancedb_s3     = var.deploy_lancedb_s3
      lancedb_efs    = var.deploy_lancedb_efs
      lancedb_ebs    = var.deploy_lancedb_ebs
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
    shared_bucket = local.shared_bucket_name
    data_bucket = var.data_bucket_name != null ? var.data_bucket_name : "not_deployed"
    s3vector = var.deploy_s3vector ? var.s3vector_bucket_name : "not_deployed"
    opensearch_domain = var.deploy_opensearch ? var.opensearch_domain_name : "not_deployed"
    qdrant_deployment     = var.deploy_qdrant ? var.qdrant_deployment_name : "not_deployed"
    qdrant_ebs_deployment = var.deploy_qdrant_ebs ? "${var.qdrant_deployment_name}-ebs" : "not_deployed"
    lancedb_deployments = {
      s3  = var.deploy_lancedb_s3 ? "${var.lancedb_deployment_name}-s3" : "not_deployed"
      efs = var.deploy_lancedb_efs ? "${var.lancedb_deployment_name}-efs" : "not_deployed"
      ebs = var.deploy_lancedb_ebs ? "${var.lancedb_deployment_name}-ebs" : "not_deployed"
    }
  }
}
