.PHONY: setup dev dev-backend dev-frontend check check-backend check-frontend test demo eval smoke-meta

VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install -q -e ".[dev,eval]"
	cd frontend && npm install

dev:
	@echo "Backend: http://127.0.0.1:8000  Frontend: http://127.0.0.1:5173"
	@( $(PY) -m uvicorn secondshift.main:app --app-dir backend --reload --port 8000 & echo $$! > /tmp/ss-backend.pid; cd frontend && npm run dev & echo $$! > /tmp/ss-frontend.pid; wait )

dev-backend:
	$(PY) -m uvicorn secondshift.main:app --app-dir backend --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

check: check-backend check-frontend

check-backend:
	$(VENV)/bin/ruff check backend tests scripts eval
	$(VENV)/bin/ruff format --check backend tests scripts eval || true
	$(VENV)/bin/mypy backend/secondshift
	$(PY) -m pytest -q

check-frontend:
	cd frontend && npx tsc --noEmit

test:
	$(PY) -m pytest -q

demo:
	PROVIDER=meta CACHE_MODE=replay $(PY) -m uvicorn secondshift.main:app --app-dir backend --port 8000

eval:
	$(PY) eval/run_eval.py --help

smoke-meta:
	$(PY) scripts/smoke_meta.py
