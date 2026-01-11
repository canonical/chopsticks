# Phase 0 Review - Round 2 Response and Remediation Plan

**Date**: January 11, 2026  
**Reviewers**: Project Team  
**Responders**: Implementation Team  

## Executive Summary

We acknowledge all 3 findings from Phase 0 Round 2 review (2 medium, 1 low severity). All issues are valid and will be addressed. These findings reveal gaps in the initial remediation: incomplete resource validation, inadequate documentation, and missing runtime safety checks.

**Status**: All findings accepted and remediation planned  
**Risk**: Medium - Findings affect operational reliability and developer experience  
**Timeline**: Immediate remediation for all findings  

---

## Finding-by-Finding Response

### 1. MEDIUM: Disk probe ignores the Ceph data devices

**Status**: ✅ ACCEPTED - Critical gap in resource validation

**Analysis**:
- **Root Cause**: `check_disk_capacity` only validates root filesystem (`df -h /`)
- **Impact**: MicroCeph OSD data paths go unmonitored; full or missing OSD disks undetected
- **Scope**: Affects resources probe module
- **Risk**: Silent failures when OSD storage is exhausted while root filesystem has space
- **Evidence**: MicroCeph stores OSD data under `/var/snap/microceph/common/osd` and often on separate block devices

**Acknowledgment**:
The reviewer is correct. Current implementation fails to validate the actual storage paths used by Ceph OSDs. A MicroCeph cluster can report healthy root filesystem while OSD data disks are full or misconfigured.

**Proposed Solution**:

1. **Query MicroCeph for actual OSD paths**:
   ```python
   def get_microceph_osd_paths(host: str, executor: RemoteExecutor) -> list[str]:
       """Get OSD data paths from MicroCeph configuration."""
       # Query: ceph osd df --format json (provides OSD utilization)
       # Or enumerate: /var/snap/microceph/common/data/osd/ceph-*
       # Also check: microceph disk list (shows block device paths)
       # Return both block device paths and data directories
   ```

2. **Validate each OSD data path**:
   ```python
   def check_osd_disk_capacity(host: str, executor: RemoteExecutor | None = None) -> ProbeResult:
       """Check disk capacity for all MicroCeph OSD data paths."""
       osd_paths = get_microceph_osd_paths(host, executor)
       
       for path in osd_paths:
           # Run df -h <path> for each OSD location
           # Aggregate results with per-OSD details
           # Fail if any OSD disk usage > 85% (Ceph nearfull threshold)
   ```

3. **Add user-configurable path override**:
   ```python
   # Allow CLI option for custom mount points
   @click.option("--osd-path", multiple=True, help="Additional OSD data paths to check")
   ```

4. **Keep backward-compatible root check**:
   - Rename `check_disk_capacity` → `check_root_disk_capacity`
   - Add new `check_osd_disk_capacity` probe
   - Both run by default in preflight command

**Implementation Plan**:
1. Add `get_microceph_osd_paths()` helper in `probes/resources.py`:
   - Parse `microceph disk list` output to get block device paths
   - Use `ceph osd df --format json` to get OSD IDs and utilization
   - Enumerate `/var/snap/microceph/common/data/osd/ceph-*` directories
   - Return tuple of (block_devices, data_dirs) for comprehensive validation
2. Implement `check_osd_disk_capacity()` function:
   - Validate each block device if on separate filesystem
   - Fall back to data directory validation if shared filesystem
   - Use Ceph's 85% nearfull threshold for warnings
3. Add `--osd-path` CLI option to preflight command for manual override
4. Update preflight to run both root and OSD disk checks
5. Add unit tests for OSD path discovery and validation
6. Add integration test verifying OSD disk reporting against real cluster
7. Update documentation with OSD validation details

**Acceptance Criteria**:
- [ ] Probe queries `microceph disk list` to discover block device paths
- [ ] Probe uses `ceph osd df --format json` to get OSD utilization data
- [ ] Probe enumerates `/var/snap/microceph/common/data/osd/ceph-*` directories
- [ ] Probe validates disk usage for each OSD location (block device or data dir)
- [ ] Probe fails if any OSD disk usage > 85% (Ceph nearfull threshold)
- [ ] Probe supports `--osd-path` manual override for custom deployments
- [ ] Probe reports detailed per-OSD disk statistics in output
- [ ] Tests cover OSD path discovery edge cases (no OSDs, custom paths, mixed storage)
- [ ] Integration test validates against real MicroCeph cluster with multiple OSDs
- [ ] Documentation updated with OSD validation details and threshold explanations

**Timeline**: 1 day (includes testing and documentation)

---

### 2. MEDIUM: README testing workflow omits the dev dependency group

**Status**: ✅ ACCEPTED - Documentation gap affecting contributor onboarding

