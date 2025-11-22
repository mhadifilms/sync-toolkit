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
get_supabase_credentials = _comfyui_utils.get_supabase_credentials
parse_json_string = _comfyui_utils.parse_json_string


class UploadToStorage:
    """Upload files to S3 or Supabase Storage"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "storage_type": (["s3", "supabase"], {"default": "s3"}),
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
            # Extract directory path from DIRECTORY_DATA or use legacy string input
            if directory_data and not directory_data.get("error"):
                base_dir = normalize_path(directory_data.get("path", ""))
                # Use files from directory_data if available
                if directory_data.get("files"):
                    input_files = [normalize_path(f) for f in directory_data.get("files", [])]
                else:
                    input_files = None
            elif input_path:
                # Parse input_path - can be directory or JSON list of files
                try:
                    files_list = parse_json_string(input_path)
                    if files_list and isinstance(files_list, list):
                        # Input is a JSON list of file paths
                        input_files = [normalize_path(f) for f in files_list]
                        base_dir = input_files[0].parent if input_files else Path.cwd()
                    else:
                        # Input is a directory path
                        base_dir = normalize_path(input_path)
                        if not base_dir.exists():
                            return (0, "ERROR: Input path not found", "")
                        input_files = None
                except (ValueError, json.JSONDecodeError):
                    # Not JSON, treat as directory path
                    base_dir = normalize_path(input_path)
                    if not base_dir.exists():
                        return (0, "ERROR: Input path not found", "")
                    input_files = None
            else:
                return (0, "ERROR: Input path or directory_data required", "")
            
            # Extract credentials
            creds = credentials or {}
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            supabase_host = creds.get("supabase_host", "")
            supabase_key = creds.get("supabase_key", "")
            
            # Use bucket from settings or credentials
            if storage_type == "s3":
                final_bucket = s3_bucket or creds.get("s3_bucket", "")
                return self._upload_to_s3(
                    base_dir, input_files, final_bucket, aws_region,
                    aws_access_key_id, aws_secret_key, s3_dest,
                    parallel, pattern, preserve_structure
                )
            else:  # supabase
                final_bucket = supabase_bucket or creds.get("supabase_bucket", "")
                return self._upload_to_supabase(
                    base_dir, input_files, supabase_host, final_bucket, supabase_key,
                    parallel
                )
                
        except Exception as e:
            return (0, format_error(e), "")
    
    def _upload_to_s3(self, base_dir: Path, input_files: List[Path],
                     s3_bucket: str, s3_region: str,
                     s3_access_key_id: str, s3_secret_key: str, s3_dest: str,
                     parallel: int, pattern: str, preserve_structure: bool):
        """Upload to S3"""
        from transfer.s3_upload import find_files, upload_file, parse_s3_path
        
        if not s3_dest:
            if not s3_bucket:
                return (0, "ERROR: S3 bucket or destination required", "")
            s3_dest = f"s3://{s3_bucket}/"
        
        # Parse S3 path
        try:
            bucket, base_key = parse_s3_path(s3_dest)
        except ValueError as e:
            return (0, format_error(e), "")
        
        # Get S3 client
        try:
            s3_client = get_s3_client(s3_region, s3_access_key_id, s3_secret_key)
        except Exception as e:
            return (0, format_error(e), "")
        
        # Find files
        if input_files:
            files = input_files
        else:
            files = find_files(base_dir, pattern, preserve_structure)
        
        if not files:
            return (0, "ERROR: No files found to upload", "")
        
        # Upload files
        successful = 0
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        tasks = []
        for local_file in files:
            if preserve_structure and not input_files:
                rel_path = local_file.relative_to(base_dir)
                key = f"{base_key}{rel_path.as_posix()}"
            else:
                key = f"{base_key}{local_file.name}"
            tasks.append((local_file, bucket, key))
        
        if parallel == 1:
            for local_file, bucket, key in tasks:
                if upload_file(s3_client, local_file, bucket, key, False, False):
                    successful += 1
        else:
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = {
                    executor.submit(upload_file, s3_client, local_file, bucket, key, False, False): (local_file, bucket, key)
                    for local_file, bucket, key in tasks
                }
                for future in as_completed(futures):
                    if future.result():
                        successful += 1
        
            # Create manifest (if video/audio files)
            manifest_path = ""
            try:
                from utils.common import find_media_files, write_manifest
                videos, audios = find_media_files(base_dir)
                if videos or audios:
                    # Build S3 URLs for manifest
                    video_urls = []
                    audio_urls = []
                    for v in videos:
                        if preserve_structure:
                            rel = v.relative_to(base_dir)
                            key_path = f"{base_key}{rel.as_posix()}"
                        else:
                            key_path = f"{base_key}{v.name}"
                        video_urls.append(f"s3://{bucket}/{key_path}")
                    for a in audios:
                        if preserve_structure:
                            rel = a.relative_to(base_dir)
                            key_path = f"{base_key}{rel.as_posix()}"
                        else:
                            key_path = f"{base_key}{a.name}"
                        audio_urls.append(f"s3://{bucket}/{key_path}")
                    manifest_file = base_dir / "uploaded_urls.txt"
                    write_manifest(video_urls, audio_urls, manifest_file)
                    manifest_path = ensure_absolute_path(manifest_file)
            except Exception as e:
                # Manifest creation is optional
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
            return (0, "ERROR: Supabase credentials required (host, bucket, key)", "")
        
        host = creds["host"].rstrip("/")
        bucket = creds["bucket"]
        key = creds["key"]
        
        # Get files
        if input_files:
            files = input_files
        else:
            files = list(iter_files(base_dir))
        
        if not files:
            return (0, "ERROR: No files found to upload", "")
        
        # Build remote prefix
        src_folder_name = base_dir.name if base_dir.is_dir() else base_dir.parent.name or base_dir.stem
        src_folder_name = slugify(src_folder_name) or "upload"
        ts = datetime.now().strftime("%Y%m%d%H%M")
        remote_prefix = f"{src_folder_name}_{ts}"
        
        # Helper function to build public URL
        def build_public_url(remote_path: str) -> str:
            return f"{host}/storage/v1/object/public/{bucket}/{remote_path}"
        
        # Upload files
        ok_urls = {"video": [], "audio": []}
        successful = 0
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def do_task(item):
            fp, rp, ct = item
            # supabase_upload uses global HOST/BUCKET, so we need to set them temporarily
            import transfer.sb_upload as sb_module
            original_host = getattr(sb_module, 'HOST', '')
            original_bucket = getattr(sb_module, 'BUCKET', '')
            try:
                sb_module.HOST = host
                sb_module.BUCKET = bucket
                ok, msg = supabase_upload(fp, rp, key, ct)
            finally:
                sb_module.HOST = original_host
                sb_module.BUCKET = original_bucket
            return fp, rp, ct, ok, msg
        
        tasks = []
        for fp in files:
            rel = fp.relative_to(base_dir) if base_dir.is_dir() else fp.name
            remote_path = f"{remote_prefix}/{rel}".replace("//", "/")
            ctype = guess_mime_type(fp)
            tasks.append((fp, remote_path, ctype))
        
        with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
            for fp, rp, ct, ok, msg in ex.map(do_task, tasks):
                if ok:
                    successful += 1
                    url = build_public_url(rp)
                    if is_video_mime(ct):
                        ok_urls["video"].append(url)
                    elif is_audio_mime(ct):
                        ok_urls["audio"].append(url)
        
        # Write manifest
        def sort_by_filename(urls):
            return sorted(urls, key=lambda u: natural_sort_key(u.rsplit('/', 1)[-1]))
        video_urls = sort_by_filename(ok_urls["video"])
        audio_urls = sort_by_filename(ok_urls["audio"])
        
        manifest_file = base_dir / "uploaded_urls.txt"
        write_manifest(video_urls, audio_urls, manifest_file)
        
        return (successful, ensure_absolute_path(manifest_file), ensure_absolute_path(base_dir))


def guess_mime_type(path: Path) -> str:
    """Guess MIME type"""
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return mime or 'application/octet-stream'

