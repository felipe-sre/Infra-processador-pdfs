# Prod environment
# terraform plan -var-file="environments/prod/prod.tfvars"
# terraform apply -var-file="environments/prod/prod.tfvars"

aws_region    = "us-east-1"
environment   = "prod"
bucket_prefix = "pdf-pipeline-prod"