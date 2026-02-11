output "namespace" {
  value       = kubernetes_namespace_v1.app.metadata[0].name
  description = "Namespace used for deployment."
}

output "backend_service_name" {
  value       = module.backend.service_name
  description = "Backend service name."
}

output "backend_service_port" {
  value       = module.backend.service_port
  description = "Backend service port."
}

output "frontend_service_name" {
  value       = module.frontend.service_name
  description = "Frontend service name."
}

output "frontend_service_port" {
  value       = module.frontend.service_port
  description = "Frontend service port."
}
