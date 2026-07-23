# ArgoCD Application of Applications
resource "argocd_application" "aiops" {
  metadata {
    name      = "aiops"
    namespace = "argocd"
    labels = {
      app = "aiops"
    }
  }

  spec {
    source {
      repo_url        = "https://github.com/your-org/aiops-agent.git"
      target_revision = "main"
      path            = "helm/aiops-agent"
    }

    destination {
      server    = "https://kubernetes.default.svc"
      namespace = "aiops"
    }

    sync_policy {
      automated {
        prune       = true
        self_heal   = true
        allow_empty = false
      }
      sync_options = [
        "CreateNamespace=true"
      ]
    }
  }
}

# ArgoCD Project
resource "argocd_project" "aiops" {
  metadata {
    name      = "aiops"
    namespace = "argocd"
  }

  spec {
    description = "AIOps Agent Project"
    source_repos {
      repo_url = "https://github.com/your-org/aiops-agent.git"
    }
    destinations {
      server    = "https://kubernetes.default.svc"
      namespace = "aiops"
    }
    cluster_resource_whitelist {
      group = "*"
      kind  = "*"
    }
  }
}
