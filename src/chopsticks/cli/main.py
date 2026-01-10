"""Main CLI entry point for Chopsticks."""

import click
from chopsticks.cli.preflight import preflight


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """Chopsticks - Prepares and runs CBT against MicroCeph clusters."""
    pass


cli.add_command(preflight)


if __name__ == "__main__":
    cli()
