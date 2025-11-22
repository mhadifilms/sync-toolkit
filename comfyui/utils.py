"""
Shared utilities for ComfyUI sync-toolkit nodes.

Handles SSO-based credential loading, path normalization, and error handling.
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import json

# Add scripts directory to path to import sync-toolkit utilities
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from utils.common import normalize_path as _normalize_path
except ImportError:
    # Fallback if utils.common not available
    def _normalize_path(path):
        return Path(path).expanduser().resolve()


def normalize_path(path: str) -> Path:
    """Normalize a path for ComfyUI (handles strings from nodes)"""
    if not path:
        raise ValueError("Path cannot be empty")
    return _normalize_path(path)


def get_aws_credentials(
    region: str = "us-east-1",
    access_key_id: Optional[str] = None,
    secret_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get AWS credentials using SSO/default chain if not provided.
    
    Returns dict with: region, access_key_id, secret_key
    Uses boto3 default credential chain if keys not provided.
    """
    import boto3
    
    creds = {
        "region": region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    }
    
    # If credentials provided, use them
    if access_key_id and secret_key:
        creds["access_key_id"] = access_key_id
        creds["secret_key"] = secret_key
        return creds
    
    # Otherwise, use boto3 default credential chain (SSO/IAM/env vars)
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            creds["access_key_id"] = credentials.access_key
            creds["secret_key"] = credentials.secret_key
            creds["region"] = session.region_name or creds["region"]
        else:
            # Will use default chain when creating client
            creds["access_key_id"] = None
            creds["secret_key"] = None
    except Exception:
        # Fall back to None - will use default chain
        creds["access_key_id"] = None
        creds["secret_key"] = None
    
    return creds


def get_s3_client(
    region: str = "us-east-1",
    access_key_id: Optional[str] = None,
    secret_key: Optional[str] = None
):
    """Get S3 client using SSO/default chain if credentials not provided"""
    import boto3
    
    creds = get_aws_credentials(region, access_key_id, secret_key)
    
    if creds["access_key_id"] and creds["secret_key"]:
        return boto3.client(
            's3',
            region_name=creds["region"],
            aws_access_key_id=creds["access_key_id"],
            aws_secret_access_key=creds["secret_key"]
        )
    
    # Use default credential chain (SSO/IAM/env vars)
    return boto3.client('s3', region_name=creds["region"])


def get_supabase_credentials(
    host: Optional[str] = None,
    bucket: Optional[str] = None,
    key: Optional[str] = None
) -> Dict[str, str]:
    """
    Get Supabase credentials from inputs or environment variables.
    
    Returns dict with: host, bucket, key
    """
    return {
        "host": host or os.getenv("SUPABASE_HOST", ""),
        "bucket": bucket or os.getenv("SUPABASE_BUCKET", ""),
        "key": key or os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE", ""),
    }


def get_sync_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Get Sync API key from input or environment variable"""
    return api_key or os.getenv("SYNC_API_KEY", "")


def format_error(error: Exception) -> str:
    """Format an exception as an error string for ComfyUI"""
    error_msg = str(error)
    if not error_msg.startswith("ERROR:"):
        return f"ERROR: {error_msg}"
    return error_msg


def ensure_absolute_path(path: Path) -> str:
    """Ensure path is absolute and return as string"""
    if not path.is_absolute():
        path = path.resolve()
    return str(path)


def parse_json_string(json_str: str) -> Any:
    """Parse a JSON string, handling empty strings"""
    if not json_str or not json_str.strip():
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {e}")


def create_output_dir(base_dir: Path, subdir: Optional[str] = None) -> Path:
    """Create output directory and return absolute path"""
    if subdir:
        output_dir = base_dir / subdir
    else:
        output_dir = base_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.resolve()

