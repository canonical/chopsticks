# Phase 0 Review – Round 3 Findings

## Summary
- Medium severity: 2
- Low severity: 1

## Findings
1. **Medium – Host resource probe ignores memory baselines.** The roadmap calls out Phase 0’s responsibility to validate “host resource baselines” before automation, yet the current probe only enforces a minimum CPU core count and never fails on undersized RAM. That means a node with 512 MiB of memory still passes the pre-flight check, contradicting the stated objective. Evidence: [roadmap.md](roadmap.md#L5-L8), [src/chopsticks/probes/resources.py](src/chopsticks/probes/resources.py#L84-L143). *Recommendation:* add configurable thresholds for both memory and CPU (and surface actual values in the report) so insufficient RAM triggers a failure.
2. **Medium – Integration guard treats powered-off VMs as ready.** `host_exists` only checks that `lxc list <name>` returns an entry; it does not confirm the instance is running. If `storage-01` exists but is shut down, the skip decorator evaluates to false and the tests proceed, eventually failing with `lxc exec` errors instead of skipping gracefully. Evidence: [tests/integration/test_preflight_integration.py](tests/integration/test_preflight_integration.py#L19-L72). *Recommendation:* require `state.status == "Running"` (and perhaps `state.cpu.usage` > 0) before considering a host available; otherwise raise a targeted skip with start instructions.
3. **Low – Skip marker and fixture disagree on required hosts.** `hosts_available()` returns true when *either* storage-01 **or** client-01 exists, so the collection-time skip never fires even if one VM is missing. The fixture then skips each test at runtime, but the failure reason appears late and duplicates work. Evidence: [tests/integration/test_preflight_integration.py](tests/integration/test_preflight_integration.py#L31-L72). *Recommendation:* make `hosts_available()` require both VMs (mirroring the fixture) or drop the decorator entirely so the skip logic lives in one place.
