terraform {
  required_version = ">= 1.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    argocd = {
      source  = "oboukili/argocd"
      version = "~> 6.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket         = "aiops-terraform-state"
    key            = "aiops-infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "aiops-terraform-locks"
  }
}

provider "kubernetes" {
  config_path = var.kube_config_path
}

provider "helm" {
  kubernetes {
    config_path = var.kube_config_path
  }
}

provider "argocd" {
  server_addr = var.argocd_server_addr
  auth_token  = var.argocd_auth_token
  insecure    = true
}

provider "aws" {
  region = var.aws_region
}

variable "kube_config_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "argocd_server_addr" {
  description = "ArgoCD server address"
  type        = string
  default     = "argocd-server.argocd.svc.cluster.local:443"
}

variable "argocd_auth_token" {
  description = "ArgoCD auth token"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Kubernetes cluster name"
  type        = string
  default     = "aiops-cluster"
}

variable "domain_name" {
  description = "Domain name for applications"
  type        = string
  default     = "aiops.example.com"
}
