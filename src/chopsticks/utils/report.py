"""Report utilities for pre-flight checks."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProbeResult:
    """Result of a single probe check."""
    
    probe_name: str
    host: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PreflightReport:
    """Aggregated pre-flight check report."""
    
    results: list[ProbeResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_result(self, result: ProbeResult) -> None:
        """Add a probe result to the report."""
        self.results.append(result)
    
    def all_passed(self) -> bool:
        """Check if all probes passed."""
        return all(r.passed for r in self.results)
    
    def get_summary(self) -> dict[str, dict[str, int]]:
        """Get summary statistics by host."""
        summary: dict[str, dict[str, int]] = {}
        
        for result in self.results:
            if result.host not in summary:
                summary[result.host] = {"total": 0, "passed": 0, "failed": 0}
            
            summary[result.host]["total"] += 1
            if result.passed:
                summary[result.host]["passed"] += 1
            else:
                summary[result.host]["failed"] += 1
        
        return summary
    
    def save_to_file(self, filepath: str) -> None:
        """Save report to YAML file."""
        path = Path(filepath)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "timestamp": self.timestamp,
            "summary": self.get_summary(),
            "results": [
                {
                    "probe": r.probe_name,
                    "host": r.host,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                    "timestamp": r.timestamp,
                }
                for r in self.results
            ],
        }
        
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
