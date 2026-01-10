"""Pre-flight check CLI command."""

import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from chopsticks.probes.cluster_health import check_microceph_status, check_ceph_status
from chopsticks.probes.network import check_network_reachability
from chopsticks.probes.resources import check_disk_capacity, check_host_resources
from chopsticks.utils.report import PreflightReport, ProbeResult
from chopsticks.utils.ssh import RemoteExecutor


console = Console()


@click.command()
@click.option(
    "--host",
    multiple=True,
    required=True,
    help="Target host(s) to check (can be specified multiple times)",
)
@click.option(
    "--transport",
    type=click.Choice(["ssh", "lxd"]),
    default="lxd",
    help="Transport method: ssh for production, lxd for development (default: lxd)",
)
@click.option(
    "--user",
    default="ubuntu",
    help="SSH username (ignored for lxd transport, default: ubuntu)",
)
@click.option(
    "--skip-ceph-status",
    is_flag=True,
    help="Skip detailed 'ceph status' check",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Write structured report to file (YAML format)",
)
def preflight(
    host: tuple[str, ...],
    transport: str,
    user: str,
    skip_ceph_status: bool,
    output: Optional[str],
) -> None:
    """Run pre-flight checks against MicroCeph cluster."""
    console.print("\n[bold cyan]Chopsticks Pre-Flight Checks[/bold cyan]\n")
    
    # Create remote executor for this run
    executor = RemoteExecutor(transport=transport, user=user)
    
    report = PreflightReport()
    
    # Run probes for each host
    for target_host in host:
        console.print(f"[bold]Checking host: {target_host}[/bold]")
        
        # Cluster health checks
        result = check_microceph_status(target_host, executor)
        report.add_result(result)
        _display_probe_result(result)
        
        if not skip_ceph_status:
            result = check_ceph_status(target_host, executor)
            report.add_result(result)
            _display_probe_result(result)
        
        # Network reachability
        result = check_network_reachability(target_host, executor)
        report.add_result(result)
        _display_probe_result(result)
        
        # Disk capacity
        result = check_disk_capacity(target_host, executor)
        report.add_result(result)
        _display_probe_result(result)
        
        # Host resources
        result = check_host_resources(target_host, executor)
        report.add_result(result)
        _display_probe_result(result)
        
        console.print()
    
    # Summary table
    _display_summary(report)
    
    # Save report if requested
    if output:
        report.save_to_file(output)
        console.print(f"\n[green]Report saved to: {output}[/green]")
    
    # Exit with appropriate code
    if not report.all_passed():
        console.print("\n[bold red]❌ Pre-flight checks failed[/bold red]")
        sys.exit(1)
    else:
        console.print("\n[bold green]✅ All pre-flight checks passed[/bold green]")


def _display_probe_result(result: ProbeResult) -> None:
    """Display a single probe result."""
    status_icon = "✅" if result.passed else "❌"
    status_color = "green" if result.passed else "red"
    
    console.print(f"  {status_icon} [{status_color}]{result.probe_name}[/{status_color}]")
    
    if result.message:
        console.print(f"    {result.message}")
    
    if result.details:
        for key, value in result.details.items():
            console.print(f"    • {key}: {value}")


def _display_summary(report: PreflightReport) -> None:
    """Display summary table of all checks."""
    table = Table(title="Pre-Flight Summary")
    table.add_column("Host", style="cyan")
    table.add_column("Total Checks", justify="right")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    
    summary = report.get_summary()
    for host, stats in summary.items():
        table.add_row(
            host,
            str(stats["total"]),
            str(stats["passed"]),
            str(stats["failed"]),
        )
    
    console.print(table)
