#!/usr/bin/env python3
"""
Process CSV file with S3 URLs and submit to Sync.so API.

Supports CSV files with columns: audio, video, asd (optional)
Audio and video columns can contain S3 URIs (s3://bucket/key) or HTTP URLs.
"""
import csv
import time
import json
import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

import boto3
import requests
from botocore.exceptions import ClientError

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import prompt_path, print_section, save_json, normalize_path


SYNC_API_URL = 'https://api.sync.so/v2/generate'
PRESIGNED_URL_EXPIRATION = 3600  # 1 hour


def get_s3_client(region: str = 'us-east-1'):
    """Get S3 client, using config or default credentials"""
    config_manager = get_config_manager()
    storage_config = config_manager.get_aws_config(prompt=False)
    
    # Try to use configured credentials
    if storage_config.aws_access_key_id and storage_config.aws_secret_access_key:
        return boto3.client(
            's3',
            region_name=storage_config.aws_region or region,
            aws_access_key_id=storage_config.aws_access_key_id,
            aws_secret_access_key=storage_config.aws_secret_access_key
        )
    
    # Fall back to default credential chain (env vars, IAM role, etc.)
    return boto3.client('s3', region_name=region)


def s3_uri_to_presigned_url(s3_uri: str, s3_client) -> str:
    """Convert S3 URI to presigned URL for private buckets"""
    if not s3_uri or not s3_uri.startswith('s3://'):
        return s3_uri  # Return as-is if not an S3 URI
    
    # Parse s3://bucket-name/path/to/file
    s3_uri = s3_uri.replace('s3://', '')
    parts = s3_uri.split('/', 1)
    
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")
    
    bucket = parts[0]
    key = parts[1]
    
    try:
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=PRESIGNED_URL_EXPIRATION
        )
        return presigned_url
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        raise


def generate_sync(api_key: str, audio_url: str, video_url: str, enable_asd: bool) -> Dict[str, Any]:
    """Make API request to Sync.so"""
    payload = {
        "model": "lipsync-2-pro",
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url}
        ]
    }
    
    # Add options if active speaker detection is enabled
    if enable_asd:
        payload["options"] = {
            "active_speaker_detection": {"auto_detect": True}
        }
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(SYNC_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def process_csv(csv_path: Path, api_key: str, limit: Optional[int] = None, 
                test_mode: bool = False, specific_rows: Optional[List[int]] = None):
    """Process CSV file and make API requests"""
    print_section("Processing CSV File")
    print(f"CSV file: {csv_path}")
    
    results: List[Dict[str, Any]] = []
    s3_client = get_s3_client()
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Normalize headers to lowercase
        reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]
        rows = list(reader)
    
    # Filter rows based on configuration
    rows_to_process = rows
    
    if specific_rows:
        rows_to_process = [rows[i-1] for i in specific_rows if 1 <= i <= len(rows)]
        print(f"Processing specific rows: {specific_rows}")
    elif limit and limit > 0:
        rows_to_process = rows[:limit]
        print(f"Processing first {len(rows_to_process)} rows (limit={limit})")
    elif test_mode:
        rows_to_process = rows[:1]
        print("TEST MODE: Processing only the first row")
    
    print(f"Found {len(rows)} total rows")
    print(f"Will process {len(rows_to_process)} rows\n")
    
    for i, row in enumerate(rows_to_process, 1):
        original_row_num = rows.index(row) + 1
        
        print(f"Processing row {i}/{len(rows_to_process)} (CSV row {original_row_num})...")
        
        try:
            # Get URLs
            audio_s3 = row.get('audio', '').strip()
            video_s3 = row.get('video', '').strip()
            
            if not audio_s3 or not video_s3:
                raise ValueError("Missing audio or video URL")
            
            # Convert S3 URIs to presigned URLs if needed
            print(f"  Audio: {audio_s3[:60]}...")
            audio_url = s3_uri_to_presigned_url(audio_s3, s3_client)
            
            print(f"  Video: {video_s3[:60]}...")
            video_url = s3_uri_to_presigned_url(video_s3, s3_client)
            
            # Parse ASD column
            asd_value = row.get('asd', '').strip().lower()
            enable_asd = asd_value in ['true', '1', 'yes', 'y']
            print(f"  Active Speaker Detection: {enable_asd}")
            
            # Make API request
            result = generate_sync(api_key, audio_url, video_url, enable_asd)
            job_id = result.get('id', 'N/A')
            print(f"  ✓ Success! Job ID: {job_id}\n")
            
            results.append({
                'csv_row': original_row_num,
                'success': True,
                'audio_s3': audio_s3,
                'video_s3': video_s3,
                'job_id': job_id,
            })
            
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as error:
            print(f"  ✗ Failed: {str(error)}\n")
            results.append({
                'csv_row': original_row_num,
                'success': False,
                'error': str(error),
            })
    
    # Save results
    output_file = csv_path.parent / 'sync_results.json'
    save_json(results, output_file)
    
    # Print summary
    print_section("Processing Complete")
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Total rows: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nResults saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Process CSV file with S3 URLs and submit to Sync.so API"
    )
    parser.add_argument('--csv', type=str, help='CSV file path')
    parser.add_argument('--limit', type=int, help='Limit number of rows to process')
    parser.add_argument('--test', action='store_true', help='Test mode (process first row only)')
    parser.add_argument('--rows', type=str, help='Comma-separated row numbers (e.g., "1,3,5")')
    
    args = parser.parse_args()
    
    # Get CSV path
    if args.csv:
        csv_path = normalize_path(args.csv)
    else:
        csv_path = prompt_path("Enter path to CSV file", must_exist=True)
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    # Get API key
    config_manager = get_config_manager()
    api_key = config_manager.get_sync_api_key(prompt=True)
    if not api_key:
        print("ERROR: Sync API key is required.", file=sys.stderr)
        sys.exit(1)
    
    # Parse specific rows if provided
    specific_rows = None
    if args.rows:
        try:
            specific_rows = [int(r.strip()) for r in args.rows.split(',')]
        except ValueError:
            print("ERROR: Invalid row numbers format. Use comma-separated integers.", file=sys.stderr)
            sys.exit(1)
    
    # Process CSV
    try:
        process_csv(csv_path, api_key, limit=args.limit, 
                   test_mode=args.test, specific_rows=specific_rows)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
