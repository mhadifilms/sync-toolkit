#!/usr/bin/env python3
"""
API processing nodes.

Wraps API-related scripts as nodes.
"""
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from nodes.base import Node, InputPort, OutputPort, PortType, register_node


@register_node(metadata={"category": "api", "description": "Batch lipsync processing from manifest file"})
class BatchLipsyncNode(Node):
    """Batch lipsync processing from manifest file"""
    
    def _define_ports(self):
        self.inputs = {
            "manifest_file": InputPort(
                name="manifest_file",
                port_type=PortType.FILE,
                required=True,
                description="Manifest file with video/audio URLs"
            ),
            "start_index": InputPort(
                name="start_index",
                port_type=PortType.INTEGER,
                required=False,
                default=1,
                description="Start index"
            ),
            "end_index": InputPort(
                name="end_index",
                port_type=PortType.INTEGER,
                required=False,
                description="End index (inclusive)"
            ),
            "max_workers": InputPort(
                name="max_workers",
                port_type=PortType.INTEGER,
                required=False,
                default=15,
                description="Maximum parallel jobs"
            ),
            "output_dir": InputPort(
                name="output_dir",
                port_type=PortType.DIRECTORY,
                required=False,
                default="./outputs",
                description="Output directory for results"
            )
        }
        self.outputs = {
            "job_results": OutputPort(
                name="job_results",
                port_type=PortType.JSON_DATA,
                description="JSON data with job results"
            ),
            "output_directory": OutputPort(
                name="output_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing output files"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        manifest_file = Path(inputs["manifest_file"])
        start_index = inputs.get("start_index", 1)
        end_index = inputs.get("end_index")
        max_workers = inputs.get("max_workers", 15)
        output_dir = Path(inputs.get("output_dir", "./outputs"))
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "api" / "lipsync_batch.py"),
            "--manifest", str(manifest_file),
            "--start", str(start_index),
            "--max-workers", str(max_workers)
        ]
        if end_index:
            cmd.extend(["--end", str(end_index)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"lipsync_batch failed: {result.stderr}")
        
        # Load job results if available
        job_results = {}
        results_file = output_dir / "results.json"
        if results_file.exists():
            import json
            with open(results_file, 'r') as f:
                job_results = json.load(f)
        
        return {
            "job_results": job_results,
            "output_directory": str(output_dir)
        }


@register_node(metadata={"category": "api", "description": "Process CSV file with S3 URLs"})
class ProcessCSVNode(Node):
    """Process CSV file with S3 URLs and submit to Sync.so"""
    
    def _define_ports(self):
        self.inputs = {
            "csv_path": InputPort(
                name="csv_path",
                port_type=PortType.FILE,
                required=True,
                description="CSV file with S3 URLs"
            ),
            "limit": InputPort(
                name="limit",
                port_type=PortType.INTEGER,
                required=False,
                description="Limit number of rows to process"
            ),
            "test_mode": InputPort(
                name="test_mode",
                port_type=PortType.BOOLEAN,
                required=False,
                default=False,
                description="Test mode (process first row only)"
            )
        }
        self.outputs = {
            "results_json": OutputPort(
                name="results_json",
                port_type=PortType.JSON_DATA,
                description="JSON data with processing results"
            ),
            "job_ids": OutputPort(
                name="job_ids",
                port_type=PortType.JSON_DATA,
                description="List of job IDs"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        csv_path = Path(inputs["csv_path"])
        limit = inputs.get("limit")
        test_mode = inputs.get("test_mode", False)
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "api" / "s3_csv.py"),
            "--csv", str(csv_path)
        ]
        if limit:
            cmd.extend(["--limit", str(limit)])
        if test_mode:
            cmd.append("--test")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"s3_csv failed: {result.stderr}")
        
        # Parse results from output file
        results_json = {}
        job_ids = []
        
        # s3_csv.py saves results to a JSON file
        output_file = csv_path.parent / f"{csv_path.stem}_results.json"
        if output_file.exists():
            import json
            with open(output_file, 'r') as f:
                results_json = json.load(f)
                # Extract job IDs
                if isinstance(results_json, list):
                    job_ids = [item.get("job_id") for item in results_json if "job_id" in item]
                elif isinstance(results_json, dict) and "job_id" in results_json:
                    job_ids = [results_json["job_id"]]
        
        return {
            "results_json": results_json,
            "job_ids": job_ids
        }

