"""
ComfyUI node for uploading to S3 or Supabase Storage.
Combines scripts/transfer/s3_upload.py and scripts/transfer/sb_upload.py
"""
import sys
import json
from pathlib import Path
from typing import List

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
get_supabase_credentials = _comfyui_utils.get_supabase_credentials
parse_json_string = _comfyui_utils.parse_json_string


class UploadToStorage:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "storage_type": (["s3", "supabase"], {"default": "s3"}),  # Will be overridden by credentials if provided
            },
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "input_path": ("STRING", {"default": ""}),  # Legacy support
                "credentials": ("CREDENTIALS", {"default": None}),
                # S3 settings
                "s3_bucket": ("STRING", {"default": ""}),
                "s3_dest": ("STRING", {"default": ""}),  # s3://bucket/path/
                # Supabase settings
                "supabase_bucket": ("STRING", {"default": ""}),  # Override bucket name
                # Upload options
                "parallel": ("INT", {"default": 8, "min": 1}),
                "pattern": ("STRING", {"default": "*"}),
                "preserve_structure": ("BOOLEAN", {"default": False}),
        }
    
    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("uploaded_count", "manifest_path", "output_directory")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/storage"
    
    def run(self, storage_type: str, directory_data: dict = None, input_path: str = "",
            credentials: dict = None,
            s3_bucket: str = "", s3_dest: str = "",
            supabase_bucket: str = "",
            parallel: int = 8, pattern: str = "*", preserve_structure: bool = False):
        """Run upload"""
        try:
            if directory_data and not directory_data.get("error"):
                # Use files from directory_data if available
                if directory_data.get("files"):
                else:
            elif input_path:
                try:
                    if files_list and isinstance(files_list, list):
                        input_files = [normalize_path(f) for f in files_list]
                        base_dir = input_files[0].parent if input_files else Path.cwd()
                    else:
                        base_dir = normalize_path(input_path)
                        if not base_dir.exists():
                        input_files = None
                except (ValueError, json.JSONDecodeError):
                    base_dir = normalize_path(input_path)
                    if not base_dir.exists():
                    input_files = None
            else:
            
            # Extract credentials
            creds = credentials or {}
            # Use storage_type from credentials if available, otherwise use node setting
            final_storage_type = creds.get("storage_type", storage_type)
            use_sso = creds.get("use_sso", False)
            aws_access_key_id = creds.get("aws_access_key_id", "") if not use_sso else None
            aws_secret_key = creds.get("aws_secret_access_key", "") if not use_sso else None
            aws_region = creds.get("aws_region", "us-east-1")
            supabase_host = creds.get("supabase_host", "")
            supabase_key = creds.get("supabase_key", "")
            
            # Use bucket from settings or credentials
            if final_storage_type == "s3":
                return self._upload_to_s3(
                    base_dir, input_files, final_bucket, aws_region,
                    aws_access_key_id, aws_secret_key, s3_dest,
                    parallel, pattern, preserve_structure, use_sso
                )
            else:  # supabase
                final_bucket = supabase_bucket or creds.get("supabase_bucket", "")
                return self._upload_to_supabase(
                    base_dir, input_files, supabase_host, final_bucket, supabase_key,
                    parallel
                )
                
        except Exception as e:
    
    def _upload_to_s3(self, base_dir: Path, input_files: List[Path],
                     s3_bucket: str, s3_region: str,
                     s3_access_key_id: str, s3_secret_key: str, s3_dest: str,
                     parallel: int, pattern: str, preserve_structure: bool, use_sso: bool = False):
        """Upload to S3"""
        from transfer.s3_upload import find_files, upload_file, parse_s3_path
        
        if not s3_dest:
                return (0, "ERROR: S3 bucket or destination required", "")
            s3_dest = f"s3://{s3_bucket}/"
        
        # Parse S3 path
        try:
        except ValueError as e:
        
        # Get S3 client
        try:
        except Exception as e:
        
        # Find files
        if input_files:
        else:
        
        if not files:
        
        # Upload files
        successful = 0
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        tasks = []
        for local_file in files:
                rel_path = local_file.relative_to(base_dir)
                key = f"{base_key}{rel_path.as_posix()}"
            else:
            tasks.append((local_file, bucket, key))
        
        if parallel == 1:
                if upload_file(s3_client, local_file, bucket, key, False, False):
        else:
                futures = {
                    executor.submit(upload_file, s3_client, local_file, bucket, key, False, False): (local_file, bucket, key)
                    for local_file, bucket, key in tasks
                }
                for future in as_completed(futures):
                        successful += 1
        
            # Create manifest (if video/audio files)
            manifest_path = ""
            try:
                videos, audios = find_media_files(base_dir)
                if videos or audios:
                    video_urls = []
                    audio_urls = []
                    for v in videos:
                            rel = v.relative_to(base_dir)
                            key_path = f"{base_key}{rel.as_posix()}"
                        else:
                        video_urls.append(f"s3://{bucket}/{key_path}")
                    for a in audios:
                            rel = a.relative_to(base_dir)
                            key_path = f"{base_key}{rel.as_posix()}"
                        else:
                        audio_urls.append(f"s3://{bucket}/{key_path}")
                    manifest_file = base_dir / "uploaded_urls.txt"
                    write_manifest(video_urls, audio_urls, manifest_file)
                    manifest_path = ensure_absolute_path(manifest_file)
            except Exception as e:
                pass
        
        return (successful, manifest_path, ensure_absolute_path(base_dir))
    
    def _upload_to_supabase(self, base_dir: Path, input_files: List[Path],
                           supabase_host: str, supabase_bucket: str, supabase_key: str,
                           parallel: int):
        """Upload to Supabase"""
        from transfer.sb_upload import (
            iter_files, supabase_upload, is_video_mime, is_audio_mime
        )
        from utils.common import write_manifest, slugify, natural_sort_key
        from datetime import datetime
        
        # Get credentials
        creds = get_supabase_credentials(supabase_host, supabase_bucket, supabase_key)
        if not creds["host"] or not creds["bucket"] or not creds["key"]:
        
        host = creds["host"].rstrip("/")
        bucket = creds["bucket"]
        key = creds["key"]
        
        # Get files
        if input_files:
        else:
        
        if not files:
        
        # Build remote prefix
        src_folder_name = base_dir.name if base_dir.is_dir() else base_dir.parent.name or base_dir.stem
        src_folder_name = slugify(src_folder_name) or "upload"
        ts = datetime.now().strftime("%Y%m%d%H%M")
        remote_prefix = f"{src_folder_name}_{ts}"
        
        # Helper function to build public URL
        def build_public_url(remote_path: str) -> str:
        
        # Upload files
        ok_urls = {"video": [], "audio": []}
        successful = 0
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def do_task(item):
            # supabase_upload uses global HOST/BUCKET, so we need to set them temporarily
            import transfer.sb_upload as sb_module
            original_host = getattr(sb_module, 'HOST', '')
            original_bucket = getattr(sb_module, 'BUCKET', '')
            try:
                sb_module.BUCKET = bucket
                ok, msg = supabase_upload(fp, rp, key, ct)
            finally:
                sb_module.BUCKET = original_bucket
            return fp, rp, ct, ok, msg
        
        tasks = []
        for fp in files:
            remote_path = f"{remote_prefix}/{rel}".replace("//", "/")
            ctype = guess_mime_type(fp)
            tasks.append((fp, remote_path, ctype))
        
        with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
                if ok:
                    url = build_public_url(rp)
                    if is_video_mime(ct):
                    elif is_audio_mime(ct):
        
        # Write manifest
        def sort_by_filename(urls):
        video_urls = sort_by_filename(ok_urls["video"])
        audio_urls = sort_by_filename(ok_urls["audio"])
        
        manifest_file = base_dir / "uploaded_urls.txt"
        write_manifest(video_urls, audio_urls, manifest_file)
        
        return (successful, ensure_absolute_path(manifest_file), ensure_absolute_path(base_dir))


def guess_mime_type(path: Path) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return mime or 'application/octet-stream'

