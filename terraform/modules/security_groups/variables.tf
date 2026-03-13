# =============================================================================
# Security Groups Module Variables
# =============================================================================

variable "deployment_name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC (for VPC endpoint security group)"
  type        = string
}

variable "create_rds_security_group" {
  description = "Whether to create RDS security group"
  type        = bool
  default     = false
}

variable "create_vpc_endpoint_security_group" {
  description = "Whether to create VPC endpoint security group"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
