# Dev environment
# terraform plan -var-file="environments/dev/dev.tfvars"
# terraform apply -var-file="environments/dev/dev.tfvars"

aws_region    = "us-east-1"
environment   = "dev"
bucket_prefix = "pdf-pipeline-dev"