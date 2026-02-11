resource "kubernetes_deployment_v1" "backend" {
  metadata {
    name      = "backend"
    namespace = var.namespace
    labels = { app = "backend" }
  }

  spec {
    replicas = var.replicas

    selector {
      match_labels = { app = "backend" }
    }

    template {
      metadata {
        labels = { app = "backend" }
      }

      spec {
        container {
          name              = "backend"
          image             = var.image
          image_pull_policy = "IfNotPresent"

          security_context {
            run_as_non_root            = true
            allow_privilege_escalation = false
            capabilities { drop = ["ALL"] }
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

resource "kubernetes_service_v1" "backend" {
  metadata {
    name      = "backend"
    namespace = var.namespace
    labels = { app = "backend" }
  }

  spec {
    selector = { app = "backend" }
    type     = "ClusterIP"

    port {
      name        = "http"
      port        = var.service_port
      target_port = var.container_port
      protocol    = "TCP"
    }
  }
}
