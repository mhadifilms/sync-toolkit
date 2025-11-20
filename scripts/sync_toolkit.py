#!/usr/bin/env python3
"""
Sync Toolkit - Unified CLI for sync. workflows

A comprehensive toolkit for bulk lipsync processing with Sync.so API.
"""
import sys
import argparse
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from utils.config import get_config_manager
from utils.common import print_section, prompt_choice, normalize_path


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Sync Toolkit - Unified CLI for Sync.so workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s detect-scenes                    # Detect and split scenes
  %(prog)s upload ./Scenes                   # Upload files to storage
  %(prog)s batch --manifest urls.txt         # Run batch lipsync processing
  %(prog)s process-csv --csv input.csv       # Process CSV with S3 URLs
  %(prog)s config                             # Configure credentials
  
For first-time setup, run: python scripts/setup.py
For help, see: USER_GUIDE.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Detect scenes command
    detect_parser = subparsers.add_parser('detect-scenes', help='Detect and split video scenes')
    detect_parser.add_argument('--video', type=str, help='Input video file')
    detect_parser.add_argument('--audio', type=str, help='Input audio file (optional)')
    detect_parser.add_argument('--output', type=str, help='Output directory')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload files to storage')
    upload_parser.add_argument('path', nargs='?', help='File or directory to upload')
    upload_parser.add_argument('dest', nargs='?', help='Storage destination (Supabase or S3 path)')
    upload_parser.add_argument('--storage', choices=['supabase', 's3'], default='supabase',
                              help='Storage backend (default: supabase)')
    upload_parser.add_argument('--bucket', type=str, help='Storage bucket name')
    upload_parser.add_argument('--concurrency', type=int, default=4, help='Parallel uploads')
    
    # S3 upload command
    s3_upload_parser = subparsers.add_parser('s3-upload', help='Upload files to S3')
    s3_upload_parser.add_argument('input_dir', nargs='?', help='Directory to upload')
    s3_upload_parser.add_argument('s3_dest', nargs='?', help='S3 destination (s3://bucket/path/)')
    s3_upload_parser.add_argument('--parallel', '-p', type=int, default=8, help='Parallel uploads')
    s3_upload_parser.add_argument('--pattern', default='*', help='File pattern')
    s3_upload_parser.add_argument('--preserve-structure', action='store_true', help='Preserve directory structure')
    s3_upload_parser.add_argument('--skip-existing', '-s', action='store_true', help='Skip existing files')
    s3_upload_parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    s3_upload_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # S3 download command
    s3_download_parser = subparsers.add_parser('s3-download', help='Download files from S3')
    s3_download_parser.add_argument('source', nargs='?', help='S3 source or input file')
    s3_download_parser.add_argument('dest', nargs='?', help='Local destination')
    s3_download_parser.add_argument('--mode', '-m', choices=['sync', 'list', 'json'], default='sync', help='Download mode')
    s3_download_parser.add_argument('--parallel', '-p', type=int, default=10, help='Parallel downloads')
    s3_download_parser.add_argument('--suffix', '-s', default='v1', help='Suffix for numbered files')
    s3_download_parser.add_argument('--name', '-n', help='Common name prefix')
    s3_download_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    s3_download_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor S3 upload progress')
    monitor_parser.add_argument('--s3-path', '-s', required=True, help='S3 path to monitor')
    monitor_parser.add_argument('--expected', '-e', type=int, required=True, help='Expected file count')
    monitor_parser.add_argument('--local-dir', '-l', help='Local directory to compare')
    monitor_parser.add_argument('--interval', '-i', type=int, default=180, help='Check interval (seconds)')
    monitor_parser.add_argument('--pattern', '-p', default=r'(_bounced\.mov|_bounced\.wav)', help='File pattern')
    
    # Batch processing command
    batch_parser = subparsers.add_parser('batch', help='Run batch lipsync processing')
    batch_parser.add_argument('--manifest', type=str, help='URL manifest file')
    batch_parser.add_argument('--start', type=int, default=1, help='Start index')
    batch_parser.add_argument('--end', type=int, help='End index')
    batch_parser.add_argument('--max-workers', type=int, default=15, help='Max parallel jobs')
    batch_parser.add_argument('--output', type=str, default='./outputs', help='Output directory')
    
    # CSV processing command
    csv_parser = subparsers.add_parser('process-csv', help='Process CSV file with S3 URLs')
    csv_parser.add_argument('--csv', type=str, required=True, help='CSV file path')
    csv_parser.add_argument('--limit', type=int, help='Limit number of rows')
    csv_parser.add_argument('--test', action='store_true', help='Test mode (process first row only)')
    
    # Face grouping command (unified - can group and organize)
    face_parser = subparsers.add_parser('group-faces', help='Group video clips by detected faces and optionally organize')
    face_parser.add_argument('--input-dir', type=str, help='Directory with video clips')
    face_parser.add_argument('--clips', nargs='+', help='List of video clip paths')
    face_parser.add_argument('--output', type=str, default='face_groups.json', help='Output JSON file')
    face_parser.add_argument('--organize', action='store_true', help='Organize clips into folders after grouping')
    face_parser.add_argument('--organize-output', type=str, help='Output directory for organized clips')
    face_parser.add_argument('--move', action='store_true', help='Move files instead of copying when organizing')
    face_parser.add_argument('--symlink', action='store_true', help='Create symlinks instead of copying/moving')
    face_parser.add_argument('--eps', type=float, default=0.35, help='DBSCAN eps parameter')
    face_parser.add_argument('--min-samples', type=int, default=2, help='DBSCAN min_samples')
    face_parser.add_argument('--num-frames', type=int, default=10, help='Frames to sample per video')
    
    # Create shots command
    shots_parser = subparsers.add_parser('create-shots', help='Create video shots from CSV')
    shots_parser.add_argument('--csv', type=str, help='CSV file with spotting data')
    shots_parser.add_argument('--video', type=str, required=True, help='Input video file')
    shots_parser.add_argument('--output', type=str, help='Output directory')
    
    # Video processing commands
    chunk_parser = subparsers.add_parser('chunk', help='Create video/audio chunks from cuts file')
    chunk_parser.add_argument('input_video', nargs='?', help='Input video file')
    chunk_parser.add_argument('input_audio', nargs='?', help='Input audio file (optional)')
    chunk_parser.add_argument('cuts_file', nargs='?', help='Cuts file (default: data/cuts.txt)')
    chunk_parser.add_argument('output_dir', nargs='?', help='Output directory')
    chunk_parser.add_argument('s3_dest', nargs='?', help='S3 destination (optional)')
    chunk_parser.add_argument('--no-upload', '-n', action='store_true', help='Disable S3 upload')
    chunk_parser.add_argument('--audio-only', '-a', action='store_true', help='Audio-only mode')
    chunk_parser.add_argument('--video-only', '-v', action='store_true', help='Video-only mode')
    
    bounce_parser = subparsers.add_parser('bounce', help='Create bounced versions of videos')
    bounce_parser.add_argument('input_dir', nargs='+', help='Input directory(ies)')
    bounce_parser.add_argument('--output', '-o', help='Output directory')
    bounce_parser.add_argument('--recursive', '-r', action='store_true', help='Process recursively')
    bounce_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing')
    bounce_parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    bounce_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    extract_audio_parser = subparsers.add_parser('extract-audio', help='Extract audio from videos')
    extract_audio_parser.add_argument('directory', help='Directory containing videos')
    extract_audio_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing')
    extract_audio_parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    extract_audio_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    rename_parser = subparsers.add_parser('rename', help='Rename files sequentially')
    rename_parser.add_argument('directory', help='Directory containing files')
    rename_parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run')
    rename_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Convert timecodes command
    convert_tc_parser = subparsers.add_parser('convert-timecodes', help='Convert timecodes between frame rates')
    convert_tc_parser.add_argument('--input-csv', type=str, help='Input CSV file with timecodes')
    convert_tc_parser.add_argument('--output-csv', type=str, help='Output CSV file with converted timecodes')
    convert_tc_parser.add_argument('--timecode', type=str, help='Single timecode to convert (format: HH:MM:SS:FF)')
    convert_tc_parser.add_argument('--source-fps', type=str, required=True, help='Source frame rate (e.g., 24, 23.976, 25, 29.97, 30, 50, 59.94, 60)')
    convert_tc_parser.add_argument('--target-fps', type=str, required=True, help='Target frame rate (e.g., 24, 23.976, 25, 29.97, 30, 50, 59.94, 60)')
    convert_tc_parser.add_argument('--start-column', type=str, default='Event Start Time', help='CSV column name for start timecode')
    convert_tc_parser.add_argument('--end-column', type=str, default='Event End Time', help='CSV column name for end timecode')
    convert_tc_parser.add_argument('--duration-column', type=str, default='Event Duration', help='CSV column name for duration')
    convert_tc_parser.add_argument('--preserve-time', action='store_true', help='Preserve time values instead of frame numbers')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure credentials')
    config_parser.add_argument('--clear', action='store_true', help='Clear stored credentials')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to appropriate handler
    try:
        if args.command == 'detect-scenes':
            # detect_scenes.py handles its own prompts, so we can call it directly
            from video.detect_scenes import main as detect_main
            detect_main()
        elif args.command == 'upload':
            # Pass sys.argv to maintain argument parsing
            import sys
            original_argv = sys.argv
            sys.argv = ['sb_upload.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from transfer.sb_upload import main as upload_main
            upload_main()
            sys.argv = original_argv
        elif args.command == 's3-upload':
            import sys
            original_argv = sys.argv
            sys.argv = ['s3_upload.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from transfer.s3_upload import main as s3_upload_main
            s3_upload_main()
            sys.argv = original_argv
        elif args.command == 's3-download':
            import sys
            original_argv = sys.argv
            sys.argv = ['s3_download.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from transfer.s3_download import main as s3_download_main
            s3_download_main()
            sys.argv = original_argv
        elif args.command == 'monitor':
            import sys
            original_argv = sys.argv
            sys.argv = ['s3_monitor.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from monitor.s3_monitor import main as monitor_main
            monitor_main()
            sys.argv = original_argv
        elif args.command == 'batch':
            import sys
            original_argv = sys.argv
            sys.argv = ['lipsync_batch.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from api.lipsync_batch import main as batch_main
            batch_main()
            sys.argv = original_argv
        elif args.command == 'process-csv':
            import sys
            original_argv = sys.argv
            sys.argv = ['s3_csv.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from api.s3_csv import main as csv_main
            csv_main()
            sys.argv = original_argv
        elif args.command == 'group-faces':
            import sys
            original_argv = sys.argv
            sys.argv = ['group_by_face.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from video.group_by_face import main as face_main
            face_main()
            sys.argv = original_argv
        elif args.command == 'create-shots':
            import sys
            original_argv = sys.argv
            sys.argv = ['create_shots.py'] + (original_argv[2:] if len(original_argv) > 2 else [])
            from video.create_shots import main as shots_main
            shots_main()
            sys.argv = original_argv
        elif args.command == 'chunk':
            import subprocess
            import sys
            cmd = ['bash', str(SCRIPT_DIR / 'video' / 'chunk.sh')]
            if args.no_upload:
                cmd.append('--no-upload')
            if args.audio_only:
                cmd.append('--audio-only')
            if args.video_only:
                cmd.append('--video-only')
            if args.input_video:
                cmd.append(args.input_video)
            if args.input_audio:
                cmd.append(args.input_audio)
            if args.cuts_file:
                cmd.append(args.cuts_file)
            if args.output_dir:
                cmd.append(args.output_dir)
            if args.s3_dest:
                cmd.append(args.s3_dest)
            subprocess.run(cmd)
        elif args.command == 'bounce':
            import subprocess
            cmd = ['bash', str(SCRIPT_DIR / 'video' / 'bounce.sh')]
            if args.output:
                cmd.extend(['--output', args.output])
            if args.recursive:
                cmd.append('--recursive')
            if args.force:
                cmd.append('--force')
            if args.dry_run:
                cmd.append('--dry-run')
            if args.verbose:
                cmd.append('--verbose')
            cmd.extend(args.input_dir)
            subprocess.run(cmd)
        elif args.command == 'extract-audio':
            import subprocess
            cmd = ['bash', str(SCRIPT_DIR / 'video' / 'extract_audio.sh')]
            if args.force:
                cmd.append('--force')
            if args.dry_run:
                cmd.append('--dry-run')
            if args.verbose:
                cmd.append('--verbose')
            cmd.append(args.directory)
            subprocess.run(cmd)
        elif args.command == 'rename':
            import subprocess
            cmd = ['bash', str(SCRIPT_DIR / 'utils' / 'rename.sh')]
            if args.dry_run:
                cmd.append('--dry-run')
            if args.verbose:
                cmd.append('--verbose')
            cmd.append(args.directory)
            subprocess.run(cmd)
        elif args.command == 'convert-timecodes':
            import sys
            original_argv = sys.argv
            # Build argument list
            cmd_args = ['timecode.py']
            if args.input_csv:
                cmd_args.extend(['--input-csv', args.input_csv])
            if args.output_csv:
                cmd_args.extend(['--output-csv', args.output_csv])
            if args.timecode:
                cmd_args.extend(['--timecode', args.timecode])
            cmd_args.extend(['--source-fps', args.source_fps])
            cmd_args.extend(['--target-fps', args.target_fps])
            if args.start_column:
                cmd_args.extend(['--start-column', args.start_column])
            if args.end_column:
                cmd_args.extend(['--end-column', args.end_column])
            if args.duration_column:
                cmd_args.extend(['--duration-column', args.duration_column])
            if args.preserve_time:
                cmd_args.append('--preserve-time')
            sys.argv = cmd_args
            from utils.timecode import main as convert_tc_main
            convert_tc_main()
            sys.argv = original_argv
        elif args.command == 'config':
            config_manager = get_config_manager()
            if args.clear:
                config_manager.clear_credentials()
            else:
                print_section("Sync Toolkit Configuration")
                print("Configuration is stored at:", config_manager.CONFIG_FILE)
                print("\nCredentials will be prompted when needed.")
                print("Use --clear to remove stored credentials.")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

