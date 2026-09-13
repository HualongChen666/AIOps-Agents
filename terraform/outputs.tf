output "argocd_url" {
  description = "ArgoCD server URL"
  value       = "https://argocd.${var.domain_name}"
}

output "s3_bucket_aiops_data" {
  description = "AIOps data S3 bucket"
  value       = aws_s3_bucket.aiops_data.id
}
