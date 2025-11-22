"""
ComfyUI node for organizing outputs into custom folder structures.
Groups files by scene, character, or custom patterns.
"""
import sys
import json
import shutil
from pathlib import Path
from typing import Optional, List

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class OrganizeOutputs:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "output_base_dir": ("STRING", {"default": ""}),
                "organization_mode": (["none", "by_scene", "by_character", "by_metadata", "custom"], {"default": "by_scene"}),
            },
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "groups_json": ("STRING", {"default": ""}),  # From GroupByFace or custom grouping
                "metadata_csv": ("STRING", {"default": ""}),  # CSV with metadata for grouping
                "custom_pattern": ("STRING", {"default": "{scene}/{file}"}),  # Pattern for custom mode
                "copy_mode": (["copy", "move", "symlink"], {"default": "copy"}),
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "INT", "STRING")
    RETURN_NAMES = ("output_directory", "organized_count", "organization_json")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/output"
    
    def run(self, output_base_dir: str, organization_mode: str = "by_scene",
            directory_data: dict = None, groups_json: str = "",
            metadata_csv: str = "", custom_pattern: str = "{scene}/{file}",
            copy_mode: str = "copy"):
        """Organize files into folder structure"""
        try:
                return ({"error": "ERROR: Directory data required"}, 0, "")
            
            input_dir = normalize_path(directory_data.get("path", ""))
            input_files = directory_data.get("files", [])
            
            if not input_dir.exists():
            
            # Get all files if not provided
            if not input_files:
                input_files = [f for f in input_files if f.is_file()]
            
            # Create output base directory
            output_base = normalize_path(output_base_dir) if output_base_dir else input_dir.parent / "organized"
            output_base.mkdir(parents=True, exist_ok=True)
            
            organized_files = []
            organization_map = {}
            
            if organization_mode == "none":
                for file_path in input_files:
                    dst = output_base / src.name
                    
                    if copy_mode == "copy":
                    elif copy_mode == "move":
                    else:  # symlink
                        dst.symlink_to(src)
                    
                    organized_files.append(dst)
                    organization_map[str(dst)] = {"original": str(src), "group": "root"}
            
            elif organization_mode == "by_scene":
                import re
                for file_path in input_files:
                    # Try to extract scene number from filename (e.g., scene_001, Scene_01, etc.)
                    match = re.search(r'(?:scene|Scene|SCENE)[_\s]*(\d+)', src.stem)
                    if match:
                        scene_dir = output_base / f"scene_{scene_num}"
                    else:
                        match = re.search(r'(\d+)', src.stem)
                        scene_num = match.group(1).zfill(4) if match else "unknown"
                        scene_dir = output_base / f"scene_{scene_num}"
                    
                    scene_dir.mkdir(parents=True, exist_ok=True)
                    dst = scene_dir / src.name
                    
                    if copy_mode == "copy":
                    elif copy_mode == "move":
                    else:  # symlink
                        dst.symlink_to(src)
                    
                    organized_files.append(dst)
                    organization_map[str(dst)] = {
                        "original": str(src),
                        "group": f"scene_{scene_num}",
                        "scene_number": scene_num
                    }
            
            elif organization_mode == "by_character":
                if groups_json:
                        groups = json.loads(groups_json)
                        if isinstance(groups, dict):
                            for group_name, files in groups.items():
                                group_dir.mkdir(parents=True, exist_ok=True)
                                
                                for file_path in files:
                                    if src in input_files or str(src) in [str(f) for f in input_files]:
                                        
                                        if copy_mode == "copy":
                                        elif copy_mode == "move":
                                        else:  # symlink
                                            dst.symlink_to(src)
                                        
                                        organized_files.append(dst)
                                        organization_map[str(dst)] = {
                                            "original": str(src),
                                            "group": group_name,
                                            "type": "character"
                                        }
                    except json.JSONDecodeError:
                
                # If no groups_json or parsing failed, fall back to by_scene
                if not organized_files:
            
            elif organization_mode == "by_metadata":
                if metadata_csv:
                    csv_path = normalize_path(metadata_csv)
                    if csv_path.exists():
                            reader = csv.DictReader(f)
                            for row in reader:
                                file_col = None
                                for col in ['file', 'filename', 'path', 'filepath']:
                                        file_col = col
                                        break
                                
                                if file_col:
                                    if src.exists() and (src in input_files or str(src) in [str(f) for f in input_files]):
                                        group_col = None
                                        for col in ['group', 'character', 'scene', 'category', 'folder']:
                                                group_col = col
                                                break
                                        
                                        if group_col:
                                            group_dir = output_base / group_name
                                            group_dir.mkdir(parents=True, exist_ok=True)
                                            dst = group_dir / src.name
                                            
                                            if copy_mode == "copy":
                                            elif copy_mode == "move":
                                            else:  # symlink
                                                dst.symlink_to(src)
                                            
                                            organized_files.append(dst)
                                            organization_map[str(dst)] = {
                                                "original": str(src),
                                                "group": group_name,
                                                "metadata": row
                                            }
            
            elif organization_mode == "custom":
                import re
                for file_path in input_files:
                    # Simple pattern replacement - extract values from filename
                    pattern = custom_pattern
                    # Replace {file} with filename
                    pattern = pattern.replace("{file}", src.name)
                    pattern = pattern.replace("{stem}", src.stem)
                    pattern = pattern.replace("{ext}", src.suffix)
                    
                    # Try to extract common patterns
                    scene_match = re.search(r'(?:scene|Scene)[_\s]*(\d+)', src.stem)
                    if scene_match:
                    
                    # Create directory structure
                    dst = output_base / pattern
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    
                    if copy_mode == "copy":
                    elif copy_mode == "move":
                    else:  # symlink
                        dst.symlink_to(src)
                    
                    organized_files.append(dst)
                    organization_map[str(dst)] = {
                        "original": str(src),
                        "pattern": pattern
                    }
            
            # Return DIRECTORY_DATA structure
            directory_data_out = {
                "path": ensure_absolute_path(output_base),
                "file_count": len(organized_files),
                "files": [ensure_absolute_path(f) for f in organized_files],
            }
            
            organization_json = json.dumps(organization_map, indent=2)
            
            return (
                directory_data_out,
                len(organized_files),
                organization_json
            )
            
        except Exception as e:

