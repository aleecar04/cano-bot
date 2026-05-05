.PHONY: help test test-bot test-backend test-all lint docker-up docker-down dev-backend

PYTHON  := python
VENV    := venv/bin/activate
BOT_DIR := .
BACK_DIR := backend

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Tests ─────────────────────────────────────────────────────────────────────

test-bot: ## Ejecuta los tests del bot errbot (plugins/)
	@echo "→ Tests errbot (plugins/)"
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ -v \
		--cov=plugins \
		--cov-report=term-missing \
		--cov-report=html:htmlcov-bot \
		--cov-fail-under=80

test-backend: ## Ejecuta los tests del backend FastAPI (backend/app/)
	@echo "→ Tests backend FastAPI (backend/app/)"
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/api/routes/ -v \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80

test-all: ## Ejecuta TODOS los tests (bot + backend)
	@echo "════════════════════════════════════════"
	@echo "  TESTS BOT (errbot / plugins)"
	@echo "════════════════════════════════════════"
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ \
		--cov=plugins \
		--cov-report=term-missing \
		--cov-report=html:htmlcov-bot \
		--cov-fail-under=80 \
		-q
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "  TESTS BACKEND (FastAPI)"
	@echo "════════════════════════════════════════"
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/api/routes/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-q
	@echo ""
	@echo "✓ Todos los tests completados"

# ── Linting ───────────────────────────────────────────────────────────────────

lint: ## Ejecuta ruff en backend y plugins
	@echo "→ Lint backend"
	. $(VENV) && cd $(BACK_DIR) && ruff check app/
	@echo "→ Lint plugins"
	. $(VENV) && ruff check plugins/

# ── Backend dev ───────────────────────────────────────────────────────────────

dev-backend: ## Inicia el backend FastAPI en modo desarrollo
	. $(VENV) && cd $(BACK_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up: ## Levanta los servicios con docker-compose
	docker compose up -d

docker-down: ## Para los servicios de docker-compose
	docker compose down

docker-build: ## Reconstruye las imágenes docker
	docker compose build
