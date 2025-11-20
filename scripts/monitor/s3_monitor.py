#!/usr/bin/env python3
"""
Monitor S3 upload progress and notify when complete.

Replaces monitor.sh with Python implementation using unified config system.
"""
import sys
import argparse
import time
import re
from pathlib import Path
from datetime import datetime

import boto3

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import normalize_path, print_section


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


def count_s3_files(s3_client, s3_path: str, pattern: str) -> int:
    """Count files in S3 matching pattern"""
    # Parse S3 path
    if not s3_path.startswith('s3://'):
        raise ValueError("S3 path must start with s3://")
    
    s3_path = s3_path.replace('s3://', '')
    if not s3_path.endswith('/'):
        s3_path += '/'
    
    parts = s3_path.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    
    # List objects
    count = 0
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    pattern_re = re.compile(pattern)
    
    for page in pages:
        if 'Contents' not in page:
            continue
        
        for obj in page['Contents']:
            key = obj['Key']
            if pattern_re.search(key):
                count += 1
    
    return count


def count_local_files(local_dir: Path, pattern: str) -> int:
    """Count files in local directory matching pattern"""
    pattern_re = re.compile(pattern)
    count = 0
    
    for file in local_dir.iterdir():
        if file.is_file() and pattern_re.search(file.name):
            count += 1
    
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Monitor S3 upload progress and notify when complete"
    )
    parser.add_argument('--s3-path', '-s', required=True, help='S3 path to monitor')
    parser.add_argument('--local-dir', '-l', help='Local directory to compare against')
    parser.add_argument('--expected', '-e', type=int, required=True, help='Expected number of files')
    parser.add_argument('--interval', '-i', type=int, default=180, help='Check interval in seconds (default: 180)')
    parser.add_argument('--pattern', '-p', default=r'(_bounced\.mov|_bounced\.wav)', 
                       help='File pattern to match')
    parser.add_argument('--log-file', default='/tmp/upload_completion.log', help='Log file path')
    
    args = parser.parse_args()
    
    # Get S3 client
    try:
        s3_client = get_s3_client()
    except Exception as e:
        print(f"ERROR: Failed to initialize S3 client: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Ensure S3 path ends with /
    s3_path = args.s3_path
    if not s3_path.endswith('/'):
        s3_path += '/'
    
    # Parse local directory if provided
    local_dir = None
    if args.local_dir:
        local_dir = normalize_path(args.local_dir)
        if not local_dir.exists():
            print(f"WARNING: Local directory not found: {local_dir}", file=sys.stderr)
            local_dir = None
    
    # Print configuration
    print_section("Monitor Configuration")
    print(f"  S3 path:         {s3_path}")
    if local_dir:
        print(f"  Local directory: {local_dir}")
    print(f"  Expected count:  {args.expected}")
    print(f"  Check interval:  {args.interval}s")
    print(f"  Pattern:         {args.pattern}")
    print(f"  Log file:        {args.log_file}")
    print("=" * 60)
    print()
    
    print(f"Starting monitoring (checking every {args.interval}s)...")
    print()
    
    log_file = Path(args.log_file)
    
    while True:
        try:
            total_s3 = count_s3_files(s3_client, s3_path, args.pattern)
            
            if total_s3 >= args.expected:
                # Write completion log
                with open(log_file, 'w') as f:
                    f.write("\n")
                    f.write("=" * 60 + "\n")
                    f.write("UPLOAD COMPLETED!\n")
                    f.write("=" * 60 + "\n")
                    f.write(f"Total files uploaded: {total_s3}/{args.expected}\n")
                    f.write("\n")
                    
                    # Show breakdown by directory if local dir provided
                    if local_dir and local_dir.exists():
                        f.write("Breakdown by directory:\n")
                        for subdir in local_dir.iterdir():
                            if subdir.is_dir():
                                dirname = subdir.name
                                subdir_s3_path = f"{s3_path}{dirname}/"
                                s3_count = count_s3_files(s3_client, subdir_s3_path, args.pattern)
                                local_count = count_local_files(subdir, args.pattern)
                                f.write(f"  {dirname}: {s3_count}/{local_count} files\n")
                        f.write("\n")
                    
                    f.write(f"All files successfully uploaded to:\n")
                    f.write(f"{s3_path}\n")
                    f.write("=" * 60 + "\n")
                
                # Print to console
                print("\n" + "=" * 60)
                print("UPLOAD COMPLETED!")
                print("=" * 60)
                print(f"Total files uploaded: {total_s3}/{args.expected}")
                print(f"\nLog written to: {log_file}")
                print("=" * 60)
                
                print("\n✅ Monitoring complete!")
                sys.exit(0)
            
            # Show progress
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Progress: {total_s3}/{args.expected} files uploaded")
            
            time.sleep(args.interval)
        
        except KeyboardInterrupt:
            print("\n\nMonitoring cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            time.sleep(args.interval)


if __name__ == '__main__':
    main()

