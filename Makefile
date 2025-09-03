# WSL-Tmux-Nvim-Setup CLI Makefile
# Build and development automation

.PHONY: help install install-dev build build-exe clean test lint format check docs release

# Default target
help:
	@echo "WSL-Tmux-Nvim-Setup CLI Build System"
	@echo "====================================="
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install package in development mode"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  build        - Build distribution packages" 
	@echo "  build-exe    - Build standalone executable"
	@echo "  clean        - Clean build artifacts"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black/isort"
	@echo "  check        - Run all checks (lint + test)"
	@echo "  docs         - Generate documentation"
	@echo "  release      - Build and upload to PyPI"
	@echo "  dev-setup    - Set up development environment"
	@echo ""

# Variables
PYTHON ?= python3
PIP ?= pip3
PACKAGE_NAME = wsl-tmux-nvim-setup
CLI_MODULE = cli.wsm
BUILD_DIR = build
DIST_DIR = dist
VENV_DIR = venv

# Development setup
dev-setup:
	@echo "Setting up development environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install -U pip setuptools wheel
	$(VENV_DIR)/bin/pip install -e .[dev,build,test]
	$(VENV_DIR)/bin/pre-commit install
	@echo "Development environment ready!"
	@echo "Activate with: source $(VENV_DIR)/bin/activate"

# Installation
install:
	@echo "Installing $(PACKAGE_NAME) in development mode..."
	$(PIP) install -e .

install-dev:
	@echo "Installing $(PACKAGE_NAME) with development dependencies..."
	$(PIP) install -e .[dev,build,test]

# Building
build: clean
	@echo "Building distribution packages..."
	$(PYTHON) -m build
	@echo "Build complete! Check $(DIST_DIR)/ for packages"

build-exe: clean
	@echo "Building standalone executable..."
	@if ! command -v pyinstaller >/dev/null 2>&1; then \
		echo "Installing PyInstaller..."; \
		$(PIP) install pyinstaller; \
	fi
	pyinstaller --name wsm \
		--onefile \
		--console \
		--clean \
		--distpath $(DIST_DIR) \
		--workpath $(BUILD_DIR) \
		--specpath $(BUILD_DIR) \
		--add-data "version.json:." \
		--add-data "requirements.txt:." \
		--hidden-import cli.commands.install \
		--hidden-import cli.commands.update \
		--hidden-import cli.commands.list_cmd \
		--hidden-import cli.commands.status \
		--hidden-import cli.commands.config_cmd \
		--hidden-import cli.commands.rollback \
		--hidden-import cli.utils.download \
		--hidden-import cli.utils.extract \
		--hidden-import cli.utils.backup \
		--hidden-import cli.utils.github \
		--hidden-import cli.utils.version_utils \
		cli/wsm.py
	@echo "Executable built: $(DIST_DIR)/wsm"

# Testing
test:
	@echo "Running test suite..."
	@if [ -d "tests" ]; then \
		$(PYTHON) -m pytest tests/ -v --tb=short; \
	else \
		echo "No tests directory found, creating basic test structure..."; \
		mkdir -p tests; \
		echo "# Add your tests here" > tests/__init__.py; \
		echo "Basic test structure created in tests/"; \
	fi

test-coverage:
	@echo "Running tests with coverage..."
	@if [ -d "tests" ]; then \
		$(PYTHON) -m pytest tests/ --cov=cli --cov-report=html --cov-report=term; \
	else \
		echo "No tests directory found"; \
	fi

# Code quality
lint:
	@echo "Running linting checks..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 cli/; \
	else \
		echo "flake8 not installed, skipping..."; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy cli/; \
	else \
		echo "mypy not installed, skipping..."; \
	fi

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black cli/; \
	else \
		echo "black not installed, skipping..."; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort cli/; \
	else \
		echo "isort not installed, skipping..."; \
	fi

check: lint test
	@echo "All checks completed!"

# Documentation
docs:
	@echo "Generating documentation..."
	@mkdir -p docs
	@echo "# WSL-Tmux-Nvim-Setup CLI Documentation" > docs/README.md
	@echo "" >> docs/README.md
	@echo "Generated on: $$(date)" >> docs/README.md
	@echo "" >> docs/README.md
	@echo "## Commands" >> docs/README.md
	@echo "" >> docs/README.md
	@if [ -x "$(DIST_DIR)/wsm" ]; then \
		$(DIST_DIR)/wsm --help >> docs/README.md 2>/dev/null || true; \
	elif command -v wsm >/dev/null 2>&1; then \
		wsm --help >> docs/README.md 2>/dev/null || true; \
	else \
		echo "CLI not available for documentation generation"; \
	fi
	@echo "Documentation generated in docs/"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ 
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "Clean complete!"

clean-all: clean
	@echo "Deep cleaning..."
	rm -rf $(VENV_DIR)/
	@echo "Deep clean complete!"

# Release management  
version:
	@echo "Current version information:"
	@if [ -f "version.json" ]; then \
		cat version.json | grep version || echo "Version not found in version.json"; \
	else \
		echo "version.json not found"; \
	fi

bump-version:
	@echo "Bumping version..."
	@if [ -f "scripts/version-manager.py" ]; then \
		$(PYTHON) scripts/version-manager.py bump patch; \
	else \
		echo "Version manager script not found"; \
	fi

release-test: build
	@echo "Testing release to TestPyPI..."
	@if command -v twine >/dev/null 2>&1; then \
		twine check $(DIST_DIR)/*; \
		twine upload --repository testpypi $(DIST_DIR)/*; \
	else \
		echo "twine not installed"; \
	fi

release: build
	@echo "Releasing to PyPI..."
	@if command -v twine >/dev/null 2>&1; then \
		twine check $(DIST_DIR)/*; \
		twine upload $(DIST_DIR)/*; \
	else \
		echo "twine not installed"; \
	fi

# Development utilities
run:
	@echo "Running CLI in development mode..."
	$(PYTHON) -m cli.wsm $(ARGS)

debug:
	@echo "Running CLI with debug output..."
	WSM_DEBUG=1 $(PYTHON) -m cli.wsm $(ARGS)

install-system:
	@echo "Installing CLI system-wide..."
	sudo $(PIP) install .

uninstall:
	@echo "Uninstalling $(PACKAGE_NAME)..."
	$(PIP) uninstall $(PACKAGE_NAME) -y

# Integration with existing scripts
integrate:
	@echo "Creating integration scripts..."
	@mkdir -p bin
	@echo "#!/bin/bash" > bin/wsm
	@echo "# WSL-Tmux-Nvim-Setup CLI Wrapper" >> bin/wsm
	@echo "exec $(PYTHON) -m cli.wsm \"\$$@\"" >> bin/wsm
	@chmod +x bin/wsm
	@echo "Integration script created: bin/wsm"

# Quick development cycle
dev: clean format lint test
	@echo "Development cycle complete!"

# Show package info
info:
	@echo "Package Information:"
	@echo "==================="
	@echo "Name: $(PACKAGE_NAME)"
	@echo "CLI Module: $(CLI_MODULE)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "Working Directory: $$(pwd)"
	@echo ""
	@echo "Package Status:"
	@if $(PIP) show $(PACKAGE_NAME) >/dev/null 2>&1; then \
		$(PIP) show $(PACKAGE_NAME); \
	else \
		echo "Package not installed"; \
	fi