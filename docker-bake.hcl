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
  targets = ["knowledge-middleware-api", "knowledge-middleware-worker", "knowledge-middleware-report"]
}

group "default" {
  targets = ["knowledge-middleware-api-base", "knowledge-middleware-worker-base", "knowledge-middleware-report-base"]
}

# ----------------------------------------------------------------------------------------------------------------------

target "_platforms" {
  platforms = ["linux/amd64", "linux/arm64"]
}

target "knowledge-middleware-api-base" {
  context = "."
  tags = tag("knowledge-middleware-api", "", "")
  dockerfile = "api/Dockerfile"
}

target "knowledge-middleware-worker-base" {
  context = "."
  tags = tag("knowledge-middleware-worker", "", "")
  dockerfile = "worker/Dockerfile"
}

target "knowledge-middleware-report-base" {
	context = "."
	tags = tag("knowledge-middleware-report", "", "")
	dockerfile = "Dockerfile.report"
}

target "knowledge-middleware-api" {
  inherits = ["_platforms", "knowledge-middleware-api-base"]
}

target "knowledge-middleware-worker" {
  inherits = ["_platforms", "knowledge-middleware-worker-base"]
}

target "knowledge-middleware-report" {
	inherits = ["_platforms", "knowledge-middleware-report-base"]
}
