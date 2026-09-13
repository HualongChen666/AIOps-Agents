# Terraform — AIOps Agent infrastructure

Provisioning for the AWS S3/DynamoDB resources and the ArgoCD GitOps application
that deploys the AIOps Agent Helm chart (`helm/aiops-agent`).

## Layout

| Path | Purpose | State |
|------|---------|-------|
| `bootstrap/` | Creates the S3 state bucket + DynamoDB lock table | **local** |
| `./` (this dir) | ArgoCD application/project + AIOps data bucket | **S3 remote** (created by `bootstrap/`) |

`main.tf` declares a `backend "s3"` block that points at the bucket/table created
by `bootstrap/`. Those resources intentionally live in the bootstrap module: if
they were created here, the first `terraform init` could never run (the bucket
must exist before init can read/write state). See `bootstrap/main.tf`.

## Order of operations

```bash
# 1) one-time: create the remote state backend (uses local state)
cd bootstrap
terraform init
terraform apply -var="aws_region=us-east-1"

# 2) main config (uses the remote S3 backend)
cd ..
terraform init
terraform apply \
  -var="argocd_auth_token=$ARGOCD_TOKEN" \
  -var="gitops_repo_url=https://github.com/HualongChen666/AIOps-Agents.git"
```

## Key variables

| Variable | Default | Notes |
|----------|---------|-------|
| `gitops_repo_url` | `https://github.com/HualongChen666/AIOps-Agents.git` | ArgoCD source repo |
| `gitops_target_revision` | `main` | tracked branch/tag |
| `gitops_path` | `helm/aiops-agent` | chart path in the repo |
| `argocd_server_addr` | `argocd-server.argocd.svc.cluster.local:443` | ArgoCD API |
| `argocd_auth_token` | *(required, sensitive)* | ArgoCD API token |
| `aws_region` | `us-east-1` | AWS region |
