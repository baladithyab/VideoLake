# =============================================================================
# Sample Datasets Module - Variables
# =============================================================================

variable "project_name" {
  description = "Project name (used for resource naming)"
  type        = string
}

variable "auto_populate" {
  description = "Automatically populate datasets on first deployment"
  type        = bool
  default     = false
}

variable "enable_lifecycle" {
  description = "Enable lifecycle policy to archive old datasets to Glacier"
  type        = bool
  default     = true
}

variable "enable_text_dataset" {
  description = "Enable text dataset population"
  type        = bool
  default     = true
}

variable "enable_image_dataset" {
  description = "Enable image dataset population"
  type        = bool
  default     = false
}

variable "enable_audio_dataset" {
  description = "Enable audio dataset population"
  type        = bool
  default     = false
}

variable "enable_video_dataset" {
  description = "Enable video dataset population"
  type        = bool
  default     = false
}

variable "text_dataset_size" {
  description = "Number of text passages to include (max 10000)"
  type        = number
  default     = 10000

  validation {
    condition     = var.text_dataset_size > 0 && var.text_dataset_size <= 100000
    error_message = "Text dataset size must be between 1 and 100000."
  }
}

variable "image_dataset_size" {
  description = "Number of images to include (max 1000)"
  type        = number
  default     = 1000

  validation {
    condition     = var.image_dataset_size > 0 && var.image_dataset_size <= 10000
    error_message = "Image dataset size must be between 1 and 10000."
  }
}

variable "audio_dataset_size" {
  description = "Number of audio clips to include (max 100)"
  type        = number
  default     = 100

  validation {
    condition     = var.audio_dataset_size > 0 && var.audio_dataset_size <= 1000
    error_message = "Audio dataset size must be between 1 and 1000."
  }
}

variable "video_dataset_size" {
  description = "Number of video clips to include (max 50)"
  type        = number
  default     = 50

  validation {
    condition     = var.video_dataset_size > 0 && var.video_dataset_size <= 500
    error_message = "Video dataset size must be between 1 and 500."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
