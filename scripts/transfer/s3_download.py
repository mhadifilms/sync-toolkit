#!/usr/bin/env python3
"""
Download files from S3 with unified configuration and consistent interface.

Replaces download.sh with Python implementation using unified config system.
"""
import sys
import argparse
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import (
    normalize_path, prompt_path, print_section, print_progress,
    ensure_output_dir, load_json
)


def get_s3_client():
    """Get S3 client using unified config"""
    config_manager = get_config_manager()
    storage_config = config_manager.get_aws_config(prompt=False)
    
    # Try configured credentials first
    if storage_config.aws_access_key_id and storage_config.aws_secret_access_key:
        return boto3.client(
            's3',
            region_name=storage_config.aws_region,
            aws_access_key_id=storage_config.aws_access_key_id,
            aws_secret_access_key=storage_config.aws_secret_access_key
        )
    
    # Fall back to default credential chain
    return boto3.client('s3', region_name=storage_config.aws_region)


def download_file(s3_client, bucket: str, key: str, local_path: Path, 
                  verbose: bool = False) -> bool:
    """Download a single file from S3"""
    try:
        ensure_output_dir(local_path.parent)
        s3_client.download_file(bucket, key, str(local_path))
        if verbose:
            print(f"✓ Downloaded: {local_path.name}")
        return True
    except Exception as e:
        print(f"✗ Failed: {key} - {e}", file=sys.stderr)
        return False


def sync_directory(s3_client, s3_source: str, local_dest: Path, verbose: bool):
    """Sync entire S3 directory"""
    # Parse S3 path
    if not s3_source.startswith('s3://'):
        raise ValueError("S3 source must start with s3://")
    
    s3_source = s3_source.replace('s3://', '')
    if not s3_source.endswith('/'):
        s3_source += '/'
    
    parts = s3_source.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    ensure_output_dir(local_dest)
    
    print(f"Syncing s3://{bucket}/{prefix} to {local_dest}...")
    
    # Use boto3 paginator to list all objects
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    total_files = 0
    for page in pages:
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('/'):
                continue  # Skip directories
            
            # Calculate local path
            rel_path = key[len(prefix):] if prefix else key
            local_path = local_dest / rel_path
            
            if download_file(s3_client, bucket, key, local_path, verbose):
                total_files += 1
    
    return total_files


def download_from_list(s3_client, input_file: Path, local_dest: Path, 
                       suffix: str, verbose: bool):
    """Download files from a list file (number<TAB>s3://path format)"""
    ensure_output_dir(local_dest)
    
    tasks = []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            number = parts[0]
            s3_url = parts[1]
            
            if not s3_url.startswith('s3://'):
                continue
            
            # Parse S3 URL
            s3_url = s3_url.replace('s3://', '')
            url_parts = s3_url.split('/', 1)
            bucket = url_parts[0]
            key = url_parts[1] if len(url_parts) > 1 else ''
            
            output_file = local_dest / f"{number}_{suffix}.mov"
            tasks.append((bucket, key, output_file))
    
    if not tasks:
        print("No valid entries found in input file")
        return 0
    
    print(f"Found {len(tasks)} file(s) to download")
    
    successful = 0
    for i, (bucket, key, output_file) in enumerate(tasks, 1):
        if download_file(s3_client, bucket, key, output_file, verbose):
            successful += 1
        if not verbose:
            print_progress(i, len(tasks), "Downloading")
    
    return successful


