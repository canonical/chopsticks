# Chopsticks Documentation

This directory contains the Sphinx documentation for Chopsticks, built using the [Canonical Sphinx Docs Starter Pack](https://github.com/canonical/sphinx-docs-starter-pack).

## Documentation Structure

The documentation follows the [Diátaxis](https://diataxis.fr/) framework:

### Tutorial (Learning-oriented)
Hands-on introduction for new users:
- Installation
- Running first test
- Understanding results

### How-to Guides (Task-oriented)
Step-by-step guides for common tasks:
- Creating custom scenarios
- Collecting metrics
- Running distributed tests
- Customizing drivers

### Reference (Information-oriented)
Technical specifications:
- CLI reference
- Configuration reference
- Metrics schema
- Driver API
- Workload API

### Explanation (Understanding-oriented)
Conceptual documentation:
- Architecture
- Metrics architecture
- Scenarios
- Error handling

## Building the Documentation

### Prerequisites

```bash
# Install Python 3.12+ and python3-venv
sudo apt install python3-venv
```

### Build Locally

```bash
# Install dependencies and build
cd docs
make install
make html

# View in browser
make serve
# Open http://localhost:8000
```

### Live Reload Development

```bash
cd docs
make run
# Open http://localhost:8000
# Docs rebuild automatically on changes
```

### Build PDF

```bash
cd docs
sudo make pdf-prep-force  # Install LaTeX dependencies
make pdf
# Output in docs/_build/
```

## Linting and Checks

```bash
cd docs

# Check links
make linkcheck

# Check spelling
make spelling

# Check inclusive language
make woke

# Check style guide compliance
make vale
```

## Publishing

Documentation is automatically published to Read the Docs when changes are pushed to the `main` branch.

**Read the Docs Configuration:** `.readthedocs.yaml` in repository root

## Contributing

When adding or updating documentation:

1. Follow the Diátaxis framework placement
2. Use reStructuredText (.rst) format
3. Add to appropriate index file
4. Build locally to verify
5. Run linting checks
6. Commit with descriptive message

See `CONTRIBUTING.md` in repository root for full contribution guidelines.
