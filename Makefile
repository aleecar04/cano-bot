.PHONY: help test test-bot test-backend test-all lint docker-up docker-down dev-backend sonar

PYTHON  := python
VENV    := venv/bin/activate
BOT_DIR := errbot
BACK_DIR := backend

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test-bot: ## Ejecuta los tests del bot errbot (plugins/ + drivers/ + api/)
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ -v \
		--cov=plugins --cov=drivers --cov=api \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov-bot \
		--cov-fail-under=80

test-backend: ## Ejecuta los tests del backend FastAPI (backend/app/)
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ -v \
		--cov=app \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80

test-all: ## Ejecuta TODOS los tests (bot + backend)
	@echo "════════════════════════════════════════"
	@echo "  TESTS BOT (errbot / plugins)"
	@echo "════════════════════════════════════════"
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ \
		--cov=plugins --cov=drivers --cov=api \
		--cov-branch \
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
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-q

sonar: ## Genera coverage y lanza SonarCloud (uso: make sonar SONAR_TOKEN=tu_token)
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ \
		--override-ini=addopts= \
		--cov=app \
		--cov-branch \
		--cov-report=xml:../backend-coverage.xml \
		-q
	@sed -i 's|$(shell cd backend && pwd)/app|backend/app|g' backend-coverage.xml
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ \
		--override-ini=addopts= \
		--cov=plugins --cov=drivers --cov=api \
		--cov-branch \
		--cov-report=xml:../bot-coverage.xml \
		-q
	@sed -i 's|$(shell cd errbot && pwd)/plugins|errbot/plugins|g' bot-coverage.xml
	@sed -i 's|$(shell cd errbot && pwd)/drivers|errbot/drivers|g' bot-coverage.xml
	@sed -i 's|$(shell cd errbot && pwd)/api|errbot/api|g' bot-coverage.xml
	/opt/sonar-scanner/bin/sonar-scanner \
		-Dsonar.token=$(SONAR_TOKEN) \
		-Dsonar.branch.name=$(shell git branch --show-current)

lint: ## Ejecuta ruff en backend y plugins
	. $(VENV) && cd $(BACK_DIR) && ruff check app/
	. $(VENV) && cd $(BOT_DIR) && ruff check plugins/

dev-backend: ## Inicia el backend FastAPI en modo desarrollo
	. $(VENV) && cd $(BACK_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up: ## Levanta los servicios con docker-compose
	docker compose up -d

docker-down: ## Para los servicios de docker-compose
	docker compose down

docker-build: ## Reconstruye las imágenes docker
	docker compose build
