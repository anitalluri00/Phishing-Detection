output "service_name" {
  value = kubernetes_service_v1.frontend.metadata[0].name
}

output "service_port" {
  value = kubernetes_service_v1.frontend.spec[0].port[0].port
}
