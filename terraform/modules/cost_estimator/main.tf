# =============================================================================
# Cost Estimation Module
# =============================================================================
# Provides real-time cost estimates for infrastructure configurations using
# AWS Pricing API.
#
# Features:
# - Lambda function for cost calculation
# - API Gateway endpoint for UI integration
# - AWS Pricing API integration
# - Per-resource cost breakdown
# - Monthly cost projections
#
# Estimated monthly cost: ~$0 (within free tier for most use cases)
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# IAM role for cost estimator Lambda
resource "aws_iam_role" "lambda_cost" {
  name = "${var.project_name}-cost-estimator-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-cost-estimator-lambda"
      Purpose = "Cost Estimation"
    }
  )
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_cost.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for Pricing API access
resource "aws_iam_role_policy" "pricing_api_access" {
  name = "${var.project_name}-pricing-api-access"
  role = aws_iam_role.lambda_cost.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "pricing:GetProducts",
          "pricing:DescribeServices"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda function for cost estimation
data "archive_file" "cost_estimator" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"

  source {
    content  = file("${path.module}/lambda/cost_estimator.py")
    filename = "cost_estimator.py"
  }
}

resource "aws_lambda_function" "cost_estimator" {
  filename         = data.archive_file.cost_estimator.output_path
  function_name    = "${var.project_name}-cost-estimator"
  role             = aws_iam_role.lambda_cost.arn
  handler          = "cost_estimator.handler"
  source_code_hash = data.archive_file.cost_estimator.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      PRICING_REGION = "us-east-1" # Pricing API only available in us-east-1
      CACHE_TTL      = var.cache_ttl_seconds
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.pricing_api_access
  ]

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-cost-estimator"
      Purpose = "Cost Estimation"
    }
  )
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "cost_estimator" {
  name              = "/aws/lambda/${aws_lambda_function.cost_estimator.function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Purpose = "Cost Estimator Logs"
    }
  )
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "cost_estimator_api" {
  count       = var.enable_api_gateway ? 1 : 0
  name        = "${var.project_name}-cost-estimator"
  description = "Cost estimation API for infrastructure configurations"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-cost-estimator-api"
      Purpose = "Cost Estimation API"
    }
  )
}

# API Gateway resource: /estimate
resource "aws_api_gateway_resource" "estimate" {
  count       = var.enable_api_gateway ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
  parent_id   = aws_api_gateway_rest_api.cost_estimator_api[0].root_resource_id
  path_part   = "estimate"
}

# API Gateway method: POST /estimate
resource "aws_api_gateway_method" "estimate_post" {
  count         = var.enable_api_gateway ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id   = aws_api_gateway_resource.estimate[0].id
  http_method   = "POST"
  authorization = var.enable_api_key_auth ? "API_KEY" : "NONE"
}

# API Gateway integration with Lambda
resource "aws_api_gateway_integration" "estimate_lambda" {
  count       = var.enable_api_gateway ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id = aws_api_gateway_resource.estimate[0].id
  http_method = aws_api_gateway_method.estimate_post[0].http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.cost_estimator.invoke_arn
}

# API Gateway CORS configuration
resource "aws_api_gateway_method" "estimate_options" {
  count         = var.enable_api_gateway && var.enable_cors ? 1 : 0
  rest_api_id   = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id   = aws_api_gateway_resource.estimate[0].id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "estimate_options" {
  count       = var.enable_api_gateway && var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id = aws_api_gateway_resource.estimate[0].id
  http_method = aws_api_gateway_method.estimate_options[0].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "estimate_options" {
  count       = var.enable_api_gateway && var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id = aws_api_gateway_resource.estimate[0].id
  http_method = aws_api_gateway_method.estimate_options[0].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "estimate_options" {
  count       = var.enable_api_gateway && var.enable_cors ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
  resource_id = aws_api_gateway_resource.estimate[0].id
  http_method = aws_api_gateway_method.estimate_options[0].http_method
  status_code = aws_api_gateway_method_response.estimate_options[0].status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.cors_allowed_origins}'"
  }

  depends_on = [aws_api_gateway_integration.estimate_options]
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "cost_estimator" {
  count       = var.enable_api_gateway ? 1 : 0
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.estimate[0].id,
      aws_api_gateway_method.estimate_post[0].id,
      aws_api_gateway_integration.estimate_lambda[0].id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.estimate_lambda
  ]
}

# API Gateway stage
resource "aws_api_gateway_stage" "cost_estimator" {
  count         = var.enable_api_gateway ? 1 : 0
  deployment_id = aws_api_gateway_deployment.cost_estimator[0].id
  rest_api_id   = aws_api_gateway_rest_api.cost_estimator_api[0].id
  stage_name    = var.api_stage_name

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-cost-estimator-${var.api_stage_name}"
    }
  )
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  count         = var.enable_api_gateway ? 1 : 0
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_estimator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.cost_estimator_api[0].execution_arn}/*/*"
}

# API Gateway usage plan (optional, for rate limiting)
resource "aws_api_gateway_usage_plan" "cost_estimator" {
  count = var.enable_api_gateway && var.enable_api_key_auth ? 1 : 0
  name  = "${var.project_name}-cost-estimator-usage-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.cost_estimator_api[0].id
    stage  = aws_api_gateway_stage.cost_estimator[0].stage_name
  }

  quota_settings {
    limit  = var.api_quota_limit
    period = "DAY"
  }

  throttle_settings {
    burst_limit = var.api_burst_limit
    rate_limit  = var.api_rate_limit
  }

  tags = var.tags
}
