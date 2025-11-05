# Terraform Outputs - All module outputs are placeholders until modules have outputs defined
# These would be populated once all module output files are created

output "infrastructure_deployed" {
  description = "Summary of deployed infrastructure"
  value = {
    data_bucket = var.data_bucket_name
    s3vector = var.s3vector_bucket_name
    opensearch_domain = var.opensearch_domain_name
    qdrant_deployment = var.qdrant_deployment_name
    lancedb_deployments = {
      s3 = "${var.lancedb_deployment_name}-s3"
      efs = "${var.lancedb_deployment_name}-efs"
      ebs = "${var.lancedb_deployment_name}-ebs"
    }
  }
}
