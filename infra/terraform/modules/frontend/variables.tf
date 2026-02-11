variable "namespace" {
  type = string
}

variable "image" {
  type = string
}

variable "backend_upstream" {
  type = string
}

variable "replicas" {
  type    = number
  default = 2
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "service_port" {
  type    = number
  default = 80
}
