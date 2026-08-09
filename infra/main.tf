# 1. ARMAZENAMENTO (S3 Buckets)
resource "aws_s3_bucket" "input_bucket" {
  bucket        = "${var.bucket_prefix}-input-${var.environment}"
  force_destroy = true
}

resource "aws_s3_bucket" "output_bucket" {
  bucket        = "${var.bucket_prefix}-output-${var.environment}"
  force_destroy = true
}

# 2. FILAS (SQS + Dead Letter Queue)
resource "aws_sqs_queue" "dlq" {
  name                      = "pdf-processing-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 dias
}

resource "aws_sqs_queue" "pdf_queue" {
  name                       = "pdf-processing-queue-${var.environment}"
  visibility_timeout_seconds = 300 # Tempo para a Lambda processar a mensagem

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3 # Envia para DLQ após 3 falhas (Resiliência SRE)
  })
}

# 3. IAM ROLE E POLÍTICAS DA LAMBDA
resource "aws_iam_role" "lambda_role" {
  name = "pdf_processor_lambda_role_${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Permissões Básicas (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Permissões de Consumo da Fila SQS
resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# Política Específica para Leitura/Escrita nos Buckets S3 (Menor Privilégio)
resource "aws_iam_policy" "lambda_s3_policy" {
  name        = "pdf_processor_s3_policy_${var.environment}"
  description = "Acesso de leitura no bucket de entrada e escrita no bucket de saída"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.input_bucket.arn,
          "${aws_s3_bucket.input_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.output_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

# 4. COMPUTAÇÃO (AWS Lambda)
data "archive_file" "lambda_dummy_zip" {
  type        = "zip"
  output_path = "${path.module}/dummy_lambda.zip"

  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200}"
    filename = "main.py"
  }
}

resource "aws_lambda_function" "pdf_processor" {
  filename         = data.archive_file.lambda_dummy_zip.output_path
  function_name    = "pdf-processor-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      OUTPUT_BUCKET = aws_s3_bucket.output_bucket.bucket
      ENVIRONMENT   = var.environment
    }
  }
}

# Trigger: SQS Event Source Mapping -> Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.pdf_queue.arn
  function_name    = aws_lambda_function.pdf_processor.arn
  batch_size       = 1
}