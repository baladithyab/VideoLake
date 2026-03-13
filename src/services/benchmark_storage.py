"""
Benchmark Results Storage

Handles persistence and retrieval of comprehensive benchmark results.
Supports local JSON storage and optional S3 sync for distributed access.
"""

import json
import boto3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict
import logging

from src.services.comprehensive_benchmark import BenchmarkDimensions

logger = logging.getLogger(__name__)


class BenchmarkStorage:
    """
    Persistent storage for benchmark results.

    Stores results as JSON files locally with optional S3 sync.
    Organizes by session_id and variant for easy querying.
    """

    def __init__(self, base_dir: Path, s3_bucket: Optional[str] = None, s3_prefix: str = "benchmarks"):
        """
        Initialize storage.

        Args:
            base_dir: Local directory for results
            s3_bucket: Optional S3 bucket for remote storage
            s3_prefix: S3 key prefix
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_client = boto3.client('s3') if s3_bucket else None

        # Create index file if it doesn't exist
        self.index_file = self.base_dir / "index.json"
        if not self.index_file.exists():
            self._write_index({"sessions": {}, "variants": {}})

    def _read_index(self) -> Dict[str, Any]:
        """Read the master index"""
        with open(self.index_file, 'r') as f:
            return json.load(f)

    def _write_index(self, index: Dict[str, Any]):
        """Write the master index"""
        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def store_variant_results(
        self,
        variant_name: str,
        results: List[BenchmarkDimensions],
        session_id: str,
        metadata: Optional[Dict] = None
    ):
        """
        Store results for a variant.

        Args:
            variant_name: Variant identifier
            results: List of benchmark results
            session_id: Session identifier
            metadata: Optional metadata
        """
        # Convert dataclass to dict
        results_dict = [asdict(r) for r in results]

        # Create session directory
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save variant results
        variant_file = session_dir / f"{variant_name}.json"
        with open(variant_file, 'w') as f:
            json.dump({
                "variant": variant_name,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
                "results": results_dict
            }, f, indent=2, default=str)

        logger.info(f"Stored results for {variant_name} in session {session_id}")

        # Update index
        index = self._read_index()

        if session_id not in index["sessions"]:
            index["sessions"][session_id] = {
                "timestamp": datetime.now().isoformat(),
                "variants": []
            }

        if variant_name not in index["sessions"][session_id]["variants"]:
            index["sessions"][session_id]["variants"].append(variant_name)

        if variant_name not in index["variants"]:
            index["variants"][variant_name] = []

        index["variants"][variant_name].append({
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "result_count": len(results)
        })

        self._write_index(index)

        # Sync to S3 if configured
        if self.s3_client and self.s3_bucket:
            try:
                s3_key = f"{self.s3_prefix}/{session_id}/{variant_name}.json"
                self.s3_client.upload_file(
                    str(variant_file),
                    self.s3_bucket,
                    s3_key
                )
                logger.info(f"Synced to S3: s3://{self.s3_bucket}/{s3_key}")
            except Exception as e:
                logger.warning(f"Failed to sync to S3: {e}")

    def load_variant_results(self, variant_name: str, session_id: str) -> Optional[List[Dict]]:
        """
        Load results for a variant.

        Args:
            variant_name: Variant identifier
            session_id: Session identifier

        Returns:
            List of result dictionaries or None if not found
        """
        variant_file = self.base_dir / session_id / f"{variant_name}.json"

        if not variant_file.exists():
            logger.warning(f"Results not found: {variant_file}")
            return None

        with open(variant_file, 'r') as f:
            data = json.load(f)
            return data.get("results", [])

    def load_session_results(self, session_id: str) -> Dict[str, List[Dict]]:
        """
        Load all results for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary mapping variant names to result lists
        """
        index = self._read_index()
        session_info = index["sessions"].get(session_id)

        if not session_info:
            logger.warning(f"Session not found: {session_id}")
            return {}

        results = {}
        for variant_name in session_info["variants"]:
            variant_results = self.load_variant_results(variant_name, session_id)
            if variant_results:
                results[variant_name] = variant_results

        return results

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all benchmark sessions.

        Returns:
            List of session info dictionaries
        """
        index = self._read_index()
        sessions = []

        for session_id, info in index["sessions"].items():
            sessions.append({
                "session_id": session_id,
                "timestamp": info["timestamp"],
                "variants": info["variants"],
                "variant_count": len(info["variants"])
            })

        # Sort by timestamp descending
        sessions.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions

    def list_variants(self) -> List[str]:
        """
        List all tested variants.

        Returns:
            List of variant names
        """
        index = self._read_index()
        return list(index["variants"].keys())

    def get_variant_history(self, variant_name: str) -> List[Dict[str, Any]]:
        """
        Get benchmark history for a variant across sessions.

        Args:
            variant_name: Variant identifier

        Returns:
            List of historical results
        """
        index = self._read_index()
        history = index["variants"].get(variant_name, [])

        # Load detailed results for each session
        detailed_history = []
        for entry in history:
            session_id = entry["session_id"]
            results = self.load_variant_results(variant_name, session_id)
            if results:
                detailed_history.append({
                    "session_id": session_id,
                    "timestamp": entry["timestamp"],
                    "results": results
                })

        return detailed_history

    def get_latest_session(self) -> Optional[str]:
        """Get the most recent session ID"""
        sessions = self.list_sessions()
        return sessions[0]["session_id"] if sessions else None

    def export_to_s3(self, session_id: Optional[str] = None):
        """
        Export results to S3.

        Args:
            session_id: Specific session to export, or None for all
        """
        if not self.s3_client or not self.s3_bucket:
            logger.error("S3 not configured")
            return

        sessions_to_export = [session_id] if session_id else [s["session_id"] for s in self.list_sessions()]

        for sid in sessions_to_export:
            session_dir = self.base_dir / sid
            if not session_dir.exists():
                continue

            for variant_file in session_dir.glob("*.json"):
                try:
                    s3_key = f"{self.s3_prefix}/{sid}/{variant_file.name}"
                    self.s3_client.upload_file(
                        str(variant_file),
                        self.s3_bucket,
                        s3_key
                    )
                    logger.info(f"Exported: s3://{self.s3_bucket}/{s3_key}")
                except Exception as e:
                    logger.error(f"Failed to export {variant_file}: {e}")

    def compare_variants(
        self,
        variant_names: List[str],
        session_id: Optional[str] = None,
        metric: str = "throughput_qps"
    ) -> Dict[str, Any]:
        """
        Compare multiple variants on a specific metric.

        Args:
            variant_names: List of variants to compare
            session_id: Session to use (default: latest)
            metric: Metric to compare

        Returns:
            Comparison dictionary
        """
        if not session_id:
            session_id = self.get_latest_session()

        if not session_id:
            return {"error": "No sessions found"}

        comparison = {
            "session_id": session_id,
            "metric": metric,
            "variants": {}
        }

        for variant_name in variant_names:
            results = self.load_variant_results(variant_name, session_id)
            if results:
                # Get the metric value from the first (or average across all) results
                values = [r.get(metric) for r in results if r.get(metric) is not None]
                if values:
                    comparison["variants"][variant_name] = {
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "values": values
                    }

        # Rank variants by metric
        if comparison["variants"]:
            # For latency metrics, lower is better
            reverse = "latency" not in metric.lower()
            ranked = sorted(
                comparison["variants"].items(),
                key=lambda x: x[1]["mean"],
                reverse=reverse
            )
            comparison["ranked"] = [{"variant": v, "mean": data["mean"]} for v, data in ranked]

        return comparison
