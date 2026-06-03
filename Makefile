.PHONY: help test test-bot test-backend test-all lint docker-up docker-down dev-backend sonar

PYTHON  := python
VENV    := venv/bin/activate
BOT_DIR := errbot
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
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ -v \
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
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-q
	@echo ""
	@echo "✓ Todos los tests completados"

# ── Sonar ─────────────────────────────────────────────────────────────────────

sonar: ## Genera coverage y lanza SonarCloud (uso: make sonar SONAR_TOKEN=tu_token)
	@echo "→ Generando coverage backend"
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ \
		--override-ini=addopts= \
		--cov=app \
		--cov-report=xml:../backend-coverage.xml \
		-q
	@sed -i 's|$(shell cd backend && pwd)/app|backend/app|g' backend-coverage.xml
	@sed -i 's|filename="|filename="backend/app/|g' backend-coverage.xml
	@echo "→ Generando coverage bot"
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ \
		--override-ini=addopts= \
		--cov=plugins \
		--cov-report=xml:../bot-coverage.xml \
		-q
	@sed -i 's|$(shell cd errbot && pwd)/plugins|errbot/plugins|g' bot-coverage.xml
	@sed -i 's|filename="|filename="errbot/plugins/|g' bot-coverage.xml
	@echo "→ Lanzando Sonar"
	/opt/sonar-scanner/bin/sonar-scanner \
		-Dsonar.token=$(SONAR_TOKEN) \
		-Dsonar.branch.name=$(shell git branch --show-current)

# ── Linting ───────────────────────────────────────────────────────────────────

lint: ## Ejecuta ruff en backend y plugins
	@echo "→ Lint backend"
	. $(VENV) && cd $(BACK_DIR) && ruff check app/
	@echo "→ Lint plugins"
	. $(VENV) && cd $(BOT_DIR) && ruff check plugins/

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