**Analysis**:
- **Root Cause**: Missing mypy and ruff from pyproject.toml dependencies
- **Impact**: README documents `uv run mypy src/` but mypy is not in any dependency group
- **Scope**: Affects README.md and pyproject.toml [dependency-groups.dev] section
- **Risk**: Poor developer experience - documented commands fail with "No such file or directory"
- **Evidence**: 
  - ✅ `uv sync` + `uv run pytest`: **WORKS** (uv run auto-installs dev dependencies)
  - ❌ `uv sync` + `uv run mypy`: **FAILS** (mypy not in pyproject.toml)
  - ⚠️ `uvx ruff`: **Status unclear** (uvx runs tools from uv tool cache or pypi)

**Acknowledgment**:
The reviewer correctly identified broken workflows. Testing reveals:
1. `uv run pytest` actually works because `uv run` automatically installs dev dependencies
2. `uv run mypy` fails because mypy is completely missing from pyproject.toml
3. ruff behavior depends on whether it's installed globally or in uv tool cache
4. The issue is missing tools in pyproject.toml, not the `uv sync` command itself

**Proposed Solution**:

**Recommended Approach**: Add missing tools to dev dependencies, fix README commands:

1. **Add mypy to pyproject.toml** (ruff via uvx doesn't need dependency entry):
   ```toml
   [dependency-groups]
   dev = [
       "pytest>=9.0.2",
       "pytest-mock>=3.15.1",
       "mypy>=1.11.2",
   ]
   ```

2. **Update README to clarify uv behavior**:
   - Document that `uv run` automatically handles dev dependencies
   - Remove confusing `uv sync --group dev` instruction
   - Clarify when to use `uv sync` vs `uv sync --no-dev`

**Rationale**: 
- `uv run <command>` automatically installs required dependencies (including dev group)
- Explicit `uv sync --group dev` is NOT needed for running tests/tools
- Production deployments should use `uv sync --no-dev` to exclude dev tools
- Current pyproject.toml is missing mypy and ruff entirely

**Implementation Plan**:
1. Add mypy and ruff to `[dependency-groups.dev]` in pyproject.toml
2. Update README.md Quick Start section:
   ```markdown
   # Install dependencies
   uv sync
   
   # Run the CLI
   uv run chopsticks --help
   
   # Note: uv run automatically manages dependencies
   # For production deployment use: uv sync --no-dev
   ```
3. Update README "Development" section with verified working commands:
   ```markdown
   ## Development
   
   ### Running Tests
   ```bash
   # uv run automatically installs dev dependencies
   uv run pytest -v                           # Run all unit tests
   uv run pytest -m integration -v            # Run integration tests
   ```
   
   ### Code Quality
   ```bash
   uv run mypy src/                           # Type checking
   uvx ruff check src/                        # Linting
   uvx ruff format src/                       # Auto-formatting
   ```
   ```
4. Add "Dependency Management" section:
   ```markdown
   ## Dependency Management
   
   Chopsticks uses uv with dependency groups:
   - **Production**: `uv sync --no-dev` (minimal: click, pyyaml, rich only)
   - **Development**: `uv sync` (includes dev tools: pytest, mypy, ruff)
   - **Running commands**: `uv run <cmd>` auto-installs required dependencies
   
   Contributors don't need to manually manage dependency groups - `uv run` handles it.
   ```
5. Validate all documented commands work:
   - Fresh clone → `uv sync` → `uv run pytest -v` ✅
   - `uv run mypy src/` ✅
   - `uvx ruff check src/` ✅
   - Production: `uv sync --no-dev` → verify dev tools excluded ✅

**Acceptance Criteria**:
- [ ] mypy added to `[dependency-groups.dev]` in pyproject.toml
- [ ] README Quick Start uses `uv sync` (not `--group dev`)
- [ ] README documents that `uv run` auto-manages dependencies and `uvx` for tools
- [ ] "Development" section commands are verified working
- [ ] New "Dependency Management" section clarifies prod vs dev usage
- [ ] Fresh clone test: `git clone` → `uv sync` → `uv run pytest -v` passes
- [ ] All documented commands validated: pytest, mypy, ruff (via uvx) all work
- [ ] Production test: `uv sync --no-dev` excludes pytest/mypy
- [ ] Commands show clear error if deps missing (not cryptic uv errors)

**Timeline**: 2 hours (add mypy to pyproject.toml, update README with uvx ruff, validate commands)

---

### 3. LOW: Running integration tests manually still crashes without guard rails

**Status**: ✅ ACCEPTED - Missing runtime safety checks

**Analysis**:
- **Root Cause**: Integration tests only have `@pytest.mark.skipif()` decorators, not runtime skip guards
- **Impact**: `pytest -m integration` crashes with opaque subprocess errors if dependencies missing
- **Scope**: Affects tests/integration/test_preflight_integration.py
- **Risk**: Poor developer experience during test debugging
- **Evidence**: Skip decorators evaluate at collection time, but subprocess failures happen at runtime

**Acknowledgment**:
The reviewer is correct. While the decorators prevent auto-execution, developers explicitly running integration tests get cryptic failures like:
```
FileNotFoundError: [Errno 2] No such file or directory: 'lxc'
subprocess.CalledProcessError: Command '['uv', 'run', ...]' returned non-zero exit status 1
```

Instead of actionable messages like:
```
SKIPPED: LXD not available - install with 'snap install lxd'
SKIPPED: Test VM 'storage-01' not running - create with 'lxc launch ...'
```

**Proposed Solution**:

Add runtime `pytest.skip()` calls at the beginning of each test function:

```python
@pytest.mark.integration
@pytest.mark.skipif(not lxd_available(), reason="LXD not available")
@pytest.mark.skipif(not uv_available(), reason="uv not installed")
@pytest.mark.skipif(not hosts_available(), reason="Test VMs not running")
def test_preflight_storage_01():
    """Test preflight against storage-01."""
    # RUNTIME guard (not just collection-time decorator)
    if not lxd_available():
        pytest.skip("LXD not available - install with: snap install lxd")
    if not uv_available():
        pytest.skip("uv not installed - install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
    if not hosts_available():
        pytest.skip("Test VMs not running - see tests/integration/README.md for setup")
    
    # ... actual test code
```

**Enhanced approach**:
1. Create fixture with better error messages:
   ```python
   @pytest.fixture
   def integration_env():
       """Validate integration test environment with actionable messages."""
       missing = []
       
       if not lxd_available():
           missing.append("LXD - Install: snap install lxd")
       if not uv_available():
           missing.append("uv - Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
       
       # Check for specific required hosts
       required_hosts = ["storage-01", "client-01"]
       for host in required_hosts:
           if not host_exists(host):
               missing.append(f"LXD VM '{host}' - See tests/integration/README.md")
       
       if missing:
           pytest.skip("Missing dependencies:\n  - " + "\n  - ".join(missing))
   ```

2. Use fixture in all integration tests:
   ```python
   def test_preflight_storage_01(integration_env):
       """Test preflight against storage-01."""
       # Environment already validated by fixture
       result = subprocess.run([...])
   ```

3. Add tests/integration/README.md with setup instructions:
   ```markdown
   # Integration Test Setup
   
   ## Prerequisites
   - LXD: `snap install lxd && lxd init --auto`
   - uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   
   ## Test VM Setup
   ```bash
   lxc launch ubuntu:22.04 storage-01
   lxc launch ubuntu:22.04 client-01
   # Install MicroCeph in VMs...
   ```
   ```

**Implementation Plan**:
1. Create `integration_env` fixture with detailed error messages
2. Refactor all integration tests to use fixture
3. Add `host_exists(hostname)` helper function
4. Create `tests/integration/README.md` with setup instructions
5. Update main README to reference integration setup docs
6. Test failure messages by temporarily removing dependencies

**Acceptance Criteria**:
- [ ] `pytest -m integration` with missing LXD shows: "LXD not available - install with: snap install lxd"
- [ ] Missing uv shows install command
- [ ] Missing test VMs show reference to setup documentation
- [ ] All checks provide actionable remediation steps
- [ ] tests/integration/README.md documents complete setup process
- [ ] No opaque subprocess errors during integration test failures

**Timeline**: 3 hours (includes fixture, helper functions, documentation)

---

## Summary and Next Steps

### Risk Assessment
- **Finding #1 (MEDIUM)**: Operational risk - MicroCeph clusters could have full OSD disks while reporting healthy
- **Finding #2 (MEDIUM)**: Developer experience risk - contributor onboarding friction
- **Finding #3 (LOW)**: Developer experience risk - poor debugging experience

### Recommended Implementation Order
1. **Finding #2** (2 hours) - Quick win, documentation only, improves immediate contributor experience
2. **Finding #3** (3 hours) - Improves test debugging, required for Finding #1 validation
3. **Finding #1** (1 day) - Most complex, benefits from improved test infrastructure

### Total Estimated Effort
- **Documentation**: 2 hours
- **Test Infrastructure**: 3 hours  
- **OSD Disk Validation**: 1 day  
- **Total**: ~1.5 days

### Validation Plan
1. Fresh environment test: Clone repo, follow README, verify tests run
2. Integration test failure simulation: Verify error messages are actionable
3. MicroCeph cluster test: Deploy cluster, fill OSD disk, verify probe catches it
4. Documentation review: Ensure all changes documented

### Dependencies
- Finding #2 has no dependencies (can start immediately)
- Finding #3 depends on Finding #2 (need working dev environment)
- Finding #1 depends on Finding #3 (need integration test infrastructure)

---

## Appendix: Additional Improvements Identified

While addressing these findings, we identified related improvements:

1. **OSD utilization thresholds**: Make configurable via CLI (currently hardcoded to 85%)
2. **Probe extensibility**: Consider plugin architecture for custom probes
3. **Report format**: Add JSON output option alongside YAML
4. **Performance**: Parallelize probe execution for faster validation

These are out of scope for Round 2 remediation but tracked for future phases.

---

**Document Status**: Ready for Review  
**Next Action**: Await confirmation to proceed with implementation  
**Estimated Completion**: All fixes can be delivered within 2 days of approval
