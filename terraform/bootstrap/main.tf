# Terraform bootstrap for the AIOps remote state backend.
#
# This module is intentionally SEPARATE from ../ (the main config) and uses LOCAL
# state. It creates the S3 bucket + DynamoDB lock table that the main config's
# `backend "s3"` block depends on. Creating those resources inside the main
# config would be a chicken-and-egg deadlock: `terraform init` needs the bucket
# to exist before it can read/write state, but the bucket is only created after
# init/apply.
#
# Usage (once, before `terraform init` in ../):
#   cd bootstrap
#   terraform init
#   terraform apply -var="aws_region=us-east-1"

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region for the state backend resources"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "S3 bucket used for Terraform remote state (must match main.tf backend)"
  type        = string
  default     = "aiops-terraform-state"
}

variable "lock_table_name" {
  description = "DynamoDB table used for Terraform state locking (must match main.tf backend)"
  type        = string
  default     = "aiops-terraform-locks"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = var.state_bucket_name

  tags = {
    Name        = var.state_bucket_name
    Environment = "production"
    Purpose     = "terraform-remote-state"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = var.lock_table_name
    Environment = "production"
    Purpose     = "terraform-state-locking"
  }
}

output "state_bucket" {
  description = "S3 bucket name for the remote backend"
  value       = aws_s3_bucket.terraform_state.id
}

output "lock_table" {
  description = "DynamoDB lock table name for the remote backend"
  value       = aws_dynamodb_table.terraform_locks.id
}
