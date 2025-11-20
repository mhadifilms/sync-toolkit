#!/usr/bin/env python3
"""
Utility nodes for data transformation and processing.

Wraps utility scripts as nodes.
"""
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from nodes.base import Node, InputPort, OutputPort, PortType, register_node


@register_node(metadata={"category": "utility", "description": "Convert timecodes between frame rates"})
class ConvertTimecodesNode(Node):
    """Convert timecodes between frame rates"""
    
    def _define_ports(self):
        self.inputs = {
            "input_csv": InputPort(
                name="input_csv",
                port_type=PortType.FILE,
                required=True,
                description="Input CSV file with timecodes"
            ),
            "source_fps": InputPort(
                name="source_fps",
                port_type=PortType.STRING,
                required=True,
                description="Source frame rate (e.g., 24, 23.976)"
            ),
            "target_fps": InputPort(
                name="target_fps",
                port_type=PortType.STRING,
                required=True,
                description="Target frame rate (e.g., 24, 23.976)"
            ),
            "output_csv": InputPort(
                name="output_csv",
                port_type=PortType.FILE,
                required=False,
                description="Output CSV file path"
            )
        }
        self.outputs = {
            "output_csv": OutputPort(
                name="output_csv",
                port_type=PortType.FILE,
                description="Path to converted CSV file"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        input_csv = Path(inputs["input_csv"])
        source_fps = inputs["source_fps"]
        target_fps = inputs["target_fps"]
        output_csv = inputs.get("output_csv")
        
        if not output_csv:
            output_csv = input_csv.parent / f"{input_csv.stem}_converted.csv"
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "utils" / "timecode.py"),
            "--input-csv", str(input_csv),
            "--output-csv", str(output_csv),
            "--source-fps", source_fps,
            "--target-fps", target_fps
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"convert_timecodes failed: {result.stderr}")
        
        return {
            "output_csv": str(output_csv)
        }


@register_node(metadata={"category": "utility", "description": "Monitor S3 upload progress"})
class MonitorS3Node(Node):
    """Monitor S3 upload progress"""
    
    def _define_ports(self):
        self.inputs = {
            "s3_path": InputPort(
                name="s3_path",
                port_type=PortType.STRING,
                required=True,
                description="S3 path to monitor"
            ),
            "expected_count": InputPort(
                name="expected_count",
                port_type=PortType.INTEGER,
                required=True,
                description="Expected number of files"
            ),
            "interval": InputPort(
                name="interval",
                port_type=PortType.INTEGER,
                required=False,
                default=180,
                description="Check interval in seconds"
            )
        }
        self.outputs = {
            "status_json": OutputPort(
                name="status_json",
                port_type=PortType.JSON_DATA,
                description="Status information"
            ),
            "completion_event": OutputPort(
                name="completion_event",
                port_type=PortType.BOOLEAN,
                description="True when monitoring completes"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        s3_path = inputs["s3_path"]
        expected_count = inputs["expected_count"]
        interval = inputs.get("interval", 180)
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "monitor" / "s3_monitor.py"),
            "--s3-path", s3_path,
            "--expected", str(expected_count),
            "--interval", str(interval)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"s3_monitor failed: {result.stderr}")
        
        # Parse status from output
        status_json = {
            "s3_path": s3_path,
            "expected_count": expected_count,
            "completed": result.returncode == 0
        }
        
        return {
            "status_json": status_json,
            "completion_event": result.returncode == 0
        }


@register_node(metadata={"category": "utility", "description": "Create manifest file from video/audio lists"})
class CreateManifestNode(Node):
    """Create manifest file from video/audio URL lists"""
    
    def _define_ports(self):
        self.inputs = {
            "video_urls": InputPort(
                name="video_urls",
                port_type=PortType.URL_LIST,
                required=False,
                description="List of video URLs"
            ),
            "audio_urls": InputPort(
                name="audio_urls",
                port_type=PortType.URL_LIST,
                required=False,
                description="List of audio URLs"
            ),
            "output_file": InputPort(
                name="output_file",
                port_type=PortType.FILE,
                required=False,
                default="uploaded_urls.txt",
                description="Output manifest file path"
            )
        }
        self.outputs = {
            "manifest_file": OutputPort(
                name="manifest_file",
                port_type=PortType.FILE,
                description="Path to created manifest file"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        from pathlib import Path
        
        video_urls = inputs.get("video_urls", [])
        audio_urls = inputs.get("audio_urls", [])
        output_file = Path(inputs.get("output_file", "uploaded_urls.txt"))
        
        # Write manifest file
        with open(output_file, 'w') as f:
            if video_urls:
                f.write("VIDEOS\n")
                for url in video_urls:
                    f.write(f"{url}\n")
                f.write("\n")
            
            if audio_urls:
                f.write("AUDIOS\n")
                for url in audio_urls:
                    f.write(f"{url}\n")
        
        return {
            "manifest_file": str(output_file)
        }


@register_node(metadata={"category": "utility", "description": "Merge multiple result JSONs"})
class MergeResultsNode(Node):
    """Merge multiple result JSON files"""
    
    def _define_ports(self):
        self.inputs = {
            "result_files": InputPort(
                name="result_files",
                port_type=PortType.FILE_LIST,
                required=True,
                description="List of JSON result files to merge"
            ),
            "output_file": InputPort(
                name="output_file",
                port_type=PortType.FILE,
                required=False,
                description="Output merged JSON file path"
            )
        }
        self.outputs = {
            "merged_json": OutputPort(
                name="merged_json",
                port_type=PortType.JSON_DATA,
                description="Merged JSON data"
            ),
            "output_file": OutputPort(
                name="output_file",
                port_type=PortType.FILE,
                description="Path to merged JSON file"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import json
        from pathlib import Path
        
        result_files = [Path(f) for f in inputs["result_files"]]
        output_file = inputs.get("output_file")
        
        if not output_file:
            output_file = result_files[0].parent / "merged_results.json"
        else:
            output_file = Path(output_file)
        
        # Load and merge all JSON files
        merged_data = []
        for result_file in result_files:
            if result_file.exists():
                with open(result_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged_data.extend(data)
                    else:
                        merged_data.append(data)
        
        # Write merged data
        with open(output_file, 'w') as f:
            json.dump(merged_data, f, indent=2)
        
        return {
            "merged_json": merged_data,
            "output_file": str(output_file)
        }

