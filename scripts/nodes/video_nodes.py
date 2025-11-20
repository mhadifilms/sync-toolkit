#!/usr/bin/env python3
"""
Video processing nodes.

Wraps video processing scripts as nodes.
"""
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from nodes.base import Node, InputPort, OutputPort, PortType, register_node


@register_node(metadata={"category": "video", "description": "Detect scene boundaries in video"})
class DetectScenesNode(Node):
    """Detect scene boundaries and split video/audio"""
    
    def _define_ports(self):
        self.inputs = {
            "video_path": InputPort(
                name="video_path",
                port_type=PortType.FILE,
                required=True,
                description="Input video file"
            ),
            "audio_path": InputPort(
                name="audio_path",
                port_type=PortType.FILE,
                required=False,
                description="Input audio file (optional)"
            ),
            "output_dir": InputPort(
                name="output_dir",
                port_type=PortType.DIRECTORY,
                required=False,
                description="Output directory for scenes"
            ),
            "threshold": InputPort(
                name="threshold",
                port_type=PortType.FLOAT,
                required=False,
                default=22.0,
                description="Scene detection threshold"
            ),
            "min_frames": InputPort(
                name="min_frames",
                port_type=PortType.INTEGER,
                required=False,
                default=8,
                description="Minimum scene length in frames"
            )
        }
        self.outputs = {
            "output_directory": OutputPort(
                name="output_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing detected scenes"
            ),
            "scene_list": OutputPort(
                name="scene_list",
                port_type=PortType.SCENE_LIST,
                description="List of detected scenes with timecodes"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        # Import detect_scenes functionality
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(SCRIPT_DIR))
        
        # Call detect_scenes.py main function
        video_path = Path(inputs["video_path"])
        audio_path = inputs.get("audio_path")
        output_dir = inputs.get("output_dir")
        threshold = inputs.get("threshold", 22.0)
        min_frames = inputs.get("min_frames", 8)
        
        # Import and call the detect_scenes module
        from video.detect_scenes import main as detect_scenes_main
        
        # Set up arguments for detect_scenes
        import argparse
        args = argparse.Namespace()
        args.video = str(video_path)
        args.audio = str(audio_path) if audio_path else None
        args.output = str(output_dir) if output_dir else None
        args.threshold = threshold
        args.min_frames = min_frames
        
        # Temporarily override sys.argv
        old_argv = sys.argv
        try:
            sys.argv = ['detect_scenes.py']
            # Note: detect_scenes.py uses interactive prompts, so we need to
            # modify it or call internal functions directly
            # For now, we'll use subprocess as a workaround
            cmd = [
                sys.executable,
                str(SCRIPT_DIR / "video" / "detect_scenes.py"),
                "--video", str(video_path)
            ]
            if audio_path:
                cmd.extend(["--audio", str(audio_path)])
            if output_dir:
                cmd.extend(["--output", str(output_dir)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"detect_scenes failed: {result.stderr}")
            
            # Parse output directory (detect_scenes creates Scenes directory)
            if output_dir:
                output_directory = Path(output_dir)
            else:
                output_directory = video_path.parent / "Scenes"
            
            # Read scene list if available
            scene_list = []
            scene_file = output_directory / "scenes.json"
            if scene_file.exists():
                import json
                with open(scene_file, 'r') as f:
                    scene_list = json.load(f)
            
            return {
                "output_directory": str(output_directory),
                "scene_list": scene_list
            }
        finally:
            sys.argv = old_argv


@register_node(metadata={"category": "video", "description": "Create video shots from CSV spotting data"})
class CreateShotsNode(Node):
    """Create video shots from CSV spotting data"""
    
    def _define_ports(self):
        self.inputs = {
            "video_path": InputPort(
                name="video_path",
                port_type=PortType.FILE,
                required=True,
                description="Input video file"
            ),
            "csv_path": InputPort(
                name="csv_path",
                port_type=PortType.FILE,
                required=True,
                description="CSV file with spotting data"
            ),
            "output_dir": InputPort(
                name="output_dir",
                port_type=PortType.DIRECTORY,
                required=False,
                description="Output directory for shots"
            )
        }
        self.outputs = {
            "shots_directory": OutputPort(
                name="shots_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing created shots"
            ),
            "shots_manifest": OutputPort(
                name="shots_manifest",
                port_type=PortType.FILE_LIST,
                description="List of created shot files"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(SCRIPT_DIR))
        
        from video.create_shots import main as create_shots_main
        
        video_path = Path(inputs["video_path"])
        csv_path = Path(inputs["csv_path"])
        output_dir = inputs.get("output_dir")
        
        # Call create_shots via subprocess
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "video" / "create_shots.py"),
            "--video", str(video_path),
            "--csv", str(csv_path)
        ]
        if output_dir:
            cmd.extend(["--output", str(output_dir)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"create_shots failed: {result.stderr}")
        
        # Determine output directory
        if output_dir:
            shots_directory = Path(output_dir)
        else:
            shots_directory = video_path.parent / "Shots"
        
        # List shot files
        shots_manifest = [str(f) for f in shots_directory.glob("*.mov") if f.is_file()]
        
        return {
            "shots_directory": str(shots_directory),
            "shots_manifest": sorted(shots_manifest)
        }


@register_node(metadata={"category": "video", "description": "Group video clips by detected faces"})
class GroupByFaceNode(Node):
    """Group video clips by detected faces"""
    
    def _define_ports(self):
        self.inputs = {
            "clips_directory": InputPort(
                name="clips_directory",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Directory containing video clips"
            ),
            "output": InputPort(
                name="output",
                port_type=PortType.FILE,
                required=False,
                default="face_groups.json",
                description="Output JSON file for groups"
            ),
            "organize": InputPort(
                name="organize",
                port_type=PortType.BOOLEAN,
                required=False,
                default=False,
                description="Organize clips into folders after grouping"
            ),
            "organize_output": InputPort(
                name="organize_output",
                port_type=PortType.DIRECTORY,
                required=False,
                description="Output directory for organized clips"
            ),
            "eps": InputPort(
                name="eps",
                port_type=PortType.FLOAT,
                required=False,
                default=0.35,
                description="DBSCAN eps parameter"
            ),
            "min_samples": InputPort(
                name="min_samples",
                port_type=PortType.INTEGER,
                required=False,
                default=2,
                description="DBSCAN min_samples parameter"
            ),
            "num_frames": InputPort(
                name="num_frames",
                port_type=PortType.INTEGER,
                required=False,
                default=10,
                description="Number of frames to sample per video"
            )
        }
        self.outputs = {
            "groups_json": OutputPort(
                name="groups_json",
                port_type=PortType.JSON_DATA,
                description="JSON data with face groups"
            ),
            "organized_directory": OutputPort(
                name="organized_directory",
                port_type=PortType.DIRECTORY,
                description="Directory with organized clips (if organize=True)"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        sys.path.insert(0, str(SCRIPT_DIR))
        
        clips_directory = Path(inputs["clips_directory"])
        output_file = inputs.get("output", "face_groups.json")
        organize = inputs.get("organize", False)
        organize_output = inputs.get("organize_output")
        eps = inputs.get("eps", 0.35)
        min_samples = inputs.get("min_samples", 2)
        num_frames = inputs.get("num_frames", 10)
        
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "video" / "group_by_face.py"),
            "--input-dir", str(clips_directory),
            "--output", str(output_file),
            "--eps", str(eps),
            "--min-samples", str(min_samples),
            "--num-frames", str(num_frames)
        ]
        
        if organize:
            cmd.append("--organize")
            if organize_output:
                cmd.extend(["--organize-output", str(organize_output)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"group_by_face failed: {result.stderr}")
        
        # Load groups JSON
        import json
        groups_json = {}
        output_path = Path(output_file)
        if output_path.exists():
            with open(output_path, 'r') as f:
                groups_json = json.load(f)
        
        organized_directory = None
        if organize and organize_output:
            organized_directory = str(organize_output)
        elif organize:
            organized_directory = str(clips_directory.parent / "organized")
        
        return {
            "groups_json": groups_json,
            "organized_directory": organized_directory
        }


@register_node(metadata={"category": "video", "description": "Extract audio from videos"})
class ExtractAudioNode(Node):
    """Extract audio from videos"""
    
    def _define_ports(self):
        self.inputs = {
            "video_directory": InputPort(
                name="video_directory",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Directory containing video files"
            )
        }
        self.outputs = {
            "audio_directory": OutputPort(
                name="audio_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing extracted audio files"
            ),
            "audio_list": OutputPort(
                name="audio_list",
                port_type=PortType.FILE_LIST,
                description="List of extracted audio files"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        video_directory = Path(inputs["video_directory"])
        
        # Call extract_audio.sh
        script_path = SCRIPT_DIR / "video" / "extract_audio.sh"
        cmd = ["bash", str(script_path), str(video_directory)]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"extract_audio failed: {result.stderr}")
        
        # Audio files are created in the same directory
        audio_directory = video_directory
        audio_list = [str(f) for f in audio_directory.glob("*.wav") if f.is_file()]
        
        return {
            "audio_directory": str(audio_directory),
            "audio_list": sorted(audio_list)
        }


@register_node(metadata={"category": "video", "description": "Create bounced versions of videos"})
class BounceVideoNode(Node):
    """Create bounced versions of videos"""
    
    def _define_ports(self):
        self.inputs = {
            "video_directory": InputPort(
                name="video_directory",
                port_type=PortType.DIRECTORY,
                required=True,
                description="Directory containing video files"
            ),
            "output_dir": InputPort(
                name="output_dir",
                port_type=PortType.DIRECTORY,
                required=False,
                description="Output directory for bounced videos"
            )
        }
        self.outputs = {
            "bounced_directory": OutputPort(
                name="bounced_directory",
                port_type=PortType.DIRECTORY,
                description="Directory containing bounced videos"
            ),
            "bounced_list": OutputPort(
                name="bounced_list",
                port_type=PortType.FILE_LIST,
                description="List of bounced video files"
            )
        }
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import sys
        from pathlib import Path
        
        SCRIPT_DIR = Path(__file__).parent.parent.parent.resolve()
        
        video_directory = Path(inputs["video_directory"])
        output_dir = inputs.get("output_dir")
        
        # Call bounce.sh
        script_path = SCRIPT_DIR / "video" / "bounce.sh"
        cmd = ["bash", str(script_path), str(video_directory)]
        if output_dir:
            cmd.extend(["--output", str(output_dir)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"bounce failed: {result.stderr}")
        
        # Determine output directory
        if output_dir:
            bounced_directory = Path(output_dir)
        else:
            bounced_directory = video_directory
        
        # Find bounced files (typically have _bounced suffix)
        bounced_list = [
            str(f) for f in bounced_directory.glob("*_bounced.mov")
            if f.is_file()
        ]
        
        return {
            "bounced_directory": str(bounced_directory),
            "bounced_list": sorted(bounced_list)
        }

