terraform {
  backend "s3" {
    bucket = "proc-pdfs-bucket-tfstate" # Informe o nome do seu bucket de estado S3
    key    = "pipeline-pdfs/dev/terraform.tfstate"
    region = "us-east-1"
  }
}