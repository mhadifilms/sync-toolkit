#!/usr/bin/env python3
"""
Input nodes for loading data into workflows.
"""
from pathlib import Path
from typing import Dict, Any, List

from nodes.base import Node, InputPort, OutputPort, PortType, register_node


@register_node(metadata={"category": "input", "description": "Load video file(s) from local path"})
class LoadVideoNode(Node):
    """Load video file(s) from local path"""
    
    def _define_ports(self):
        self.inputs = {
            "video_path": InputPort(
                name="video_path",
                port_type=PortType.FILE,
                required=True,
                description="Path to video file or directory containing videos"
            )
        }
        self.outputs = {
            "video_path": OutputPort(
                name="video_path",
                port_type=PortType.FILE,
                description="Path to video file"
            ),
            "video_list": OutputPort(
                name="video_list",
                port_type=PortType.FILE_LIST,
                description="List of video file paths"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        video_path = Path(inputs["video_path"])
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video path does not exist: {video_path}")
        
        if video_path.is_file():
            return {
                "video_path": str(video_path),
                "video_list": [str(video_path)]
            }
        elif video_path.is_dir():
            # Find video files in directory
            video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.mxf', '.m4v'}
            video_files = [
                str(f) for f in video_path.iterdir()
                if f.is_file() and f.suffix.lower() in video_extensions
            ]
            return {
                "video_path": str(video_path),
                "video_list": sorted(video_files)
            }
        else:
            raise ValueError(f"Invalid video path: {video_path}")


@register_node(metadata={"category": "input", "description": "Load audio file(s) from local path"})
class LoadAudioNode(Node):
    """Load audio file(s) from local path"""
    
    def _define_ports(self):
        self.inputs = {
            "audio_path": InputPort(
                name="audio_path",
                port_type=PortType.FILE,
                required=True,
                description="Path to audio file or directory containing audio files"
            )
        }
        self.outputs = {
            "audio_path": OutputPort(
                name="audio_path",
                port_type=PortType.FILE,
                description="Path to audio file"
            ),
            "audio_list": OutputPort(
                name="audio_list",
                port_type=PortType.FILE_LIST,
                description="List of audio file paths"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = Path(inputs["audio_path"])
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio path does not exist: {audio_path}")
        
        if audio_path.is_file():
            return {
                "audio_path": str(audio_path),
                "audio_list": [str(audio_path)]
            }
        elif audio_path.is_dir():
            # Find audio files in directory
            audio_extensions = {'.wav', '.aiff', '.mp3', '.m4a', '.flac', '.ogg'}
            audio_files = [
                str(f) for f in audio_path.iterdir()
                if f.is_file() and f.suffix.lower() in audio_extensions
            ]
            return {
                "audio_path": str(audio_path),
                "audio_list": sorted(audio_files)
            }
        else:
            raise ValueError(f"Invalid audio path: {audio_path}")


@register_node(metadata={"category": "input", "description": "Load CSV file"})
class LoadCSVNode(Node):
    """Load CSV file"""
    
    def _define_ports(self):
        self.inputs = {
            "csv_path": InputPort(
                name="csv_path",
                port_type=PortType.FILE,
                required=True,
                description="Path to CSV file"
            )
        }
        self.outputs = {
            "csv_path": OutputPort(
                name="csv_path",
                port_type=PortType.FILE,
                description="Path to CSV file"
            ),
            "csv_data": OutputPort(
                name="csv_data",
                port_type=PortType.CSV_DATA,
                description="CSV data as dictionary"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import csv
        
        csv_path = Path(inputs["csv_path"])
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file does not exist: {csv_path}")
        
        # Read CSV file
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        
        return {
            "csv_path": str(csv_path),
            "csv_data": rows
        }


@register_node(metadata={"category": "input", "description": "Load manifest file"})
class LoadManifestNode(Node):
    """Load manifest file (uploaded_urls.txt format)"""
    
    def _define_ports(self):
        self.inputs = {
            "manifest_path": InputPort(
                name="manifest_path",
                port_type=PortType.FILE,
                required=True,
                description="Path to manifest file"
            )
        }
        self.outputs = {
            "manifest_path": OutputPort(
                name="manifest_path",
                port_type=PortType.FILE,
                description="Path to manifest file"
            ),
            "manifest": OutputPort(
                name="manifest",
                port_type=PortType.MANIFEST,
                description="Parsed manifest data"
            ),
            "video_urls": OutputPort(
                name="video_urls",
                port_type=PortType.URL_LIST,
                description="List of video URLs"
            ),
            "audio_urls": OutputPort(
                name="audio_urls",
                port_type=PortType.URL_LIST,
                description="List of audio URLs"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        # Import parse_manifest from utils
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(SCRIPT_DIR))
        from utils.common import parse_manifest
        
        manifest_path = Path(inputs["manifest_path"])
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest file does not exist: {manifest_path}")
        
        video_urls, audio_urls = parse_manifest(manifest_path)
        
        manifest_data = {
            "videos": video_urls,
            "audios": audio_urls
        }
        
        return {
            "manifest_path": str(manifest_path),
            "manifest": manifest_data,
            "video_urls": video_urls,
            "audio_urls": audio_urls
        }


@register_node(metadata={"category": "input", "description": "Load directory of files"})
class LoadDirectoryNode(Node):
    """Load directory of files"""
    
    def _define_ports(self):
        self.inputs = {
            "directory": InputPort(
                name="directory",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Path to directory"
            ),
            "pattern": InputPort(
                name="pattern",
                port_type=PortType.STRING,
                required=False,
                default="*",
                description="File pattern to match"
            )
        }
        self.outputs = {
            "directory": OutputPort(
                name="directory",
                port_type=PortType.DIRECTORY,
                description="Path to directory"
            ),
            "file_list": OutputPort(
                name="file_list",
                port_type=PortType.FILE_LIST,
                description="List of file paths in directory"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        directory = Path(inputs["directory"])
        pattern = inputs.get("pattern", "*")
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        # Find files matching pattern
        files = [str(f) for f in directory.glob(pattern) if f.is_file()]
        
        return {
            "directory": str(directory),
            "file_list": sorted(files)
        }

