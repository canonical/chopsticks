# Phase 0: Pre-Flight Checks - Implementation Documentation

## Overview

Phase 0 delivers a pre-flight CLI that validates MicroCeph cluster health, network reachability, disk capacity, and host resource baselines before any automation. This is a read-only validation phase that ensures clusters meet baseline requirements.

## Objectives Achieved

✅ **Pre-flight CLI**: Implemented `chopsticks preflight` command with structured reporting  
✅ **Cluster Health Probes**: MicroCeph status and Ceph status validation  
✅ **Network Probes**: LXC connectivity validation  
✅ **Resource Probes**: Disk capacity and host resource checks  
✅ **Unit Tests**: 13 unit tests covering all probe logic  
✅ **Integration Tests**: 5 integration tests against live LXD VMs  
✅ **Documentation**: Comprehensive operator checklist and usage guide  

## Deliverables

### 1. `chopsticks preflight` Command

The pre-flight command validates multiple aspects of target hosts:

```bash
chopsticks preflight --host storage-01 [--output report.yaml] [--skip-ceph-status]
```

**Options:**
- `--host`: Target host(s) to check (can be specified multiple times)
- `--output`: Write structured YAML report to file
- `--skip-ceph-status`: Skip detailed 'ceph status' check

**Example Usage:**

```bash
# Single host check
chopsticks preflight --host storage-01

# Multiple hosts with report output
chopsticks preflight --host storage-01 --host client-01 --output report.yaml

# Skip detailed ceph status check
chopsticks preflight --host storage-01 --skip-ceph-status
```

### 2. Implemented Probes

#### Cluster Health Probes
- **MicroCeph Status**: Validates `microceph status` returns successfully and parses service/disk information
- **Ceph Status**: Checks `ceph status` and validates HEALTH_OK/WARN/ERR states

#### Network Probes
- **Network Reachability**: Tests LXC connectivity and extracts IP address information

#### Resource Probes
- **Disk Capacity**: Checks disk usage on root filesystem, fails if >90% used
- **Host Resources**: Validates CPU core count (minimum 2) and memory availability

### 3. Structured Reporting

Reports are generated in YAML format with the following structure:

```yaml
timestamp: '2026-01-10T21:36:20.480868'
summary:
  storage-01:
    total: 5
    passed: 5
    failed: 0
results:
  - probe: MicroCeph Status
    host: storage-01
    passed: true
    message: MicroCeph is operational
    details:
      services: mds, mgr, mon, osd
      disks: '3'
    timestamp: '2026-01-10T21:36:20.910910'
```

### 4. Test Coverage

**Unit Tests** (13 tests):
- `tests/unit/test_report.py`: Report utility tests (4 tests)
- `tests/unit/test_probes.py`: Probe module tests (9 tests)

**Integration Tests** (5 tests):
- `tests/integration/test_preflight_integration.py`: End-to-end CLI tests

Run tests:
```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run integration tests (requires LXD VMs)
uv run pytest tests/integration/ -v -m integration

# Run all tests
uv run pytest -v
```

## Project Structure

```
src/chopsticks/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # Main CLI entry point
│   └── preflight.py     # Pre-flight command implementation
├── probes/
│   ├── __init__.py
│   ├── cluster_health.py  # MicroCeph/Ceph status probes
│   ├── network.py         # Network reachability probes
│   └── resources.py       # Disk/host resource probes
└── utils/
    ├── __init__.py
    └── report.py          # Report generation utilities

tests/
├── unit/
│   ├── test_report.py
│   └── test_probes.py
└── integration/
    └── test_preflight_integration.py
```

## Operator Pre-Flight Checklist

### Prerequisites

Before running pre-flight checks, ensure:

1. **MicroCeph cluster is bootstrapped**: The tool does not bootstrap clusters
2. **LXD/container access**: Tool must be able to execute `lxc exec` commands
3. **Host reachability**: All target hosts must be accessible via LXD

### Expected Outputs

When all checks pass:
- Exit code: 0
- Console: "✅ All pre-flight checks passed"
- All probes show green checkmarks

When checks fail:
- Exit code: 1
- Console: "❌ Pre-flight checks failed"
- Failed probes show red X marks with error messages

### Remediation Steps

#### MicroCeph Status Failed
- **Cause**: MicroCeph not installed or not running
- **Remediation**: 
  ```bash
  lxc exec <host> -- snap install microceph
  lxc exec <host> -- microceph cluster bootstrap
  ```

#### Ceph Status Failed (HEALTH_WARN)
- **Cause**: Cluster has warnings (e.g., clock skew, too few OSDs)
- **Remediation**: 
  ```bash
  lxc exec <host> -- ceph -s  # View detailed status
  lxc exec <host> -- ceph health detail  # View warning details
  ```

#### Network Reachability Failed
- **Cause**: LXD container not running or network issues
- **Remediation**:
  ```bash
  lxc list  # Check container status
  lxc start <host>  # Start if stopped
  ```

#### Disk Capacity Failed
- **Cause**: Disk usage >90%
- **Remediation**: Free up disk space or expand storage

#### Host Resources Failed
- **Cause**: Insufficient CPU cores (<2)
- **Remediation**: Reconfigure VM with more CPU cores

## Validation

Phase 0 validation was performed on:
- **storage-01**: Ubuntu 24.04 LXD VM with MicroCeph installed (3 OSDs)
- **client-01**: Ubuntu 24.04 LXD VM without MicroCeph

### Validation Results

**storage-01** (MicroCeph host):
- ✅ All 5 checks passed
- MicroCeph status: operational (mds, mgr, mon, osd services, 3 disks)
- Ceph status: HEALTH_OK
- Network: reachable (10.240.47.219)
- Disk: 23% usage
- Resources: 4 cores, 3.5Gi memory

**client-01** (non-MicroCeph host):
- ❌ 2 of 5 checks failed (expected)
- MicroCeph/Ceph status: Command not found (expected)
- Network: reachable (10.240.47.161)
- Disk: 19% usage
- Resources: 4 cores, 3.5Gi memory

## Rollback

No rollback required for Phase 0 as all checks are read-only. If regressions are discovered:

1. Disable specific probes by commenting out probe calls in `src/chopsticks/cli/preflight.py`
2. Revert to previous git commit if necessary

## Known Limitations

1. **Requires bootstrapped cluster**: Tool does not bootstrap MicroCeph or join nodes
2. **No automatic remediation**: Tool only reports issues, does not fix them
3. **LXD-specific**: Currently uses `lxc exec` for host access
4. **MicroCeph bootstrap/join out of scope**: Operators must complete cluster setup before pre-flight

## Next Steps

Phase 0 is complete and validated. Ready to proceed to Phase 1: Foundation & Packaging Baseline.

Phase 1 will establish:
- Complete Python project structure with pyproject.toml
- Snapcraft configuration with classic confinement
- Dual uv environments (core vs CBT)
- CBT vendoring and compatibility matrix
- CI workflows and error handling framework
