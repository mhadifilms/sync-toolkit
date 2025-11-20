#!/usr/bin/env python3
"""
Upload files to S3 with unified configuration and consistent interface.

Replaces upload.sh with Python implementation using unified config system.
"""
import sys
import argparse
import time
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import (
    normalize_path, prompt_path, print_section, print_progress,
    ensure_output_dir
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


def parse_s3_path(s3_path: str) -> tuple[str, str]:
    """Parse S3 path into bucket and key"""
    if not s3_path.startswith('s3://'):
        raise ValueError(f"Invalid S3 path: {s3_path}. Must start with s3://")
    
    s3_path = s3_path.replace('s3://', '')
    parts = s3_path.split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ''
    
    return bucket, key


def upload_file(s3_client, local_file: Path, bucket: str, key: str, 
                skip_existing: bool = False, verbose: bool = False) -> bool:
    """Upload a single file to S3"""
    filename = local_file.name
    
    try:
        # Check if exists
        if skip_existing:
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                if verbose:
                    print(f"⊘ Skipping: {filename} (exists)")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
        
        # Upload file
        s3_client.upload_file(str(local_file), bucket, key)
        if verbose:
            print(f"✓ Uploaded: {filename}")
        return True
    except Exception as e:
        print(f"✗ Failed: {filename} - {e}", file=sys.stderr)
        return False


def find_files(input_dir: Path, pattern: str, preserve_structure: bool) -> List[Path]:
    """Find files matching pattern"""
    files = []
    
    if preserve_structure:
        # Recursive search
        for ext in ['*'] if pattern == '*' else [pattern]:
            files.extend(input_dir.rglob(ext))
    else:
        # Top-level only
        for ext in ['*'] if pattern == '*' else [pattern]:
            files.extend(input_dir.glob(ext))
    
    # Filter out hidden files and directories
    files = [f for f in files if f.is_file() and not f.name.startswith('.')]
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(
        description="Upload files to S3 with unified configuration"
    )
    parser.add_argument('input_dir', nargs='?', help='Directory containing files to upload')
    parser.add_argument('s3_dest', nargs='?', help='S3 destination path (s3://bucket/path/)')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be uploaded')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')
    parser.add_argument('--skip-existing', '-s', action='store_true', help='Skip existing files')
    parser.add_argument('--parallel', '-p', type=int, default=8, help='Parallel uploads (default: 8)')
    parser.add_argument('--pattern', default='*', help='File pattern to match (default: *)')
    parser.add_argument('--preserve-structure', action='store_true', help='Preserve directory structure')
    
    args = parser.parse_args()
    
    # Get input directory
    if args.input_dir:
        input_dir = normalize_path(args.input_dir)
    else:
        input_dir = prompt_path("Enter directory to upload", must_exist=True)
    
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"ERROR: Directory not found: {input_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Get S3 destination
    if args.s3_dest:
        s3_dest = args.s3_dest
    else:
        s3_dest = input("Enter S3 destination path (s3://bucket/path/): ").strip()
    
    if not s3_dest:
        print("ERROR: S3 destination is required", file=sys.stderr)
        sys.exit(1)
    
    # Ensure S3 path ends with /
    if not s3_dest.endswith('/'):
        s3_dest += '/'
    
    # Parse S3 path
    try:
        bucket, base_key = parse_s3_path(s3_dest)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get S3 client
    try:
        s3_client = get_s3_client()
    except Exception as e:
        print(f"ERROR: Failed to initialize S3 client: {e}", file=sys.stderr)
        print("Make sure AWS credentials are configured.", file=sys.stderr)
        sys.exit(1)
    
    # Find files
    files = find_files(input_dir, args.pattern, args.preserve_structure)
    
    if not files:
        print(f"No files matching pattern '{args.pattern}' found in {input_dir}")
        sys.exit(0)
    
    # Print configuration
    print_section("Upload Configuration")
    print(f"  Input directory:  {input_dir}")
    print(f"  S3 destination:   s3://{bucket}/{base_key}")
    print(f"  Pattern:          {args.pattern}")
    print(f"  Parallel jobs:    {args.parallel}")
    print(f"  Structure:        {'Preserved' if args.preserve_structure else 'Flat'}")
    if args.dry_run:
        print(f"  Mode:             DRY RUN")
    if args.skip_existing:
        print(f"  Mode:             Skip existing files")
    print("=" * 60)
    print()
    
    print(f"Found {len(files)} file(s) to upload")
    if args.verbose:
        for f in files[:10]:  # Show first 10
            size = f.stat().st_size / (1024 * 1024)
            print(f"  - {f.name} ({size:.2f} MB)")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        print()
    
    if args.dry_run:
        print(f"DRY RUN: Would upload {len(files)} file(s) to s3://{bucket}/{base_key}")
        sys.exit(0)
    
    # Prepare upload tasks
    tasks = []
    for local_file in files:
        if args.preserve_structure:
            rel_path = local_file.relative_to(input_dir)
            key = f"{base_key}{rel_path.as_posix()}"
        else:
            key = f"{base_key}{local_file.name}"
        
        tasks.append((local_file, bucket, key))
    
    # Upload files
    start_time = time.time()
    successful = 0
    failed = 0
    
    if args.parallel == 1:
        # Sequential upload
        for i, (local_file, bucket, key) in enumerate(tasks, 1):
            if upload_file(s3_client, local_file, bucket, key, 
                          args.skip_existing, args.verbose):
                successful += 1
            else:
                failed += 1
            
            if not args.verbose and i % 10 == 0:
                print_progress(i, len(tasks), "Uploading")
    else:
        # Parallel upload
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {
                executor.submit(upload_file, s3_client, local_file, bucket, key,
                              args.skip_existing, args.verbose): (local_file, bucket, key)
                for local_file, bucket, key in tasks
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                if future.result():
                    successful += 1
                else:
                    failed += 1
                
                if not args.verbose:
                    print_progress(i, len(tasks), "Uploading")
    
    # Print summary
    duration = time.time() - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    
    print_section("Summary")
    print(f"  Total:      {len(tasks)}")
    print(f"  Successful: {successful}")
    if failed > 0:
        print(f"  Failed:     {failed}")
    print(f"  Duration:   {minutes}m {seconds}s")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    
    print("\n✅ All uploads completed successfully!")


if __name__ == '__main__':
    main()

