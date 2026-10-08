.PHONY: help dev-setup test lint format sync check-sync validate validate-all clean

help:
	@echo "NAS2RBPi — sistema multiagéntico"
	@echo ""
	@echo "  dev-setup     Instala dependencias (uv) y los hooks de pre-commit"
	@echo "  test          Ejecuta todos los tests"
	@echo "  lint          ruff check + ruff format --check"
	@echo "  format        Formatea el código"
	@echo "  sync          Copia shared/ a cada plugin (tras editar shared/)"
	@echo "  check-sync    Falla si alguna copia de shared/ ha divergido"
	@echo "  validate D=x  Valida la última versión del entregable x (nrd, hld, rbk...)"
	@echo "  validate-all  Valida la última versión de todos los entregables"

dev-setup:
	uv sync
	uv run pre-commit install

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

sync:
	uv run python tools/sync_shared.py

check-sync:
	uv run python tools/sync_shared.py --check

validate:
	uv run python tools/validate.py $(D)

validate-all:
	uv run python tools/validate.py --all

clean:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
