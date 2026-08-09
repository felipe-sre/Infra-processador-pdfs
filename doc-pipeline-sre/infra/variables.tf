variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Região da AWS para o deploy"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Ambiente da aplicação"
}

variable "bucket_prefix" {
  type        = string
  default     = "pdf-pipeline"
  description = "Prefixo para os buckets do S3"
}