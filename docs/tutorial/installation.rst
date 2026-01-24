Installation
============

This guide walks you through installing Chopsticks and its dependencies.

Prerequisites
-------------

* A Ceph cluster with S3 (RGW) endpoint
* S3 credentials (access key and secret key)
* Snapd (pre-installed on Ubuntu)

Option 1: Snap Installation (Recommended)
------------------------------------------

The snap package includes everything you need - chopsticks and s5cmd bundled together.

Step 1: Build the snap
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/canonical/chopsticks.git
   cd chopsticks
   snapcraft

Step 2: Install the snap
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   sudo snap install chopsticks_*.snap --dangerous --devmode

That's it! Chopsticks is now available as a command.

Option 2: Development Installation
-----------------------------------

For development and contributions, use the uv-based installation.

Prerequisites
~~~~~~~~~~~~~

* Python 3.12 or higher

Step 1: Install uv
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

Step 2: Clone the repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/canonical/chopsticks.git
   cd chopsticks

Step 3: Install dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   uv sync

This creates a virtual environment and installs all Python dependencies.

Step 4: Install s5cmd driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The S3 workload uses s5cmd as the default driver:

.. code-block:: bash

   ./scripts/install_s5cmd.sh

This installs s5cmd to ``~/.local/bin/s5cmd``.

Configure S3 Credentials
------------------------

Create a configuration file in your home directory.

For snap installation:

.. code-block:: bash

   mkdir -p ~/config
   nano ~/config/s3_config.yaml

For development installation:

.. code-block:: bash

   cp config/s3_config.yaml.example config/s3_config.yaml
   nano config/s3_config.yaml

Edit with your S3 endpoint details:

.. code-block:: yaml

   endpoint: https://your-s3-endpoint.com
   access_key: YOUR_ACCESS_KEY
   secret_key: YOUR_SECRET_KEY
   bucket: test-bucket
   region: us-east-1
   driver: s5cmd
   # s5cmd path is auto-detected

Verification
------------

Verify the installation:

**Snap installation:**

.. code-block:: bash

   # Check chopsticks is available
   chopsticks --help
   
   # Verify s5cmd is bundled
   chopsticks.s5cmd version

**Development installation:**

.. code-block:: bash

   # Check uv installation
   uv --version
   
   # Check s5cmd installation
   s5cmd version
   
   # Verify Python environment
   uv run python --version

You're now ready to run your first test!

Next steps
----------

* :doc:`first-test`