def download_from_json(s3_client, json_file: Path, local_dest: Path, 
                       common_name: str, verbose: bool):
    """Download files from JSON file (extracts job_ids)"""
    ensure_output_dir(local_dest)
    
    # Load JSON
    data = load_json(json_file)
    
    # Get S3 config
    config_manager = get_config_manager()
    bucket, base_path = config_manager.get_s3_config(prompt=True)
    
    if not bucket or not base_path:
        print("ERROR: S3_BUCKET and S3_BASE_PATH must be configured", file=sys.stderr)
        sys.exit(1)
    
    # Extract job IDs
    job_ids = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'job_id' in item:
                job_ids.append(item['job_id'])
    elif isinstance(data, dict) and 'job_id' in data:
        job_ids.append(data['job_id'])
    
    if not job_ids:
        print("ERROR: No job_ids found in JSON file", file=sys.stderr)
        sys.exit(1)
    
    # Get common name if not provided
    if not common_name:
        common_name = input("Enter a common name prefix for downloaded files: ").strip()
        if not common_name:
            print("ERROR: Common name cannot be empty", file=sys.stderr)
            sys.exit(1)
    
    # Prepare download tasks
    tasks = []
    s3_file = "result.mov"  # Default filename
    
    for i, job_id in enumerate(job_ids, 1):
        key = f"{base_path}/{job_id}/{s3_file}"
        output_file = local_dest / f"{common_name}_{i}.mov"
        tasks.append((bucket, key, output_file))
    
    print(f"Found {len(tasks)} job(s) to download")
    
    # Download files
    successful = 0
    for i, (bucket, key, output_file) in enumerate(tasks, 1):
        if download_file(s3_client, bucket, key, output_file, verbose):
            successful += 1
        if not verbose:
            print_progress(i, len(tasks), "Downloading")
    
    return successful


def main():
    parser = argparse.ArgumentParser(
        description="Download files from S3 with unified configuration"
    )
    parser.add_argument('source', nargs='?', help='S3 source path or input file')
    parser.add_argument('dest', nargs='?', help='Local destination directory')
    parser.add_argument('--mode', '-m', choices=['sync', 'list', 'json'], 
                       default='sync', help='Operation mode (default: sync)')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be downloaded')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')
    parser.add_argument('--parallel', '-p', type=int, default=10, help='Parallel downloads (default: 10)')
    parser.add_argument('--suffix', '-s', default='v1', help='Suffix for numbered files (list mode)')
    parser.add_argument('--name', '-n', help='Common name prefix (json mode)')
    
    args = parser.parse_args()
    
    # Get S3 client
    try:
        s3_client = get_s3_client()
    except Exception as e:
        print(f"ERROR: Failed to initialize S3 client: {e}", file=sys.stderr)
        print("Make sure AWS credentials are configured.", file=sys.stderr)
        sys.exit(1)
    
    # Mode-specific handling
    if args.mode == 'sync':
        if not args.source:
            args.source = input("Enter S3 source path (s3://bucket/path/): ").strip()
        if not args.dest:
            args.dest = prompt_path("Enter local destination directory", must_exist=False)
        
        local_dest = normalize_path(args.dest)
        
        print_section("S3 Sync Configuration")
        print(f"  Source:        {args.source}")
        print(f"  Destination:   {local_dest}")
        if args.dry_run:
            print(f"  Mode:          DRY RUN")
        print("=" * 60)
        print()
        
        if args.dry_run:
            print(f"DRY RUN: Would sync {args.source} to {local_dest}")
            sys.exit(0)
        
        successful = sync_directory(s3_client, args.source, local_dest, args.verbose)
        print(f"\n✅ Sync complete! Downloaded {successful} file(s)")
    
    elif args.mode == 'list':
        if not args.source:
            args.source = prompt_path("Enter list file path", must_exist=True)
        if not args.dest:
            args.dest = Path.cwd()
        
        input_file = normalize_path(args.source)
        local_dest = normalize_path(args.dest)
        
        print_section("List Download Configuration")
        print(f"  Input file:     {input_file}")
        print(f"  Output dir:     {local_dest}")
        print(f"  Suffix:        {args.suffix}")
        print("=" * 60)
        print()
        
        successful = download_from_list(s3_client, input_file, local_dest, 
                                       args.suffix, args.verbose)
        print(f"\n✅ Download complete! Downloaded {successful} file(s)")
    
    elif args.mode == 'json':
        if not args.source:
            args.source = prompt_path("Enter JSON file path", must_exist=True)
        if not args.dest:
            args.dest = Path.cwd()
        
        json_file = normalize_path(args.source)
        local_dest = normalize_path(args.dest)
        
        print_section("JSON Download Configuration")
        print(f"  JSON file:      {json_file}")
        print(f"  Output dir:     {local_dest}")
        print("=" * 60)
        print()
        
        successful = download_from_json(s3_client, json_file, local_dest,
                                       args.name or '', args.verbose)
        print(f"\n✅ Download complete! Downloaded {successful} file(s)")


if __name__ == '__main__':
    main()

