variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
}

variable "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  type        = string
}

variable "ingestion_task_definition_arn" {
  description = "ARN of the ingestion task definition"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ECS task"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for the ECS task"
  type        = string
}

resource "aws_iam_role" "step_function_role" {
  name = "${var.project_name}-${var.environment}-ingestion-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "step_function_policy" {
  name = "${var.project_name}-${var.environment}-ingestion-sfn-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          var.ingestion_task_definition_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:StopTask",
          "ecs:DescribeTasks"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = [
          "arn:aws:events:*:*:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*" # Ideally restrict to the Task Execution Role
        Condition = {
          StringLike = {
            "iam:PassedToService": "ecs-tasks.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_function_policy_attach" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

resource "aws_sfn_state_machine" "ingestion_pipeline" {
  name     = "${var.project_name}-${var.environment}-ingestion-pipeline"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/../../../src/ingestion/step_function_definition.json", {
    ECS_CLUSTER_ARN    = var.ecs_cluster_arn
    INGESTION_TASK_ARN = var.ingestion_task_definition_arn
    SUBNET_1           = var.subnet_ids[0]
    SUBNET_2           = length(var.subnet_ids) > 1 ? var.subnet_ids[1] : var.subnet_ids[0]
    SECURITY_GROUP     = var.security_group_id
  })
}

output "state_machine_arn" {
  value = aws_sfn_state_machine.ingestion_pipeline.arn
}