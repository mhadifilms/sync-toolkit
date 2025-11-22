"""
ComfyUI node for managing credentials.
Stores credentials that can be reused across multiple nodes.
"""
import sys
import os
from pathlib import Path
from typing import Optional

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
# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class Credentials:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "storage_type": (["s3", "supabase"], {"default": "s3"}),
            },
            "optional": {
                "sync_api_key": ("STRING", {"default": "", "password": True}),
                # S3 options
                "use_sso": ("BOOLEAN", {"default": False}),
                "aws_access_key_id": ("STRING", {"default": "", "password": True}),
                "aws_secret_access_key": ("STRING", {"default": "", "password": True}),
                "aws_region": ("STRING", {"default": "us-east-1"}),
                # Supabase options
                "supabase_host": ("STRING", {"default": ""}),
                "supabase_bucket": ("STRING", {"default": ""}),
                "supabase_key": ("STRING", {"default": "", "password": True}),
        }
    
    RETURN_TYPES = ("CREDENTIALS",)
    RETURN_NAMES = ("credentials",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/config"
    
    def run(self, storage_type: str = "s3", sync_api_key: str = "",
            use_sso: bool = False, aws_access_key_id: str = "",
            aws_secret_access_key: str = "", aws_region: str = "us-east-1",
            supabase_host: str = "", supabase_bucket: str = "", supabase_key: str = ""):
        """Create credentials object"""
        try:
            creds = {
                "storage_type": storage_type,
                "sync_api_key": sync_api_key or os.getenv("SYNC_API_KEY", ""),
            }
            
            if storage_type == "s3":
                    # Use SSO/IAM role - don't set access keys, boto3 will use default credential chain
                    creds["use_sso"] = True
                    creds["aws_access_key_id"] = ""
                    creds["aws_secret_access_key"] = ""
                else:
                    creds["aws_access_key_id"] = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID", "")
                    creds["aws_secret_access_key"] = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY", "")
                
                creds["aws_region"] = aws_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            else:  # supabase
                creds["supabase_host"] = supabase_host or os.getenv("SUPABASE_HOST", "")
                creds["supabase_bucket"] = supabase_bucket or os.getenv("SUPABASE_BUCKET", "")
                creds["supabase_key"] = supabase_key or os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", "")
            
            return (creds,)
            
        except Exception as e:

