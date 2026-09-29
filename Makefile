PYTHON ?= python3
.PHONY: check
check:
	$(PYTHON) -m py_compile backend/settings.py music/views.py
	$(PYTHON) manage.py check
	$(PYTHON) manage.py makemigrations --check --dry-run
	$(PYTHON) manage.py test
	npm --prefix frontend run lint
	npm --prefix frontend run build
