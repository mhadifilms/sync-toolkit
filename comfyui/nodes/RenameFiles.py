"""
ComfyUI node for renaming files sequentially.
Wraps scripts/utils/rename.sh
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


class RenameFiles:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {},
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "directory": ("STRING", {"default": ""}),  # Legacy support
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "INT")
    RETURN_NAMES = ("output_directory", "renamed_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/utility"
    
    def run(self, directory_data: dict = None, directory: str = ""):
        try:
            if directory_data and not directory_data.get("error"):
            elif directory:

            else:
            
            if not dir_path.exists() or not dir_path.is_dir():
            
            # Get rename.sh script
            script_path = SCRIPT_DIR / "utils" / "rename.sh"
            if not script_path.exists():
            
            # Count files before renaming
            files_before = list(dir_path.glob("*"))
            files_before = [f for f in files_before if f.is_file() and not f.name.startswith('.')]
            
            # Build command
            cmd = ["bash", str(script_path), str(dir_path)]
            
            # Run script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
            
            # Count files after renaming
            files_after = list(dir_path.glob("*"))
            files_after = [f for f in files_after if f.is_file() and not f.name.startswith('.')]
            
            # Return count (should be same, but verify)
            renamed_count = len(files_after)
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(dir_path),
                "file_count": renamed_count,
                "files": [ensure_absolute_path(f) for f in files_after],
            }
            
            return (directory_data, renamed_count)
            
        except Exception as e:

