"""
ComfyUI node for merging multiple directories into one.
Combines files from multiple DIRECTORY_DATA inputs.
"""
import sys
import shutil
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


class MergeDirectories:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "output_dir": ("STRING", {"default": ""}),
            },
            "optional": {
                "directory_data_1": ("DIRECTORY_DATA", {"default": None}),
                "directory_data_2": ("DIRECTORY_DATA", {"default": None}),
                "directory_data_3": ("DIRECTORY_DATA", {"default": None}),
                "directory_data_4": ("DIRECTORY_DATA", {"default": None}),
                "copy_files": ("BOOLEAN", {"default": True}),  # True = copy, False = move
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA",)
    RETURN_NAMES = ("output_directory",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/utility"
    
    def run(self, output_dir: str, directory_data_1: dict = None,
            directory_data_2: dict = None, directory_data_3: dict = None,
            directory_data_4: dict = None, copy_files: bool = True):
        """Merge directories"""
        try:
                return ({"error": "ERROR: Output directory required"},)
            
            output_path = normalize_path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Collect all directory data inputs
            directories = []
            for dd in [directory_data_1, directory_data_2, directory_data_3, directory_data_4]:
                    directories.append(dd)
            
            if not directories:
            
            merged_files = []
            file_counter = {}
            
            # Merge files from all directories
            for dd in directories:
                if not source_dir.exists():
                
                # Use files from directory_data if available, otherwise scan
                if dd.get("files"):
                else:
                
                for source_file in source_files:
                        continue
                    
                    # Handle name conflicts
                    dest_file = output_path / source_file.name
                    if dest_file.exists():
                        suffix = source_file.suffix
                        counter = file_counter.get(source_file.name, 0) + 1
                        file_counter[source_file.name] = counter
                        dest_file = output_path / f"{stem}_{counter}{suffix}"
                    
                    try:
                            shutil.copy2(source_file, dest_file)
                        else:
                        merged_files.append(dest_file)
                    except Exception as e:
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(output_path),
                "file_count": len(merged_files),
                "files": [ensure_absolute_path(f) for f in merged_files],
            }
            
            return (directory_data,)
            
        except Exception as e:

