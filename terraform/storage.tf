# S3 Bucket for Terraform State
resource "aws_s3_bucket" "terraform_state" {
  bucket = "aiops-terraform-state"

  tags = {
    Name        = "aiops-terraform-state"
    Environment = "production"
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

# DynamoDB Table for Terraform Locks
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "aiops-terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "aiops-terraform-locks"
    Environment = "production"
  }
}

# S3 Bucket for AIOps Data
resource "aws_s3_bucket" "aiops_data" {
  bucket = "aiops-data-bucket"

  tags = {
    Name        = "aiops-data-bucket"
    Environment = "production"
  }
}

resource "aws_s3_bucket_versioning" "aiops_data" {
  bucket = aws_s3_bucket.aiops_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "aiops_data" {
  bucket = aws_s3_bucket.aiops_data.id

  rule {
    id     = "cold-storage-transition"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 365
    }
  }
}
