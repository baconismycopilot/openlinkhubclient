.PHONY: clean clean-pyc clean-test lint format install install-tool test help
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
    match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
    if match:
        target, help = match.groups()
        print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help: ## show this help
	@uv run python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-pyc clean-test ## remove Python and test artifacts

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and cache artifacts
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -f .coverage
	rm -rf htmlcov/

lint: ## check code style with ruff
	uv run ruff check .

format: ## auto-format code with ruff
	uv run ruff format .

install: ## sync project dependencies with uv
	uv sync

install-tool: ## install olh as an editable global command (~/.local/bin)
	uv tool install --editable .

test: ## run the test suite
	uv run pytest
