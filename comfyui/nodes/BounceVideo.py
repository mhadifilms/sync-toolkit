"""
ComfyUI node for bouncing videos.
Wraps scripts/video/bounce.sh
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


class BounceVideo:
    """Create bounced versions of videos"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "input_dir": ("STRING", {"default": ""}),  # Legacy support
                "output_dir": ("STRING", {"default": ""}),
                "recursive": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA",)
    RETURN_NAMES = ("output_directory",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, directory_data: dict = None, input_dir: str = "", output_dir: str = "", recursive: bool = False):
        """Run video bouncing"""
        try:
            # Extract directory path from DIRECTORY_DATA or use legacy string input
            if directory_data and not directory_data.get("error"):
                input_path = normalize_path(directory_data.get("path", ""))
            elif input_dir:
                input_path = normalize_path(input_dir)
            else:
                return ({"error": "ERROR: Input directory required"},)
            
            if not input_path.exists() or not input_path.is_dir():
                return ({"error": "ERROR: Input directory not found"},)
            
            # Get bounce.sh script
            script_path = SCRIPT_DIR / "video" / "bounce.sh"
            if not script_path.exists():
                return ("ERROR: bounce.sh script not found",)
            
            # Build command
            cmd = ["bash", str(script_path)]
            if output_dir:
                cmd.extend(["--output", str(normalize_path(output_dir))])
            if recursive:
                cmd.append("--recursive")
            cmd.append(str(input_path))
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return ({"error": f"ERROR: {result.stderr}"},)
            
            # Determine output directory
            if output_dir:
                out_dir = normalize_path(output_dir)
            else:
                out_dir = input_path
            
            # Get output files
            output_files = list(out_dir.glob("*.mov")) + list(out_dir.glob("*.mp4"))
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(out_dir),
                "file_count": len(output_files),
                "files": [ensure_absolute_path(f) for f in output_files],
            }
            
            return (directory_data,)
            
        except Exception as e:
            return ({"error": format_error(e)},)

