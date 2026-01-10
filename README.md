# Chopsticks

Chopsticks prepares and runs CBT (Ceph Benchmarking Tool) against MicroCeph clusters.

## Current Status: Phase 0 Complete ✅

Phase 0 delivers pre-flight checks for validating MicroCeph cluster health before automation.

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- LXD (for accessing target hosts)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd chopsticks

# Install dependencies
uv sync

# Run the CLI
uv run chopsticks --help
```

## Usage

### Pre-Flight Checks

Validate MicroCeph cluster health before running benchmarks:

```bash
# Single host check
uv run chopsticks preflight --host storage-01

# Multiple hosts with report output
uv run chopsticks preflight --host storage-01 --host client-01 --output report.yaml

# Skip detailed ceph status check
uv run chopsticks preflight --host storage-01 --skip-ceph-status
```

### Pre-Flight Probes

The pre-flight command validates:

- **Cluster Health**: MicroCeph status and Ceph cluster health (HEALTH_OK/WARN/ERR)
- **Network Reachability**: LXC connectivity to target hosts
- **Disk Capacity**: Root filesystem usage (warns if >90%)
- **Host Resources**: CPU cores (minimum 2) and memory availability

## Development

### Running Tests

```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run integration tests (requires LXD VMs)
uv run pytest tests/integration/ -v -m integration

# Run all tests
uv run pytest -v
```

### Code Quality

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

## Documentation

- [Phase 0: Pre-Flight Checks](docs/PHASE_0_PREFLIGHT.md) - Complete implementation documentation
- [Roadmap](roadmap.md) - Full project roadmap with all phases
- [CBT Research Notes](cbt.md) - CBT integration research and design notes

## Project Structure

```
src/chopsticks/
├── cli/              # CLI commands
├── probes/           # Pre-flight probe implementations
└── utils/            # Shared utilities

tests/
├── unit/             # Unit tests
└── integration/      # Integration tests

docs/                 # Documentation
```

## Contributing

This project follows the phased roadmap defined in `roadmap.md`. Each phase has specific objectives, deliverables, tests, and validation criteria.

## License

See [LICENSE](LICENSE) file for details.
