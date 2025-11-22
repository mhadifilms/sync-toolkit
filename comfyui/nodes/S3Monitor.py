"""
ComfyUI node for monitoring S3 upload progress.
Wraps scripts/monitor/s3_monitor.py
"""
import sys
import re
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
get_s3_client = _comfyui_utils.get_s3_client


class S3Monitor:
    """Monitor S3 upload progress"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "s3_path": ("STRING", {"default": ""}),
                "expected_count": ("INT", {"default": 0, "min": 0}),
            },
            "optional": {
                "credentials": ("CREDENTIALS", {"default": None}),
                "interval": ("INT", {"default": 180, "min": 1}),
                "pattern": ("STRING", {"default": "(_bounced\\.mov|_bounced\\.wav)"}),
            }
        }
    
    RETURN_TYPES = ("INT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("current_count", "status", "is_complete")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/storage"
    
    def run(self, s3_path: str, expected_count: int,
            credentials: dict = None, interval: int = 180,
            pattern: str = "(_bounced\\.mov|_bounced\\.wav)"):
        """Run monitoring (single check)"""
        try:
            # Extract credentials
            creds = credentials or {}
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            
            # Get S3 client
            try:
                s3_client = get_s3_client(aws_region, aws_access_key_id, aws_secret_key)
            except Exception as e:
                return (0, format_error(e), False)
            
            # Parse S3 path
            if not s3_path.startswith('s3://'):
                return (0, "ERROR: S3 path must start with s3://", False)
            
            s3_path_clean = s3_path.replace('s3://', '')
            if not s3_path_clean.endswith('/'):
                s3_path_clean += '/'
            
            parts = s3_path_clean.split('/', 1)
            bucket = parts[0]
            prefix = parts[1] if len(parts) > 1 else ''
            
            # Count files matching pattern
            count = 0
            pattern_re = re.compile(pattern)
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                for obj in page['Contents']:
                    key = obj['Key']
                    if pattern_re.search(key):
                        count += 1
            
            # Determine status
            is_complete = count >= expected_count
            if is_complete:
                status = f"Complete: {count}/{expected_count} files uploaded"
            else:
                status = f"Progress: {count}/{expected_count} files uploaded"
            
            return (count, status, is_complete)
            
        except Exception as e:
            return (0, format_error(e), False)

