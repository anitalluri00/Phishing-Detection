terraform {
  required_version = ">= 1.4.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.27.0"
    }
  }
}

provider "kubernetes" {
  config_path    = pathexpand(var.kubeconfig_path)
  config_context = var.kubeconfig_context
}

locals {
  k8s_manifest_dir   = var.k8s_manifest_dir != "" ? var.k8s_manifest_dir : "${path.module}/../k8s"
  kubectl_context_arg = var.kubeconfig_context != null && trim(var.kubeconfig_context) != "" ? "--context=${var.kubeconfig_context}" : ""
  manifest_hash = sha256(join(",", [
    for f in sort(fileset(local.k8s_manifest_dir, "*.yaml")) : filesha256("${local.k8s_manifest_dir}/${f}")
  ]))
}

resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.namespace
  }
}

module "backend" {
  source = "./modules/backend"

  namespace = kubernetes_namespace_v1.app.metadata[0].name
  image     = var.backend_image
  replicas  = var.backend_replicas
}

module "frontend" {
  source = "./modules/frontend"

  namespace        = kubernetes_namespace_v1.app.metadata[0].name
  image            = var.frontend_image
  replicas         = var.frontend_replicas
  backend_upstream = "http://${module.backend.service_name}:${module.backend.service_port}"
}

resource "terraform_data" "kubectl_apply" {
  count = var.run_kubectl_apply ? 1 : 0

  triggers_replace = [
    local.manifest_hash,
    var.backend_image,
    var.frontend_image,
    tostring(var.backend_replicas),
    tostring(var.frontend_replicas),
    var.namespace,
    pathexpand(var.kubeconfig_path),
    var.kubeconfig_context != null ? var.kubeconfig_context : "",
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      kubectl --kubeconfig "${pathexpand(var.kubeconfig_path)}" ${local.kubectl_context_arg} apply -f "${local.k8s_manifest_dir}/namespace.yaml"
      kubectl --kubeconfig "${pathexpand(var.kubeconfig_path)}" ${local.kubectl_context_arg} apply -f "${local.k8s_manifest_dir}/backend.yaml"
      kubectl --kubeconfig "${pathexpand(var.kubeconfig_path)}" ${local.kubectl_context_arg} apply -f "${local.k8s_manifest_dir}/frontend.yaml"
    EOT
  }

  depends_on = [module.backend, module.frontend]
}
