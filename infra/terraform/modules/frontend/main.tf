resource "kubernetes_deployment_v1" "frontend" {
  metadata {
    name      = "frontend"
    namespace = var.namespace
    labels = { app = "frontend" }
  }

  spec {
    replicas = var.replicas

    selector {
      match_labels = { app = "frontend" }
    }

    template {
      metadata {
        labels = { app = "frontend" }
      }

      spec {
        container {
          name              = "frontend"
          image             = var.image
          image_pull_policy = "IfNotPresent"

          security_context {
            run_as_non_root            = true
            allow_privilege_escalation = false
            capabilities { drop = ["ALL"] }
          }

          env {
            name  = "BACKEND_UPSTREAM"
            value = var.backend_upstream
          }

          port {
            container_port = var.container_port
          }

          readiness_probe {
            http_get {
              path = "/health"
              port = var.container_port
            }
            initial_delay_seconds = 5
            period_seconds        = 10
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = var.container_port
            }
            initial_delay_seconds = 15
            period_seconds        = 20
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "frontend" {
  metadata {
    name      = "frontend"
    namespace = var.namespace
    labels = { app = "frontend" }
  }

  spec {
    selector = { app = "frontend" }
    type     = "LoadBalancer"

    port {
      name        = "http"
      port        = var.service_port
      target_port = var.container_port
      protocol    = "TCP"
    }
  }
}
