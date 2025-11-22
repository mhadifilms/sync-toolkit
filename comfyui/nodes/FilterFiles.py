"""
ComfyUI node for filtering files by pattern from a directory.
Filters DIRECTORY_DATA to include only matching files.
"""
import sys
import fnmatch
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


class FilterFiles:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "pattern": ("STRING", {"default": "*.mov"}),
            },
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "directory": ("STRING", {"default": ""}),  # Legacy support
                "include_subdirs": ("BOOLEAN", {"default": False}),
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA",)
    RETURN_NAMES = ("output_directory",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/utility"
    
    def run(self, pattern: str, directory_data: dict = None,
            directory: str = "", include_subdirs: bool = False):
        """Filter files by pattern"""
        try:
            if directory_data and not directory_data.get("error"):
                # Use files from directory_data if available
                if directory_data.get("files"):
                else:
            elif directory:
                all_files = []
            else:
            
            if not dir_path.exists() or not dir_path.is_dir():
            
            # If files not provided, scan directory
            if not all_files:
                    all_files = list(dir_path.rglob("*"))
                else:
                all_files = [f for f in all_files if f.is_file()]
            
            # Filter files by pattern
            filtered_files = []
            for file_path in all_files:
                    filtered_files.append(file_path)
            
            # Return DIRECTORY_DATA structure (files stay in original location)
            directory_data = {
                "path": ensure_absolute_path(dir_path),
                "file_count": len(filtered_files),
                "files": [ensure_absolute_path(f) for f in filtered_files],
            }
            
            return (directory_data,)
            
        except Exception as e:

