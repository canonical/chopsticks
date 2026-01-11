# Phase 0 Review – Round 2 Findings

## Summary
- Medium severity: 2
- Low severity: 1

## Findings
1. **Medium – Disk probe ignores the Ceph data devices.** `check_disk_capacity` only runs `df -h /`, so it reports success as long as the root filesystem has space. MicroCeph stores OSD data under `/var/snap/microceph/common/osd` (and often on separate block devices), meaning full or missing OSD disks go undetected. Evidence: [src/chopsticks/probes/resources.py](src/chopsticks/probes/resources.py#L13-L57). *Recommendation:* inspect the MicroCeph OSD data path(s) or accept user-supplied mount points and validate each of them.
2. **Medium – README testing workflow omits the dev dependency group.** The setup instructions direct contributors to run `uv sync`, but the dev tools (pytest, etc.) live in the `[dependency-groups]` section, so they are not installed by default. Following the documented steps leaves `pytest` missing and the advertised commands fail. Evidence: [README.md](README.md#L19-L80), [pyproject.toml](pyproject.toml#L42-L46). *Recommendation:* document `uv sync --group dev` (or move pytest into the main dependency set) so new contributors can run the tests successfully.
3. **Low – Running integration tests manually still crashes without guard rails.** Even though pytest now skips the integration marker by default, invoking `pytest -m integration` still assumes LXD hosts plus `uv` exist and crashes with opaque subprocess errors. Evidence: [tests/integration/test_preflight_integration.py](tests/integration/test_preflight_integration.py#L35-L77). *Recommendation:* add `pytest.skip` guards (checking for `uv`, `lxc`, and required hosts) so opt-in runs fail fast with actionable messages.
