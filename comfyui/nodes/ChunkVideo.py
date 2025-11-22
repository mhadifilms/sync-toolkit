"""
ComfyUI node for chunking video/audio from cuts file.
Wraps scripts/video/chunk.sh
"""
import sys
import subprocess
from pathlib import Path

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:

# Add scripts directory to path
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:

# Import utils - use absolute import from current directory
# Add current directory (comfyui) to path FIRST for utils import
COMFYUI_DIR = Path(__file__).parent.parent.resolve()
if str(COMFYUI_DIR) not in sys.path:

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class ChunkVideo:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "cuts_file": ("STRING", {"default": ""}),
            },
            "optional": {
                "video_data": ("VIDEO_DATA", {"default": None}),
                "audio_data": ("AUDIO_DATA", {"default": None}),
                "video_path": ("STRING", {"default": ""}),  # Legacy support
                "audio_path": ("STRING", {"default": ""}),  # Legacy support
                "output_dir": ("STRING", {"default": ""}),
                "s3_dest": ("STRING", {"default": ""}),
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "INT")
    RETURN_NAMES = ("output_directory", "chunk_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, cuts_file: str, video_data: dict = None, audio_data: dict = None,
            video_path: str = "", audio_path: str = "", output_dir: str = "", s3_dest: str = ""):
        """Run video chunking"""
        try:
            if video_data and not video_data.get("error"):
            elif video_path:
            else:
            
            # Extract audio path from AUDIO_DATA or use legacy string input
            audio_in = None
            if audio_data and not audio_data.get("error"):
            elif audio_path:
            
            cuts_in = normalize_path(cuts_file)
            
            # Set output directory
            if output_dir:

            else:
            out_dir.mkdir(parents=True, exist_ok=True)
            
            if not video_in.exists():
            if not cuts_in.exists():
            
            # Get chunk.sh script
            script_path = SCRIPT_DIR / "video" / "chunk.sh"
            if not script_path.exists():
            
            # Build command
            cmd = ["bash", str(script_path)]
            cmd.append(str(video_in))
            
            if audio_in and audio_in.exists():
            else:
            
            cmd.append(str(cuts_in))
            cmd.append(str(out_dir))
            
            if s3_dest:
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
            
            # Count chunks
            chunks = list(out_dir.glob("*.mov")) + list(out_dir.glob("*.wav"))
            chunk_count = len(chunks)
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(out_dir),
                "file_count": chunk_count,
                "files": [ensure_absolute_path(f) for f in chunks],
            }
            
            return (directory_data, chunk_count)
            
        except Exception as e:

