"""Command-line interface for Chopsticks."""

import argparse
import os
import sys
from pathlib import Path

from chopsticks.config.config_loader import ConfigLoader


def main() -> int:
    """Main entry point for Chopsticks CLI."""
    parser = argparse.ArgumentParser(
        description="Chopsticks - Ceph stress testing framework"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a stress test")
    run_parser.add_argument(
        "--config",
        "-c",
        required=True,
        type=Path,
        help="Path to configuration file",
    )
    run_parser.add_argument(
        "--scenario",
        "-s",
        required=True,
        help="Scenario to run",
    )
    run_parser.add_argument(
        "--duration",
        "-d",
        type=int,
        default=300,
        help="Duration of test in seconds (default: 300)",
    )
    run_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no web UI)",
    )
    run_parser.add_argument(
        "--users",
        "-u",
        type=int,
        default=10,
        help="Number of users to spawn (default: 10)",
    )
    run_parser.add_argument(
        "--spawn-rate",
        "-r",
        type=int,
        default=1,
        help="Users to spawn per second (default: 1)",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "run":
        return run_test(args)
    
    return 0


def run_test(args: argparse.Namespace) -> int:
    """Run a stress test."""
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(args.config)
        
        # Set environment variable for config path
        os.environ["S3_CONFIG_PATH"] = str(args.config.absolute())
        
        # Set metrics configuration from config file
        metrics_config = config.get("metrics", {})
        if metrics_config.get("enabled", False):
            os.environ["METRICS_PORT"] = str(metrics_config.get("prometheus_port", 9646))
            if metrics_config.get("export_path"):
                os.environ["METRICS_EXPORT_PATH"] = metrics_config["export_path"]
        
        # Map scenario names to module paths
        scenario_map = {
            "large_objects": "chopsticks.scenarios.s3.large_objects:LargeObjectUser",
            "small_objects": "chopsticks.scenarios.s3.small_objects:SmallObjectUser",
            "mixed_objects": "chopsticks.scenarios.s3.mixed_workload:MixedWorkloadUser",
            "high_concurrency": "chopsticks.scenarios.s3.concurrent_access:ConcurrentAccessUser",
            "metadata_intensive": "chopsticks.scenarios.s3.metadata_intensive:MetadataIntensiveUser",
            "versioning_workload": "chopsticks.scenarios.s3.versioning_workload:VersioningWorkloadUser",
        }
        
        if args.scenario not in scenario_map:
            print(f"Error: Unknown scenario: {args.scenario}")
            print(f"Available scenarios: {', '.join(scenario_map.keys())}")
            return 1
        
        locustfile = scenario_map[args.scenario]
        
        # Build Locust command
        cmd_parts = [
            "locust",
            "-f", locustfile,
            "--users", str(args.users),
            "--spawn-rate", str(args.spawn_rate),
            "--run-time", f"{args.duration}s",
        ]
        
        if args.headless:
            cmd_parts.append("--headless")
        else:
            cmd_parts.extend(["--web-host", "0.0.0.0"])
        
        # Run Locust
        print(f"Running {args.scenario} scenario for {args.duration} seconds...")
        print(f"Command: {' '.join(cmd_parts)}")
        
        import subprocess
        result = subprocess.run(cmd_parts)
        
        return result.returncode
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
