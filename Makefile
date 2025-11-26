.PHONY: all clean build install uninstall test publish redis redis-down

# Default target
all: clean build

# Remove Python + build artifacts
clean:
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*~" -delete
	rm -rf dist build *.egg-info

# Build package (requires: pip install build)
build:
	python -m build

# Install locally built package
install:
	pip install --force-reinstall dist/*.whl

# Uninstall FQ completely
uninstall:
	pip uninstall -y flowdacity-queue

# Run tests — prefers pytest, falls back to python modules
test:
	@if python -c "import pytest" 2>/dev/null; then \
		python -m pytest -q; \
	else \
		echo 'pytest not installed — running direct test modules'; \
		python -m tests.test_queue; \
		python -m tests.test_func; \
	fi

publish: clean
	uv sync --group dev
	uv run python -m build
# 	@if [ -z "$$PYPI_API_TOKEN" ]; then echo "PYPI_API_TOKEN must be set"; exit 1; fi
# 	uv run python -m twine upload dist/* -u __token__ -p "$$PYPI_API_TOKEN"
	uv run python -m twine upload dist/*

# Start Redis container
redis:
	docker compose up -d redis

# Stop Redis container
redis-down:
	docker compose down
