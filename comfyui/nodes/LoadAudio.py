"""
ComfyUI node for loading audio file(s).
Can load single audio or multiple audio files from directory/list.
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


class LoadAudio:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "input_type": (["single_file", "directory", "list"], {"default": "single_file"}),
            },
            "optional": {
                "audio_path": ("STRING", {"default": ""}),
                "directory_path": ("STRING", {"default": ""}),
                "audio_list": ("STRING", {"default": ""}),  # JSON list of paths
                "pattern": ("STRING", {"default": "*.wav,*.aac,*.mp3,*.m4a"}),
        }
    
    RETURN_TYPES = ("AUDIO_DATA",)
    RETURN_NAMES = ("audio_data",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/input"
    
    def run(self, input_type: str, audio_path: str = "", directory_path: str = "",
            audio_list: str = "", pattern: str = "*.wav,*.aac,*.mp3,*.m4a"):
        """Load audio file(s)"""
        try:
            
            if input_type == "single_file":
                    return ({"error": "ERROR: Audio path required for single_file mode"},)
                aud_path = normalize_path(audio_path)
                if not aud_path.exists():
                audio_files = [aud_path]
                
            elif input_type == "directory":
                    return ({"error": "ERROR: Directory path required for directory mode"},)
                dir_path = normalize_path(directory_path)
                if not dir_path.exists() or not dir_path.is_dir():
                
                # Parse pattern
                patterns = [p.strip() for p in pattern.split(",")]
                for pat in patterns:
                audio_files = sorted(set(audio_files))  # Remove duplicates and sort
                
            else:  # list mode
                if not audio_list:
                try:
                    if not isinstance(paths, list):
                    audio_files = [normalize_path(p) for p in paths]
                    # Validate all files exist
                    for af in audio_files:
                            return ({"error": f"ERROR: Audio file not found: {af}"},)
                except ValueError as e:
            
            if not audio_files:
            
            # Create AUDIO_DATA structure
            audio_data = {
                "files": [ensure_absolute_path(af) for af in audio_files],
                "primary_file": ensure_absolute_path(audio_files[0]),
                "count": len(audio_files),
            }
            
            return (audio_data,)
            
        except Exception as e:

