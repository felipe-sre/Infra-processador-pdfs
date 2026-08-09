# ------------------------------------------------------------------------------
# ARMAZENAMENTO (S3)
# ------------------------------------------------------------------------------
output "input_bucket_name" {
  description = "Nome do bucket S3 de entrada para upload dos PDFs"
  value       = aws_s3_bucket.input_bucket.bucket
}

output "output_bucket_name" {
  description = "Nome do bucket S3 de saída para os resultados extraídos em JSON"
  value       = aws_s3_bucket.output_bucket.bucket
}

# ------------------------------------------------------------------------------
# FILAS (SQS)
# ------------------------------------------------------------------------------
output "sqs_queue_url" {
  description = "URL da fila SQS principal para acionamento do pipeline"
  value       = aws_sqs_queue.pdf_queue.id
}

output "sqs_queue_arn" {
  description = "ARN da fila SQS principal"
  value       = aws_sqs_queue.pdf_queue.arn
}

output "sqs_dlq_url" {
  description = "URL da Dead Letter Queue (DLQ) para investigação SRE"
  value       = aws_sqs_queue.dlq.id
}

# ------------------------------------------------------------------------------
# COMPUTAÇÃO (AWS Lambda)
# ------------------------------------------------------------------------------
output "lambda_function_name" {
  description = "Nome da função AWS Lambda responsável pelo processamento"
  value       = aws_lambda_function.pdf_processor.function_name
}

output "lambda_function_arn" {
  description = "ARN da função AWS Lambda"
  value       = aws_lambda_function.pdf_processor.arn
}