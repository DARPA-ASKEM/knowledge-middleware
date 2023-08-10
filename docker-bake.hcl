variable "DOCKER_REGISTRY" {
  default = "ghcr.io"
}
variable "DOCKER_ORG" {
  default = "darpa-askem"
}
variable "VERSION" {
  default = "local"
}

# ----------------------------------------------------------------------------------------------------------------------

function "tag" {
  params = [image_name, prefix, suffix]
  result = [ "${DOCKER_REGISTRY}/${DOCKER_ORG}/${image_name}:${check_prefix(prefix)}${VERSION}${check_suffix(suffix)}" ]
}

function "check_prefix" {
  params = [tag]
  result = notequal("",tag) ? "${tag}-": ""
}

function "check_suffix" {
  params = [tag]
  result = notequal("",tag) ? "-${tag}": ""
}

# ----------------------------------------------------------------------------------------------------------------------

group "prod" {
  targets = ["ta1-service-api", "ta1-service-worker"]
}

group "default" {
  targets = ["ta1-service-api-base", "ta1-service-worker-base"]
}

# ----------------------------------------------------------------------------------------------------------------------

target "_platforms" {
  platforms = ["linux/amd64", "linux/arm64"]
}

target "ta1-service-api-base" {
  context = "."
  tags = tag("ta1-service-api", "", "")
  dockerfile = "api/Dockerfile"
}

target "ta1-service-worker-base" {
  context = "."
  tags = tag("ta1-service-worker", "", "")
  dockerfile = "workers/Dockerfile"
}

target "ta1-service-api" {
  inherits = ["_platforms", "ta1-service-api-base"]
}

target "ta1-service-worker" {
  inherits = ["_platforms", "ta1-service-worker-base"]
}
