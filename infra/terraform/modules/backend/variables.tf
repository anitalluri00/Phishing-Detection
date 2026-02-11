variable "namespace" {
  type = string
}

variable "image" {
  type = string
}

variable "replicas" {
  type    = number
  default = 2
}

variable "container_port" {
  type    = number
  default = 5000
}

variable "service_port" {
  type    = number
  default = 5000
}
