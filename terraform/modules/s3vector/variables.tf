# S3Vector Module Variables

variable "bucket_name" {
  description = "Name of the S3 Vector bucket (not a regular S3 bucket!)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "kms_key_id" {
  description = "KMS key ARN for encryption (optional)"
  type        = string
  default     = null
}

variable "default_index_name" {
  description = "Name of the default vector index to create"
  type        = string
  default     = "embeddings"
}

variable "vector_dimension" {
  description = "Dimension of vectors (e.g., 384 for MiniLM, 768 for BERT, 1536 for OpenAI)"
  type        = number
  default     = 1536
}

variable "vector_data_type" {
  description = "Data type for vectors (float32, float16, int8)"
  type        = string
  default     = "float32"

  validation {
    condition     = contains(["float32", "float16", "int8"], var.vector_data_type)
    error_message = "vector_data_type must be one of: float32, float16, int8"
  }
}

variable "distance_metric" {
  description = "Distance metric for similarity search (cosine, euclidean, dot_product)"
  type        = string
  default     = "cosine"

  validation {
    condition     = contains(["cosine", "euclidean", "dot_product"], var.distance_metric)
    error_message = "distance_metric must be one of: cosine, euclidean, dot_product"
  }
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
