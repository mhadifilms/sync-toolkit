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
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "video_data": ("VIDEO_DATA", {"default": None}),
                "video_directory": ("STRING", {"default": ""}),  # Legacy support
                "force": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA",)
    RETURN_NAMES = ("output_directory",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, directory_data: dict = None, video_data: dict = None,
            video_directory: str = "", force: bool = False):
        """Run audio extraction"""
        try:
            if directory_data and not directory_data.get("error"):
            elif video_data and not video_data.get("error"):
                first_video = normalize_path(video_data.get("primary_file", ""))
                video_dir = first_video.parent
            elif video_directory:

            else:
            
            if not video_dir.exists() or not video_dir.is_dir():
            
            # Get extract_audio.sh script
            script_path = SCRIPT_DIR / "video" / "extract_audio.sh"
            if not script_path.exists():
            
            # Build command
            cmd = ["bash", str(script_path)]
            if force:
            cmd.append(str(video_dir))
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(video_dir)
            )
            
            if result.returncode != 0:
            
            # Get extracted audio files
            audio_files = list(video_dir.glob("*.wav")) + list(video_dir.glob("*.aac"))
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(video_dir),
                "file_count": len(audio_files),
                "files": [ensure_absolute_path(f) for f in audio_files],
            }
            
            return (directory_data,)
            
        except Exception as e:

