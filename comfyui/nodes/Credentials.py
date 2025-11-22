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
    """Manage credentials for sync-toolkit nodes"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "sync_api_key": ("STRING", {"default": "", "password": True}),
                "aws_access_key_id": ("STRING", {"default": "", "password": True}),
                "aws_secret_access_key": ("STRING", {"default": "", "password": True}),
                "aws_region": ("STRING", {"default": "us-east-1"}),
                "supabase_host": ("STRING", {"default": ""}),
                "supabase_bucket": ("STRING", {"default": ""}),
                "supabase_key": ("STRING", {"default": "", "password": True}),
            }
        }
    
    RETURN_TYPES = ("CREDENTIALS",)
    RETURN_NAMES = ("credentials",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/config"
    
    def run(self, sync_api_key: str = "", aws_access_key_id: str = "",
            aws_secret_access_key: str = "", aws_region: str = "us-east-1",
            supabase_host: str = "", supabase_bucket: str = "", supabase_key: str = ""):
        """Create credentials object"""
        try:
            # Use provided credentials or fall back to environment variables
            creds = {
                "sync_api_key": sync_api_key or os.getenv("SYNC_API_KEY", ""),
                "aws_access_key_id": aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "aws_region": aws_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                "supabase_host": supabase_host or os.getenv("SUPABASE_HOST", ""),
                "supabase_bucket": supabase_bucket or os.getenv("SUPABASE_BUCKET", ""),
                "supabase_key": supabase_key or os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", ""),
            }
            
            return (creds,)
            
        except Exception as e:
            return ({"error": format_error(e)},)

