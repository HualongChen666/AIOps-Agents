output "argocd_url" {
  description = "ArgoCD server URL"
  value       = "https://argocd.${var.domain_name}"
}

output "s3_bucket_terraform_state" {
  description = "Terraform state S3 bucket"
  value       = aws_s3_bucket.terraform_state.id
}

output "s3_bucket_aiops_data" {
  description = "AIOps data S3 bucket"
  value       = aws_s3_bucket.aiops_data.id
}

output "dynamodb_table_locks" {
  description = "DynamoDB table for locks"
  value       = aws_dynamodb_table.terraform_locks.id
}
