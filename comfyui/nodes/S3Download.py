"""
ComfyUI node for downloading from S3.
Wraps scripts/transfer/s3_download.py
"""
import sys
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
get_s3_client = _comfyui_utils.get_s3_client


class S3Download:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "source": ("STRING", {"default": ""}),
                "local_dest": ("STRING", {"default": ""}),
                "mode": (["sync", "list", "json"], {"default": "sync"}),
            },
            "optional": {
                "credentials": ("CREDENTIALS", {"default": None}),
                "parallel": ("INT", {"default": 10, "min": 1}),
                "suffix": ("STRING", {"default": "v1"}),
                "name": ("STRING", {"default": ""}),
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "INT")
    RETURN_NAMES = ("output_directory", "downloaded_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/storage"
    
    def run(self, source: str, local_dest: str, mode: str,
            credentials: dict = None, parallel: int = 10,
            suffix: str = "v1", name: str = ""):
        """Run download"""
        try:
            creds = credentials or {}
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            
            # Get S3 client
            try:
            except Exception as e:
            
            local_dest_path = normalize_path(local_dest)
            local_dest_path.mkdir(parents=True, exist_ok=True)
            
            from transfer.s3_download import (
                sync_directory, download_from_list, download_from_json
            )
            
            successful = 0
            
            if mode == "sync":
            elif mode == "list":
                if not source_file.exists():
                successful = download_from_list(s3_client, source_file, local_dest_path, suffix, False)
            elif mode == "json":
                if not source_file.exists():
                # For JSON mode, we need S3 config - use from environment or defaults
                successful = download_from_json(s3_client, source_file, local_dest_path, name, False)
            
            # Get downloaded files
            downloaded_files = list(local_dest_path.glob("*"))
            downloaded_files = [f for f in downloaded_files if f.is_file()]
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(local_dest_path),
                "file_count": len(downloaded_files),
                "files": [ensure_absolute_path(f) for f in downloaded_files],
            }
            
            return (directory_data, successful)
            
        except Exception as e:

