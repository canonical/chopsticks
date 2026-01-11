# Integration Test Setup

This document describes how to set up the environment for running integration tests.

## Prerequisites

Integration tests require the following tools installed:

1. **LXD**: Container/VM hypervisor
   ```bash
   snap install lxd
   lxd init --auto
   ```

2. **uv**: Python package manager
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## Test VM Setup

Integration tests expect two LXD VMs to be available:

### storage-01 (MicroCeph Storage Node)

```bash
# Launch Ubuntu 22.04 VM
lxc launch ubuntu:22.04 storage-01 --vm

# Wait for VM to boot
lxc exec storage-01 -- cloud-init status --wait

# Install MicroCeph
lxc exec storage-01 -- snap install microceph
lxc exec storage-01 -- snap refresh --hold microceph
lxc exec storage-01 -- microceph cluster bootstrap

# Add OSDs (file-backed for testing)
lxc exec storage-01 -- microceph disk add loop,4G,3

# Verify cluster
lxc exec storage-01 -- microceph status
lxc exec storage-01 -- ceph status
```

### client-01 (Non-Ceph Node)

```bash
# Launch Ubuntu 22.04 VM (no MicroCeph)
lxc launch ubuntu:22.04 client-01 --vm

# Wait for VM to boot
lxc exec client-01 -- cloud-init status --wait
```

## Running Integration Tests

Once VMs are set up, run integration tests explicitly:

```bash
# From project root
cd /path/to/chopsticks

# Run all integration tests
uv run pytest -m integration -v

# Run specific integration test
uv run pytest tests/integration/test_preflight_integration.py::test_preflight_storage_01 -v
```

## Troubleshooting

### Test Skipped with Missing Dependencies Message

If you see a skip message like:
```
SKIPPED: Missing integration test dependencies:
  - LXD - Install: snap install lxd && lxd init --auto
  - LXD VM 'storage-01' - See tests/integration/README.md for setup
```

Follow the installation instructions provided in the skip message.

### VM Not Responding

If tests timeout or VMs don't respond:

```bash
# Check VM status
lxc list

# Restart VM
lxc restart storage-01

# Check VM logs
lxc console storage-01 --show-log
```

### MicroCeph Issues

If MicroCeph isn't working in storage-01:

```bash
# Check MicroCeph status
lxc exec storage-01 -- microceph status

# View Ceph cluster status
lxc exec storage-01 -- ceph -s

# Check MicroCeph logs
lxc exec storage-01 -- snap logs microceph
```

## Cleanup

To remove test VMs:

```bash
lxc delete storage-01 --force
lxc delete client-01 --force
```

## CI/CD Considerations

For CI environments:

1. Use LXD in container mode (not VM) for faster startup
2. Pre-build images with MicroCeph installed
3. Consider using GitHub Actions LXD setup actions
4. Set appropriate timeouts for VM boot and cluster initialization
