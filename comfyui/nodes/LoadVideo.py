"""
ComfyUI node for loading video file(s).
Can load single video or multiple videos from directory/list.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:

# Add scripts directory to path
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error
parse_json_string = _comfyui_utils.parse_json_string


class LoadVideo:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "input_type": (["single_file", "directory", "list"], {"default": "single_file"}),
            },
            "optional": {
                "video_path": ("STRING", {"default": ""}),
                "directory_path": ("STRING", {"default": ""}),
                "video_list": ("STRING", {"default": ""}),  # JSON list of paths
                "pattern": ("STRING", {"default": "*.mov,*.mp4,*.avi,*.mkv"}),
        }
    
    RETURN_TYPES = ("VIDEO_DATA",)
    RETURN_NAMES = ("video_data",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/input"
    
    def run(self, input_type: str, video_path: str = "", directory_path: str = "",
            video_list: str = "", pattern: str = "*.mov,*.mp4,*.avi,*.mkv"):
        """Load video file(s)"""
        try:
            
            if input_type == "single_file":
                    return ({"error": "ERROR: Video path required for single_file mode"},)
                vid_path = normalize_path(video_path)
                if not vid_path.exists():
                video_files = [vid_path]
                
            elif input_type == "directory":
                    return ({"error": "ERROR: Directory path required for directory mode"},)
                dir_path = normalize_path(directory_path)
                if not dir_path.exists() or not dir_path.is_dir():
                
                # Parse pattern
                patterns = [p.strip() for p in pattern.split(",")]
                for pat in patterns:
                video_files = sorted(set(video_files))  # Remove duplicates and sort
                
            else:  # list mode
                if not video_list:
                try:
                    if not isinstance(paths, list):
                    video_files = [normalize_path(p) for p in paths]
                    # Validate all files exist
                    for vf in video_files:
                            return ({"error": f"ERROR: Video file not found: {vf}"},)
                except ValueError as e:
            
            if not video_files:
            
            # Create VIDEO_DATA structure
            video_data = {
                "files": [ensure_absolute_path(vf) for vf in video_files],
                "primary_file": ensure_absolute_path(video_files[0]),
                "count": len(video_files),
            }
            
            return (video_data,)
            
        except Exception as e:

