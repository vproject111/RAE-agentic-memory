"""
Benchmark telemetry module for RAE.

Exports benchmark metrics to time-series format for monitoring and analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class BenchmarkTelemetry:
    """
    Records and exports benchmark metrics with timestamps.

    Provides a simple time-series database for tracking benchmark
    performance over time. Exports to JSON/CSV format.
    """

    def __init__(self, output_dir: str = "benchmarking/results/telemetry"):
        """
        Initialize telemetry system.

        Args:
            output_dir: Directory to store telemetry data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: List[Dict[str, Any]] = []

    def record_metric(
        self,
        benchmark: str,
        metric: str,
        value: float,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Record a single benchmark metric.

        Args:
            benchmark: Benchmark name (LECT, MMIT, GRDT, RST, MPEB, ORB)
            metric: Metric name (consistency, coherence, adaptation, etc.)
            value: Metric value
            timestamp: When metric was recorded (default: now)
            metadata: Additional context (config params, environment, etc.)
        """
        if timestamp is None:
            timestamp = datetime.now()

        record = {
            "timestamp": timestamp.isoformat(),
            "benchmark": benchmark,
            "metric": metric,
            "value": value,
            "metadata": metadata or {},
        }

        self.metrics.append(record)

    def export_json(self, filename: Optional[str] = None) -> Path:
        """
        Export metrics to JSON format.

        Args:
            filename: Output filename (default: telemetry_TIMESTAMP.json)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telemetry_{timestamp}.json"

        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            json.dump(self.metrics, f, indent=2)

        return output_path

    def export_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export metrics to CSV format.

        Args:
            filename: Output filename (default: telemetry_TIMESTAMP.csv)

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telemetry_{timestamp}.csv"

        output_path = self.output_dir / filename

        # Write CSV header
        with open(output_path, "w") as f:
            f.write("timestamp,benchmark,metric,value\n")

            # Write data rows
            for record in self.metrics:
                f.write(
                    f"{record['timestamp']},"
                    f"{record['benchmark']},"
                    f"{record['metric']},"
                    f"{record['value']}\n"
                )

        return output_path

    def export_timeseries(self, output_path: str, format: str = "json"):
        """
        Export metrics in time-series format.

        Args:
            output_path: Path to output file
            format: Export format ('json' or 'csv')
        """
        if format == "json":
            self.export_json(Path(output_path).name)
        elif format == "csv":
            self.export_csv(Path(output_path).name)
        else:
            raise ValueError(f"Unknown format: {format}")

    def get_latest_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Get latest value for each benchmark metric.

        Returns:
            Dict mapping benchmark -> metric -> latest value
        """
        latest: Dict[str, Dict[str, float]] = {}

        for record in self.metrics:
            benchmark = record["benchmark"]
            metric = record["metric"]
            value = record["value"]

            if benchmark not in latest:
                latest[benchmark] = {}

            latest[benchmark][metric] = value

        return latest

    def clear(self):
        """Clear all recorded metrics."""
        self.metrics.clear()
