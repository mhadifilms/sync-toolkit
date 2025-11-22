"""
ComfyUI node for extracting audio from videos.
Wraps scripts/video/extract_audio.sh
"""
import sys
import subprocess
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


class ExtractAudio:
    """Extract audio from videos in a directory"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_directory": ("STRING", {"default": ""}),
            },
            "optional": {
                "force": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_directory",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, video_directory: str, force: bool = False):
        """Run audio extraction"""
        try:
            video_dir = normalize_path(video_directory)
            if not video_dir.exists() or not video_dir.is_dir():
                return ("ERROR: Video directory not found",)
            
            # Get extract_audio.sh script
            script_path = SCRIPT_DIR / "video" / "extract_audio.sh"
            if not script_path.exists():
                return ("ERROR: extract_audio.sh script not found",)
            
            # Build command
            cmd = ["bash", str(script_path)]
            if force:
                cmd.append("--force")
            cmd.append(str(video_dir))
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(video_dir)
            )
            
            if result.returncode != 0:
                return (f"ERROR: {result.stderr}",)
            
            return (ensure_absolute_path(video_dir),)
            
        except Exception as e:
            return (format_error(e),)

