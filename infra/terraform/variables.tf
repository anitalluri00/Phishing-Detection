variable "namespace" {
  description = "Kubernetes namespace for all resources."
  type        = string
  default     = "phishing-detection"
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig file used by Terraform."
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "Kubeconfig context name."
  type        = string
  default     = null
}

variable "backend_image" {
  description = "Container image for backend."
  type        = string
  default     = "phishing-backend:latest"
}

variable "frontend_image" {
  description = "Container image for frontend."
  type        = string
  default     = "phishing-frontend:latest"
}

variable "backend_replicas" {
  description = "Number of backend replicas."
  type        = number
  default     = 2
}

variable "frontend_replicas" {
  description = "Number of frontend replicas."
  type        = number
  default     = 2
}

variable "run_kubectl_apply" {
  description = "Run kubectl apply for infra/k8s manifests automatically during terraform apply."
  type        = bool
  default     = true
}

variable "k8s_manifest_dir" {
  description = "Absolute or relative directory containing namespace.yaml, backend.yaml, and frontend.yaml."
  type        = string
  default     = ""
}
