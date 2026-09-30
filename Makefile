.PHONY: setup dev check
setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	npm --prefix frontend ci
	@test -f .env || cp .env.example .env
dev:
	.venv/bin/python scripts/dev.py
check:
	.venv/bin/python manage.py check
	.venv/bin/python manage.py makemigrations --check --dry-run
	.venv/bin/python manage.py test music
	npm --prefix frontend test
	npm --prefix frontend run typecheck
	npm --prefix frontend run lint
	npm --prefix frontend run build
