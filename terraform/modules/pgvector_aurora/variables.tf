# =============================================================================
# pgvector Aurora Serverless - Variables
# =============================================================================

variable "deployment_name" {
  description = "Name of the deployment (used for resource naming)"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod) - affects backup and deletion settings"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "postgres_version" {
  description = "Aurora PostgreSQL engine version (must support pgvector)"
  type        = string
  default     = "15.4"

  validation {
    condition     = can(regex("^1[45]\\.", var.postgres_version))
    error_message = "PostgreSQL version must be 14.x or 15.x (required for pgvector support)."
  }
}

variable "database_name" {
  description = "Name of the database"
  type        = string
  default     = "vectors"
}

variable "master_username" {
  description = "Master username for the database"
  type        = string
  default     = "vectoradmin"

  validation {
    condition     = length(var.master_username) >= 1 && length(var.master_username) <= 16
    error_message = "Master username must be between 1 and 16 characters."
  }
}

variable "master_password" {
  description = "Master password for the database (leave empty to auto-generate)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "min_acu" {
  description = "Minimum Aurora Capacity Units (0.5-128)"
  type        = number
  default     = 0.5

  validation {
    condition     = var.min_acu >= 0.5 && var.min_acu <= 128
    error_message = "Minimum ACU must be between 0.5 and 128."
  }
}

variable "max_acu" {
  description = "Maximum Aurora Capacity Units (0.5-128)"
  type        = number
  default     = 2

  validation {
    condition     = var.max_acu >= 0.5 && var.max_acu <= 128
    error_message = "Maximum ACU must be between 0.5 and 128."
  }

  validation {
    condition     = var.max_acu >= var.min_acu
    error_message = "Maximum ACU must be greater than or equal to minimum ACU."
  }
}

variable "instance_count" {
  description = "Number of Aurora instances (1 for single-AZ, 2+ for multi-AZ HA)"
  type        = number
  default     = 1

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 15
    error_message = "Instance count must be between 1 and 15."
  }
}

variable "embedding_dimension" {
  description = "Vector dimension for pgvector index"
  type        = number
  default     = 1536

  validation {
    condition     = var.embedding_dimension > 0 && var.embedding_dimension <= 16000
    error_message = "Embedding dimension must be between 1 and 16000."
  }
}

variable "vpc_id" {
  description = "VPC ID for the Aurora cluster"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the Aurora cluster"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least 2 private subnets are required for Aurora cluster."
  }
}

variable "allowed_security_groups" {
  description = "List of security group IDs allowed to access the database"
  type        = list(string)
  default     = []
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 1 and 35 days."
  }
}

variable "preferred_backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "preferred_maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
