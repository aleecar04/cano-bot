.PHONY: help test test-bot test-backend test-front test-all lint docker-up docker-down dev-backend sonar supabase-up supabase-down supabase-migrate

PYTHON   := python
VENV     := venv/bin/activate
BOT_DIR  := errbot
BACK_DIR := backend
FRONT_DIR := cano-app

supabase-up:
	@supabase status > /dev/null 2>&1 || supabase start

supabase-down:
	@supabase stop --no-backup

supabase-migrate: supabase-up
	@supabase db reset --no-seed

test-bot:
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ -v \
		--cov=plugins --cov=drivers \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov-bot \
		--cov-fail-under=80

test-backend: supabase-migrate
	. $(VENV) && cd $(BACK_DIR) && $(PYTHON) -m pytest tests/ -v \
		--cov=app \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80

test-front:
	cd $(FRONT_DIR) && npm test -- --coverage

test-all: supabase-migrate
	@echo "════════════════════════════════════════"
	@echo "  TESTS BOT (errbot / plugins)"
	@echo "════════════════════════════════════════"
	. $(VENV) && cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ \
		--cov=plugins --cov=drivers \
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
