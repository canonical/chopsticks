# Ceph Benchmarking Tool (CBT) Research Notes

## Overview
- CBT is a Python-based harness for automating performance tests against Ceph clusters, covering cluster lifecycle tasks, benchmark execution, monitoring, and result collection ([CBT README](https://github.com/ceph/cbt/blob/master/README.md)).
- It supports running on pre-existing clusters or orchestrating OSD provisioning before each run, and can coordinate advanced test scenarios (OSD outages, erasure coding, cache tiers) ([CBT README](https://github.com/ceph/cbt/blob/master/README.md)).

## Core Modules & Benchmarks
- `radosbench`: Drives Ceph via the `rados` CLI for object store performance validation; creates per-client pools for isolation ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#radosbench)).
- `librbdfio`: Uses `fio` with the librbd engine to measure block storage without hypervisor overhead and approximates KVM/QEMU performance ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#librbdfio)).
- `kvmrbdfio`: Targets RBD volumes mapped into KVM guests, requiring pre-provisioned instances for OpenStack or similar stacks ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#kvmrbdfio)).
- `rbdfio`: Exercises kernel RBD mappings (KRBD) to emulate bare-metal block consumers ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#rbdfio)).
- Workload sequencing lets a benchmark vary parameters (e.g., queue depth) to generate latency curves, currently scoped to `librbdfio` ([Workloads doc](https://github.com/ceph/cbt/blob/master/docs/Workloads.md)).

## Configuration Model
- Test plans are YAML with mandatory top-level `cluster` and `benchmarks` sections; optional sections include `monitoring_profiles` and `client_endpoints` ([Test Plan Schema](https://github.com/ceph/cbt/blob/master/docs/TestPlanSchema.md)).
- `cluster` describes control node (`head`), benchmark clients, OSD nodes, monitors, filesystems, pool profiles, and toggles such as `use_existing` or OSD recreation policies ([Test Plan Schema](https://github.com/ceph/cbt/blob/master/docs/TestPlanSchema.md)).
- `benchmarks` enumerate one or more benchmark suites, each with parameter collections (runtime, block sizes, concurrency, iodepth, command paths) that CBT expands into test runs ([Test Plan Schema](https://github.com/ceph/cbt/blob/master/docs/TestPlanSchema.md#benchmarks)).
- `monitoring_profiles` declare metrics collectors (`collectl`, `perf`, `top`) and node scopes; `client_endpoints` bind benchmarks to endpoint drivers ([Test Plan Schema](https://github.com/ceph/cbt/blob/master/docs/TestPlanSchema.md#monitoring_profiles)).

## Dependencies & Environment Preparation
- Required packages: `python3-yaml`, `python3-lxml`, `ssh`, `scp`, `pdsh`, `pdcp`, plus Ceph client utilities ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#prerequisites)). Chopsticks bundles these runtime tools inside its snap so execution never depends on remote package managers.
- Optional tooling: `collectl`, `blktrace`, `seekwatcher`, `perf`, `valgrind`, `fio`, `cosbench`, `pytest` for richer monitoring and regression coverage ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#prerequisites)).
- Python dependencies are minimal (`pyyaml`, `lxml`, `matplotlib`) and listed in `requirements.txt` ([requirements.txt](https://github.com/ceph/cbt/blob/master/requirements.txt)). Chopsticks must capture these (and its own) Python requirements via `uv` lockfiles so the snap builds remain reproducible and centrally managed.
- Head node must have passwordless SSH and passwordless sudo to all cluster roles (clients, OSDs, monitors). Operators generate keys with `ssh-keygen` (or equivalent), then use the tool’s import commands to stage them on each node; the tool should verify both SSH trust and sudoers configuration match CBT expectations ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#user-and-node-setup)).
- Disk layout expectations: CBT searches for GPT labels `osd-device-<num>-data` and `osd-device-<num>-journal` when it provisions OSDs, assuming homogeneous device counts per node ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#disk-partitioning)). Chopsticks detects when MicroCeph already manages storage and forces CBT into `use_existing: true` mode to avoid provisioning conflicts.

## Running CBT
1. Clone repository and install Python dependencies (e.g., `pip install -r requirements.txt`).
2. Ensure supporting binaries (`fio`, `rados`, etc.) are available on benchmark clients.
3. Author a test plan YAML and, optionally, a matching `ceph.conf` tuned for the workload ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#creating-a-test-plan-yaml-file)).
4. Execute `cbt.py --archive <archive_dir> --conf <ceph.conf> <test_plan.yaml>` to launch runs and store logs/results under the archive directory ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#creating-a-test-plan-yaml-file)).
5. Use `mkcephconf.py` (tools directory) to generate configuration sweeps when exploring parameter matrices ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#creating-a-test-plan-yaml-file)).

## Result Handling & Monitoring
- CBT automatically captures system metrics via `collectl` and can extend to `perf`, `blktrace`, or `valgrind` depending on test plan directives ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#introduction)).
- Output archives include benchmark logs, system metrics, and optional generated reports; post-processing scripts (`post_processing/`, `include/`) can produce graphs (e.g., `plot_results.py`) or comparative reports.

## MicroCeph Primer (for CBT Integration)
- MicroCeph delivers Ceph as a snap, simplifying deployment across single-node or multi-node clusters ([MicroCeph README](https://github.com/canonical/microceph#installation)).
- Single-node workflow: `sudo snap install microceph`, `sudo snap refresh --hold microceph`, `sudo microceph cluster bootstrap`, then add storage via `sudo microceph disk add loop,4G,3` and inspect cluster health with `sudo microceph status` ([Get started tutorial](https://canonical-microceph.readthedocs-hosted.com/latest/tutorial/get-started/?plain=1#install-microceph)).
- RGW enablement (for S3 workloads) uses `sudo microceph enable rgw [--port <port>]`, and user creation via `sudo radosgw-admin user create ...`; access is confirmed with standard S3 tooling like `aws-cli` ([Get started tutorial](https://canonical-microceph.readthedocs-hosted.com/latest/tutorial/get-started/?plain=1#enable-rgw)).
- Multi-node clusters: install microceph on each node, bootstrap on the primary, generate join tokens with `sudo microceph cluster add <node>`, join secondary nodes using `microceph cluster join <token>`, and attach physical disks with `microceph disk add <device> --wipe` ([Multi-node install guide](https://canonical-microceph.readthedocs-hosted.com/latest/how-to/multi-node/?plain=1#prepare-the-cluster)).
- Additional services (NFS, RGW, cephfs-mirror) can be explicitly placed using `microceph enable <service> --target <node> ...`, complementing CBT scenarios that rely on specific gateways ([Enable service instances](https://canonical-microceph.readthedocs-hosted.com/latest/how-to/enable-service-instances/?plain=1#enable-an-rgw-service)).
- MicroCeph exposes native Ceph tooling; administrators can run `sudo ceph <command>` where snap-level commands are insufficient ([MicroCeph README](https://github.com/canonical/microceph#basic-usage)).

## Designing a CBT Automation Tool for MicroCeph
### Responsibilities
- **Cluster discovery**: Query `microceph status` to list nodes and roles; map them into CBT test plan sections (head, clients, osds, mons).
- **Credential import**: Assume the operator generates the SSH keypair out-of-band and supplies both private and public keys. Provide snap commands to ingest these keys on each node, install them under the correct account (e.g., `/home/<user>/.ssh/{id_rsa,id_rsa.pub}`), set permissions, and confirm both passwordless SSH and sudo access align with CBT prerequisites ([CBT README](https://github.com/ceph/cbt/blob/master/README.md#user-and-node-setup)).
- **Bundled dependencies**: Ship `pdsh`, `fio`, monitoring helpers, and Python libraries directly inside the Chopsticks snap, ensuring consistent versions across nodes without invoking remote package managers. Require the Chopsticks snap on the controller and every participating node so the packaged binaries are available locally, and validate availability by executing the bundled tooling through classic confinement interfaces.
- **Controller/head alignment**: Treat the Chopsticks controller as the CBT head node, guaranteeing it has passwordless SSH and sudo access to every participant, and size its resources (CPU, RAM, disk) for sustained benchmark orchestration while documenting alternative head-node deployments as future work.
- **CBT deployment**: Implement the automation tool in Python adhering to language best practices (packaging with `pyproject.toml`, type hints, logging, unit tests) and manage dependencies with `uv`; vendor CBT via a dedicated snap part pinned to a reviewed tag/commit, and manage configuration files (test plans, `ceph.conf`) per scenario.
- **CBT payload management**: Maintain dual `uv` environments (core vs CBT) with independent lockfiles, run conflict detection tests, and update a compatibility matrix (Chopsticks version × CBT tag × MicroCeph channel × Ubuntu release) whenever dependencies change. Provide scripts that refresh the vendored CBT snapshot while preserving reproducibility and emit runtime warnings when operators exercise untested combinations.
- **Test plan templating**: Generate YAML templates aligned with MicroCeph topology (pool profiles, replication, selected benchmarks). Allow parameterization of workloads to cover RBD and object tests.
- **Execution control**: Run `cbt.py` from the bundled environment with appropriate archive directories, capturing exit codes, stdout/stderr, and aggregating run metadata via structured modules (logging, subprocess wrappers, dataclasses) with timeout, retry, and cancellation support.
- **Result management**: Collect archives, optionally parse metrics (`plot_results.py`, post-processing scripts), store artifacts for downstream analysis using typed pipelines and reusable utilities, and enforce retention policies (default keep latest 10 archives with operator overrides) plus disk space monitoring hooks.
- **Cleanup hooks**: Provide opt-in commands (and systemd-triggered jobs) that tear down CBT-generated resources, confirm MicroCeph returns to baseline health, and document rollback sequences when cleanup is skipped.
- **Configuration staging**: Accept operator-provided Ceph settings (e.g., `ceph.conf` fragments, monitor/map details, keyring contents) via CLI, materialize them into canonical files (`ceph.conf`, `ceph.keyring`) in tool-managed directories, and validate syntax before kicking off CBT. Assume no direct access to MicroCeph CLI or on-node configuration files; the operator must supply all required values explicitly.

### Integration Considerations
- MicroCeph nodes are managed via snap services; the tool should respect snap confinement and leverage native Ceph CLI (`sudo ceph <command>`) when snap-level wrappers are insufficient (e.g., inspecting `ceph.conf`).
- MicroCeph cluster bootstrap and join operations remain outside Chopsticks scope; operators must complete these steps before running pre-flight checks.
- Disk provisioning strategies differ: CBT expects labeled partitions for automated OSD creation, whereas MicroCeph’s `disk add` handles device preparation. Tool should detect when to rely on MicroCeph’s orchestration versus CBT-managed OSD lifecycle.
- For multi-node clusters, operators remain responsible for generating and consuming MicroCeph join tokens prior to using Chopsticks; the tool only validates resulting cluster quorum and records token usage metadata for troubleshooting ([Multi-node install guide](https://canonical-microceph.readthedocs-hosted.com/latest/how-to/multi-node/?plain=1#join-the-non-primary-nodes-to-the-cluster)).
- RGW or NFS workloads may require enabling additional services; the automation flow should expose toggles for `microceph enable` commands prior to CBT runs ([Enable service instances](https://canonical-microceph.readthedocs-hosted.com/latest/how-to/enable-service-instances/?plain=1#enable-an-rgw-service)).
- Because Chopsticks ships all runtime binaries, include health checks to confirm the packaged tools execute correctly on each node, require the snap to be installed on every participant, and document the refresh cadence for vendored artifacts (including license reviews and integrity verification).
- Provide dedicated CLI commands for installing operator-supplied keys: accept file paths or stdin, enforce `0600` permissions on private keys, `0644` on public keys, ensure `.ssh` directories have `0700` permissions before validating SSH access, and implement the logic with robust tooling (e.g., `pathlib`, `subprocess`, `click` or `argparse`).
- Expose convenience commands to ingest operator-provided Ceph configuration data (raw values or file paths), render `ceph.conf` and `ceph.keyring` under predictable locations, set strict permissions (`0600`), and surface validation errors clearly without assuming access to MicroCeph nodes.
- After importing keys, automatically test that `sudo` can be executed without a password on each target node and raise actionable errors if the requirement is not satisfied.
- Evaluate background workflows that benefit from `systemd` management (e.g., a `chopd` service to execute CBT jobs asynchronously, and timers that periodically revalidate SSH/sudo health or rotate logs) so long-lived tasks survive terminal sessions and integrate with host logging.
- Surface compatibility matrix checks before execution, warning operators when they attempt unvalidated combinations and linking to the published matrix for support expectations.

### Suggested Workflow
1. Validate MicroCeph cluster state (`microceph status`, optional `sudo ceph status`) and confirm required services are active.
2. Operator generates the SSH keypair and provides both private and public keys to the tool. Use the snap’s key-import commands on the leader and follower nodes so the tool can place the keys securely and verify connectivity.
3. Install or refresh the Chopsticks snap on the controller and every participating node so bundled dependencies (`pdsh`, `fio`, monitoring helpers) are present locally, and run `uv` sync as part of the snap build hooks to keep both environments aligned with their lockfiles.
4. Feed operator-supplied Ceph configuration values into the snap’s config commands so the tool can assemble `ceph.conf` and `ceph.keyring`, then sanity-check the rendered files.
5. Render CBT test plan(s) based on cluster topology and desired benchmarks (RADOS, RBD, RGW scenarios).
6. Execute CBT runs from the controller/head node using the packaged CBT, monitor progress, and collect metrics while updating the compatibility matrix with tested combinations.
7. Summarize results, upload artifacts, enforce archive retention policies (or adjust per operator preference), and (optionally) roll back temporary services or configurations.

## Reference Links
- CBT project: https://github.com/ceph/cbt
- MicroCeph project: https://github.com/canonical/microceph
- MicroCeph documentation (latest): https://canonical-microceph.readthedocs-hosted.com/latest/