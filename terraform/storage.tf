# NOTE: the S3 state bucket and the DynamoDB lock table that this module's
# `backend "s3"` block references are created by the *bootstrap* module in
# ./bootstrap (local state). Run that module's `terraform apply` once before the
# first `terraform init` here — creating them from this config would deadlock.

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
