SHELL = /bin/bash
LANG = en_US.utf-8
PYTHON = $(shell which python3.10 || which python3 || which python)
DOCKER = $(shell which docker)
DOCKER_COMPOSE = $(shell $(DOCKER) compose > /dev/null && echo "$(DOCKER) compose" || which docker-compose)
export LANG

# Initializes submodules and copies environment file sample to env file.
.PHONY:init
init:.env
	@if (poetry -q > /dev/null); then \
		poetry install; \
		poetry run pre-commit install; \
		git submodule update --init; \
	else \
		echo -en "This app requires the Poetry Python package manager.\nWould you like to try to install it automatically? [y/N] "; \
		read i; \
		if [[ "$$i" == "y" || "$$i" == "Y" ]]; then \
			$(PYTHON) -m pip install poetry; \
		else \
			echo "Please see the official documentation for further instructions: https://python-poetry.org/docs/#installation"; \
		fi; \
	fi

# Environment file copy
.env:
ifeq ($(wildcard envfile),)
	cp env.sample .env; \
	echo -e "\nDon't forget to update 'envfile' with all your secrets!";
endif

# Turn project on
.PHONY:up
up:docker-compose.yaml
	$(DOCKER_COMPOSE) up -d

# Rebuild all containers and turn project on
.PHONY:up-rebuild
up-rebuild:docker-compose.yaml
	$(DOCKER_COMPOSE) up --build -d

# Turn project off
.PHONY:down
down:docker-compose.yaml
	$(DOCKER_COMPOSE) down

# Restart project
.PHONY:restart
restart:docker-compose.yaml
	make down && make up


# Turn project on for production
# No internal docker connection to TDS
.PHONY:up-prod
up-prod:docker-compose.yaml
	$(DOCKER_COMPOSE) -f docker-compose.prod.yaml up -d

