# Phase 0 Review – Round 4 Findings

## Summary
- High severity: 2

## Findings
1. **High – SSH transport cannot execute MicroCeph probes without sudo.** The roadmap expectation is controller-only network reachability, yet `check_microceph_status` and `check_ceph_status` now run through the SSH executor as the supplied user (default `ubuntu`) without privilege escalation. On a stock MicroCeph host those commands require `sudo`, so the new SSH path consistently fails with `Permission denied` and the pre-flight exits non-zero. Evidence: [src/chopsticks/probes/cluster_health.py](src/chopsticks/probes/cluster_health.py#L13-L75), [src/chopsticks/utils/ssh.py](src/chopsticks/utils/ssh.py#L28-L81). *Recommendation:* wrap MicroCeph/Ceph invocations with `sudo` (or allow configurable command prefixes) when using SSH.
2. **High – OSD disk probe manufactures non-existent paths.** When `ceph osd df --format json` succeeds, `get_microceph_osd_paths` ignores the actual OSD IDs and instead generates `ceph-{index+1}` directories. With three OSDs (ids 0,1,2) this checks `ceph-1`, `ceph-2`, and a bogus `ceph-3`, skipping `ceph-0` and flagging the fake path as “inaccessible”, so healthy clusters fail pre-flight. Evidence: [src/chopsticks/probes/resources.py](src/chopsticks/probes/resources.py#L76-L166). *Recommendation:* use the real IDs from the JSON payload (e.g., `node['id']`) or rely solely on directory enumeration so only existing OSD paths are validated.
