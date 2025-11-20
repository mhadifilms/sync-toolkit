#!/usr/bin/env python3
"""
Storage nodes for uploading and downloading files.

Wraps storage transfer scripts as nodes.
"""
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from nodes.base import Node, InputPort, OutputPort, PortType, register_node


@register_node(metadata={"category": "storage", "description": "Upload files to Supabase Storage"})
class UploadSupabaseNode(Node):
    """Upload files to Supabase Storage"""
    
    def _define_ports(self):
        self.inputs = {
            "local_path": InputPort(
                name="local_path",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Local directory or file to upload"
            ),
            "bucket": InputPort(
                name="bucket",
                port_type=PortType.STRING,
                required=False,
                description="Supabase bucket name"
            ),
            "remote_path": InputPort(
                name="remote_path",
                port_type=PortType.STRING,
                required=False,
                description="Remote path prefix"
            )
        }
        self.outputs = {
            "uploaded_urls": OutputPort(
                name="uploaded_urls",
                port_type=PortType.URL_LIST,
                description="List of uploaded file URLs"
            ),
            "manifest_file": OutputPort(
                name="manifest_file",
                port_type=PortType.FILE,
                description="Path to manifest file with uploaded URLs"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(SCRIPT_DIR))
        
        local_path = Path(inputs["local_path"])
        bucket = inputs.get("bucket")
        remote_path = inputs.get("remote_path")
        
        # Call sb_upload.py
        cmd = [sys.executable, str(SCRIPT_DIR / "transfer" / "sb_upload.py"), str(local_path)]
        if bucket:
            cmd.extend(["--bucket", bucket])
        if remote_path:
            cmd.extend(["--remote-path", remote_path])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"sb_upload failed: {result.stderr}")
        
        # Parse uploaded URLs from output or manifest file
        uploaded_urls = []
        manifest_file = local_path.parent / "uploaded_urls.txt"
        
        if manifest_file.exists():
            from utils.common import parse_manifest
            video_urls, audio_urls = parse_manifest(manifest_file)
            uploaded_urls = video_urls + audio_urls
        
        return {
            "uploaded_urls": uploaded_urls,
            "manifest_file": str(manifest_file) if manifest_file.exists() else None
        }


@register_node(metadata={"category": "storage", "description": "Upload files to AWS S3"})
class UploadS3Node(Node):
    """Upload files to AWS S3"""
    
    def _define_ports(self):
        self.inputs = {
            "local_directory": InputPort(
                name="local_directory",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Local directory to upload"
            ),
            "s3_destination": InputPort(
                name="s3_destination",
                port_type=PortType.STRING,
                required=True,
                description="S3 destination (s3://bucket/path/)"
            ),
            "pattern": InputPort(
                name="pattern",
                port_type=PortType.STRING,
                required=False,
                default="*",
                description="File pattern to match"
            ),
            "parallel": InputPort(
                name="parallel",
                port_type=PortType.INTEGER,
                required=False,
                default=8,
                description="Number of parallel uploads"
            ),
            "preserve_structure": InputPort(
                name="preserve_structure",
                port_type=PortType.BOOLEAN,
                required=False,
                default=False,
                description="Preserve directory structure"
            )
        }
        self.outputs = {
            "uploaded_urls": OutputPort(
                name="uploaded_urls",
                port_type=PortType.URL_LIST,
                description="List of uploaded S3 URLs"
            ),
            "manifest_file": OutputPort(
                name="manifest_file",
                port_type=PortType.FILE,
                description="Path to manifest file"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        local_directory = Path(inputs["local_directory"])
        s3_destination = inputs["s3_destination"]
        pattern = inputs.get("pattern", "*")
        parallel = inputs.get("parallel", 8)
        preserve_structure = inputs.get("preserve_structure", False)
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "transfer" / "s3_upload.py"),
            str(local_directory),
            s3_destination,
            "--pattern", pattern,
            "--parallel", str(parallel)
        ]
        if preserve_structure:
            cmd.append("--preserve-structure")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"s3_upload failed: {result.stderr}")
        
        # Parse uploaded URLs
        uploaded_urls = []
        manifest_file = local_directory.parent / "uploaded_urls.txt"
        
        if manifest_file.exists():
            from utils.common import parse_manifest
            video_urls, audio_urls = parse_manifest(manifest_file)
            uploaded_urls = video_urls + audio_urls
        
        return {
            "uploaded_urls": uploaded_urls,
            "manifest_file": str(manifest_file) if manifest_file.exists() else None
        }


@register_node(metadata={"category": "storage", "description": "Download files from AWS S3"})
class DownloadS3Node(Node):
    """Download files from AWS S3"""
    
    def _define_ports(self):
        self.inputs = {
            "s3_source": InputPort(
                name="s3_source",
                port_type=PortType.STRING,
                required=True,
                description="S3 source path or input file"
            ),
            "local_destination": InputPort(
                name="local_destination",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Local destination directory"
            ),
            "mode": InputPort(
                name="mode",
                port_type=PortType.STRING,
                required=False,
                default="sync",
                description="Download mode: sync, list, or json"
            ),
            "parallel": InputPort(
                name="parallel",
                port_type=PortType.INTEGER,
                required=False,
                default=10,
                description="Number of parallel downloads"
            )
        }
        self.outputs = {
            "downloaded_directory": OutputPort(
                name="downloaded_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing downloaded files"
            ),
            "downloaded_files": OutputPort(
                name="downloaded_files",
                port_type=PortType.FILE_LIST,
                description="List of downloaded file paths"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        s3_source = inputs["s3_source"]
        local_destination = Path(inputs["local_destination"])
        mode = inputs.get("mode", "sync")
        parallel = inputs.get("parallel", 10)
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "transfer" / "s3_download.py"),
            s3_source,
            str(local_destination),
            "--mode", mode,
            "--parallel", str(parallel)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"s3_download failed: {result.stderr}")
        
        # List downloaded files
        downloaded_files = []
        if local_destination.exists():
            downloaded_files = [str(f) for f in local_destination.rglob("*") if f.is_file()]
        
        return {
            "downloaded_directory": str(local_destination),
            "downloaded_files": sorted(downloaded_files)
        }

