"""
ComfyUI node for processing CSV with S3 URLs or URL lists.
Wraps scripts/api/s3_csv.py with flexible inputs
"""
import sys
import json
import csv
from pathlib import Path
from typing import List, Optional

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
get_sync_api_key = _comfyui_utils.get_sync_api_key
get_s3_client = _comfyui_utils.get_s3_client
parse_json_string = _comfyui_utils.parse_json_string


class ProcessCSV:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "input_type": (["csv_file", "list"], {"default": "csv_file"}),
            },
            "optional": {
                "credentials": ("CREDENTIALS", {"default": None}),
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "csv_path": ("STRING", {"default": ""}),  # Legacy support
                "video_urls": ("STRING", {"default": ""}),  # JSON list
                "audio_urls": ("STRING", {"default": ""}),  # JSON list
                "limit": ("INT", {"default": 0, "min": 0}),  # 0 means no limit
                "test_mode": ("BOOLEAN", {"default": False}),
        }
    
    RETURN_TYPES = ("INT", "STRING", "DIRECTORY_DATA")
    RETURN_NAMES = ("processed_count", "results_json", "output_directory")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/api"
    
    def run(self, input_type: str, credentials: dict = None,
            directory_data: dict = None, csv_path: str = "",
            video_urls: str = "", audio_urls: str = "",
            limit: int = 0, test_mode: bool = False):
        """Run CSV/list processing"""
        try:
            creds = credentials or {}
            api_key = creds.get("sync_api_key", "") or get_sync_api_key("")
            if not api_key:
            
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            
            # Get S3 client
            try:
            except Exception as e:
            
            from api.s3_csv import (
                s3_uri_to_presigned_url, generate_sync
            )
            import time
            
            results = []
            output_dir = Path.cwd() / "sync_outputs"
            output_dir.mkdir(exist_ok=True)
            
            if input_type == "csv_file":
                if directory_data and not directory_data.get("error"):
                    dir_path = normalize_path(directory_data.get("path", ""))
                    csv_files = list(dir_path.glob("*.csv"))
                    if csv_files:
                    else:
                elif csv_path:

                else:
                
                if not csv_file.exists():
                
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
                    rows = list(reader)
                
                # Filter rows
                rows_to_process = rows
                if test_mode:
                elif limit > 0:
                
                for i, row in enumerate(rows_to_process, 1):
                        audio_s3 = row.get('audio', '').strip()
                        video_s3 = row.get('video', '').strip()
                        
                        if not audio_s3 or not video_s3:
                                'csv_row': i,
                                'success': False,
                                'error': 'Missing audio or video URL'
                            })
                            continue
                        
                        # Convert S3 URIs to presigned URLs if needed
                        audio_url = s3_uri_to_presigned_url(audio_s3, s3_client)
                        video_url = s3_uri_to_presigned_url(video_s3, s3_client)
                        
                        # Parse ASD column
                        asd_value = row.get('asd', '').strip().lower()
                        enable_asd = asd_value in ['true', '1', 'yes', 'y']
                        
                        # Make API request
                        result = generate_sync(api_key, audio_url, video_url, enable_asd)
                        job_id = result.get('id', 'N/A')
                        
                        results.append({
                            'csv_row': i,
                            'success': True,
                            'audio_s3': audio_s3,
                            'video_s3': video_s3,
                            'job_id': job_id,
                        })
                        
                        time.sleep(1)  # Rate limiting
                        
                    except Exception as error:
                            'csv_row': i,
                            'success': False,
                            'error': str(error)
                        })
            
            else:  # list mode
                # Process URL lists
                if not video_urls or not audio_urls:
                
                try:
                    audio_list = parse_json_string(audio_urls)
                except ValueError as e:
                
                if not isinstance(video_list, list) or not isinstance(audio_list, list):
                
                if len(video_list) != len(audio_list):
                
                # Filter pairs
                pairs_to_process = list(zip(video_list, audio_list))
                if test_mode:
                elif limit > 0:
                
                for i, (video_url, audio_url) in enumerate(pairs_to_process, 1):
                        # Convert S3 URIs if needed
                        video_url_processed = s3_uri_to_presigned_url(video_url, s3_client)
                        audio_url_processed = s3_uri_to_presigned_url(audio_url, s3_client)
                        
                        # Make API request (no ASD for list mode by default)
                        result = generate_sync(api_key, audio_url_processed, video_url_processed, False)
                        job_id = result.get('id', 'N/A')
                        
                        results.append({
                            'pair_index': i,
                            'success': True,
                            'video_url': video_url,
                            'audio_url': audio_url,
                            'job_id': job_id,
                        })
                        
                        time.sleep(1)  # Rate limiting
                        
                    except Exception as error:
                            'pair_index': i,
                            'success': False,
                            'error': str(error)
                        })
            
            # Save results
            results_file = output_dir / 'sync_results.json'
            with open(results_file, 'w') as f:
            
            successful = sum(1 for r in results if r.get('success', False))
            
            # Get output files
            output_files = list(output_dir.glob("*"))
            output_files = [f for f in output_files if f.is_file()]
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(output_dir),
                "file_count": len(output_files),
                "files": [ensure_absolute_path(f) for f in output_files],
            }
            
            return (
                successful,
                json.dumps(results),
                directory_data
            )
            
        except Exception as e:

