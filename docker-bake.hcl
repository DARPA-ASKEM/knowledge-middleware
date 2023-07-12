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
  targets = ["extraction-service"]
}

group "default" {
  targets = ["extraction-service-base"]
}

# ----------------------------------------------------------------------------------------------------------------------

target "_platforms" {
  platforms = ["linux/amd64", "linux/arm64"]
}

target "extraction-service-api-base" {
  context = "."
  tags = tag("extraction-service-api", "", "")
  dockerfile = "api/Dockerfile"
}

target "extraction-service-worker-base" {
  context = "."
  tags = tag("extraction-service-worker", "", "")
  dockerfile = "workers/Dockerfile"
}

target "extraction-service-api" {
  inherits = ["_platforms", "extraction-service-api-base"]
}

target "extraction-service-worker" {
  inherits = ["_platforms", "extraction-service-worker-base"]
}
