# File: Makefile

COMPOSE_DEV = docker compose -f docker-compose.dev.yaml
COMPOSE_PROD = docker compose -f docker-compose.prod.yaml
SERVICE = backend
timestamp = $(shell date +%Y_%m_%d_%H%M)
# ================================
# ========== Development ==========
# ================================
build-dev:
	$(COMPOSE_DEV) build
up-dev:
	$(COMPOSE_DEV) up -d
deploy-dev:
	$(COMPOSE_DEV) up -d --build
healthcheck-dev:
	$(COMPOSE_DEV) ps | grep healthy
## ========== Database ==========
db-migrate-dev:
	$(COMPOSE_DEV) exec $(SERVICE) alembic revision --autogenerate -m "dev migration_$(timestamp)"

db-upgrade-dev:
	$(COMPOSE_DEV) exec $(SERVICE) alembic upgrade head
## Optional: status, logs, or bash
bash-dev:
	$(COMPOSE_DEV) exec $(SERVICE) sh
logs-dev:
	$(COMPOSE_DEV) logs -f $(SERVICE)
# ================================
# ========== Production ==========
# ================================
build-prod:
	$(COMPOSE_PROD) build
up-prod:
	$(COMPOSE_PROD) up -d
deploy-prod:
	$(COMPOSE_PROD) up -d --build
healthcheck-prod:
	$(COMPOSE_PROD) ps | grep healthy
## ========== Database ==========
db-migrate-prod:
	$(COMPOSE_PROD) exec $(SERVICE) alembic revision --autogenerate -m "prod migration_$(timestamp)"
db-upgrade-prod:
	$(COMPOSE_PROD) exec $(SERVICE) alembic upgrade head
## Optional: status, logs, or bash
bash-prod:
	$(COMPOSE_PROD) exec $(SERVICE) sh
logs-prod:
	$(COMPOSE_PROD) logs -f $(SERVICE)
