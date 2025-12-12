# Chopsticks development tasks

# Default recipe: list available commands
default:
    @just --list

# Run all unit tests
test:
    uv run pytest tests/unit/ -v

# Run unit tests with coverage
test-cov:
    uv run pytest tests/unit/ --cov=src/chopsticks --cov-report=term

# Run a specific test file or pattern
test-filter pattern:
    uv run pytest tests/unit/ -v -k "{{pattern}}"

# Run linting
lint:
    uv run ruff check src/chopsticks/ tests/

# Format code
fmt:
    uv run ruff format src/chopsticks/ tests/

# Check formatting without modifying
fmt-check:
    uv run ruff format --check src/chopsticks/ tests/

# Run lint and format check
check: lint fmt-check

# Run functional tests (requires MicroCeph)
test-functional:
    ./scripts/run-functional-test.sh

# Install dependencies
install:
    uv sync

# Clean build artifacts
clean:
    rm -rf .pytest_cache .ruff_cache __pycache__ .coverage
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
