# =============================================================================
# CloudWatch Monitoring Module Variables
# =============================================================================

variable "deployment_name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
  default     = ""
  sensitive   = true
}

# ALB Configuration
variable "alb_name" {
  description = "Name of the ALB to monitor"
  type        = string
  default     = ""
}

variable "alb_arn_suffix" {
  description = "ARN suffix of the ALB (from ALB ARN)"
  type        = string
  default     = ""
}

variable "target_group_arn_suffix" {
  description = "ARN suffix of the target group"
  type        = string
  default     = ""
}

variable "alb_5xx_threshold" {
  description = "Threshold for ALB 5xx errors"
  type        = number
  default     = 10
}

# ECS Configuration
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster to monitor"
  type        = string
  default     = ""
}

variable "ecs_service_name" {
  description = "Name of the ECS service to monitor"
  type        = string
  default     = ""
}

variable "ecs_cpu_threshold" {
  description = "CPU utilization threshold percentage"
  type        = number
  default     = 80
}

variable "ecs_memory_threshold" {
  description = "Memory utilization threshold percentage"
  type        = number
  default     = 80
}

variable "ecs_min_task_count" {
  description = "Minimum number of running tasks"
  type        = number
  default     = 1
}

# NAT Gateway Configuration
variable "nat_gateway_ids" {
  description = "List of NAT Gateway IDs to monitor"
  type        = list(string)
  default     = []
}

# Dashboard Configuration
variable "create_dashboard" {
  description = "Create CloudWatch dashboard"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
