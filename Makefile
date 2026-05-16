PYTHON ?= python

.PHONY: dev worker migrate test compile create-admin check-setup seed-queries smoke-yandex

dev:
	$(PYTHON) -m uvicorn app.main:app --reload

worker:
	$(PYTHON) -m app.workers.scan_worker

migrate:
	alembic upgrade head

test:
	$(PYTHON) -m pytest

compile:
	$(PYTHON) -m compileall app alembic tests

create-admin:
	$(PYTHON) scripts/create_admin.py --username admin --password change-me

check-setup:
	$(PYTHON) scripts/check_setup.py

seed-queries:
	$(PYTHON) scripts/seed_query_catalog.py

smoke-yandex:
	$(PYTHON) scripts/smoke_yandex_provider.py --query "CNC" --city "Izmir" --limit 5
