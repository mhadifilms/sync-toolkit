"""
ComfyUI node for grouping video clips by detected faces.
Wraps scripts/video/group_by_face.py
"""
import sys
import json
from pathlib import Path

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:
    sys.path.insert(0, str(COMFYUI_DIR))

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add scripts directory to path
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import utils - use absolute import from current directory
# Add current directory (comfyui) to path FIRST for utils import
COMFYUI_DIR = Path(__file__).parent.parent.resolve()
if str(COMFYUI_DIR) not in sys.path:
    sys.path.insert(0, str(COMFYUI_DIR))

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class GroupByFace:
    """Group video clips by detected faces and optionally organize them"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_dir": ("STRING", {"default": ""}),
            },
            "optional": {
                "output_json": ("STRING", {"default": ""}),
                "eps": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
                "min_samples": ("INT", {"default": 2, "min": 1}),
                "organize": ("BOOLEAN", {"default": False}),
                "organize_output": ("STRING", {"default": ""}),
                "move": ("BOOLEAN", {"default": False}),
                "symlink": ("BOOLEAN", {"default": False}),
                "num_frames": ("INT", {"default": 10, "min": 1}),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("groups_json", "group_count", "output_directory")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, input_dir: str, output_json: str = "", eps: float = 0.35,
            min_samples: int = 2, organize: bool = False, organize_output: str = "",
            move: bool = False, symlink: bool = False, num_frames: int = 10):
        """Run face grouping"""
        try:
            from video.group_by_face import (
                group_clips_by_face_clustering, organize_clips
            )
            
            input_path = normalize_path(input_dir)
            if not input_path.exists() or not input_path.is_dir():
                return ("ERROR: Input directory not found", 0, "")
            
            # Get video clips
            video_files = list(input_path.glob("*.mov")) + list(input_path.glob("*.mp4"))
            if not video_files:
                return ("ERROR: No video files found in input directory", 0, "")
            
            # Group clips using the actual function signature
            clip_paths = [str(f) for f in video_files]
            groups = group_clips_by_face_clustering(
                clip_paths, 
                eps=eps, 
                min_samples=min_samples, 
                num_frames=num_frames
            )
            
            # Filter out 'no_face' group for count
            face_groups = {k: v for k, v in groups.items() if k != 'no_face'}
            group_count = len(face_groups)
            
            # Convert groups to JSON format
            groups_data = {}
            for group_id, clips in groups.items():
                groups_data[group_id] = clips
            
            # Save JSON
            if output_json:
                json_path = normalize_path(output_json)
            else:
                json_path = input_path / "face_groups.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w') as f:
                json.dump(groups_data, f, indent=2)
            
            groups_json_str = json.dumps(groups_data)
            
            # Organize if requested
            output_directory = str(input_path)
            if organize:
                if organize_output:
                    org_output = normalize_path(organize_output)
                else:
                    org_output = input_path / "organized"
                
                # organize_clips expects copy_files (not move) and create_symlinks
                organize_clips(
                    groups, 
                    str(org_output), 
                    copy_files=not move and not symlink,
                    create_symlinks=symlink
                )
                output_directory = ensure_absolute_path(org_output)
            
            return (groups_json_str, group_count, output_directory)
            
        except Exception as e:
            return (format_error(e), 0, "")

