# Chopsticks Snap

This directory contains the snapcraft configuration to package Chopsticks as a snap.

## Building the Snap

To build the snap locally:

```bash
snapcraft
```

This will create a `chopsticks_<version>_<arch>.snap` file in the project root.

## Installing Locally

To install the snap you just built:

```bash
# Install the locally built snap
sudo snap install chopsticks_*.snap --dangerous --devmode
```

## Using Chopsticks

Once installed, you can use chopsticks as a command:

```bash
# Run with web UI
chopsticks --workload-config ~/config/s3_config.yaml \
  -f /snap/chopsticks/current/usr/local/lib/python3.12/dist-packages/chopsticks/scenarios/s3_large_objects.py

# Run headless
chopsticks --workload-config ~/config/s3_config.yaml \
  -f /snap/chopsticks/current/usr/local/lib/python3.12/dist-packages/chopsticks/scenarios/s3_large_objects.py \
  --headless --users 10 --spawn-rate 2 --duration 5m
```

Note: The snap has access to files in your home directory via the `home` plug.

## What's Included

The snap bundles:

- **chopsticks** - Main application binary
- **chopsticks.s5cmd** - S3 client driver for high-performance operations
- **Python dependencies** - All required Python packages

Both commands are available after installation:

```bash
chopsticks --help
chopsticks.s5cmd version
```

## Permissions

The snap uses strict confinement with the following plugs:

- `network` - Required for connecting to Ceph/S3 endpoints
- `network-bind` - Required for Locust web UI and metrics server
- `home` - Access to configuration files and test data in home directory

## Development

### Cleaning Build Artifacts

```bash
snapcraft clean
```

### Building for Different Architectures

```bash
# Build for arm64
snapcraft --target-arch=arm64
```

## Troubleshooting

### Snap doesn't see my config files

Make sure your config files are in your home directory. The snap has access to `$HOME` via the `home` plug.

### Permission denied errors

Check that the necessary plugs are connected:

```bash
snap connections chopsticks
```

To manually connect a plug if needed:

```bash
sudo snap connect chopsticks:network
sudo snap connect chopsticks:network-bind
sudo snap connect chopsticks:home
```
