#!/usr/bin/env python3
"""
Create individual video shots from Vub spotting CSV file.

This script reads a CSV file with spotting data (24fps timecodes) and either:
- Directly extracts clips from a master video file (23.976fps), OR
- Generates a bash script that extracts clips (legacy mode)
"""
import csv
import sys
import subprocess
from pathlib import Path

# Import timecode utilities
# Handle symlinks by resolving to actual file first
_script_file = Path(__file__).resolve()
SCRIPT_DIR = _script_file.parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR / "utils"))
from timecode import tc24_to_frames, frames_to_seconds, FPS_23976, FPS_24

# Default configuration
DEFAULT_INPUT_VIDEO = ""
DEFAULT_OUTPUT_DIR = "vub_clips_23976"
DEFAULT_OUT_SCRIPT = "cut_vub_spots.sh"
DEFAULT_SHOW_ID = "SHOW001"
DEFAULT_CSV_PATH = SCRIPT_DIR / "data" / "spotting_template.csv"


def severity_code(event_name: str, description: str) -> str:
    """
    Map Event Name / Description to a short category code:
      VUB, CRIT, EDGE
    """
    text = f"{event_name} {description}".lower()
    if "critical" in text:
        return "CRIT"
    if "edge" in text:
        return "EDGE"
    # Default to base Vub
    return "VUB"


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create individual video shots from Vub spotting CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-video /path/to/master.mov
  %(prog)s --input-video /path/to/master.mov --output-dir ./clips
  %(prog)s --csv custom.csv --input-video /path/to/master.mov
        """
    )
    
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV_PATH),
        help=f"Path to Vub spotting CSV file (default: {DEFAULT_CSV_PATH.name})"
    )
    
    parser.add_argument(
        "--input-video",
        type=str,
        required=True,
        help="Path to input video file (23.976fps master)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for clips (default: {DEFAULT_OUTPUT_DIR})"
    )
    
    parser.add_argument(
        "--script-name",
        type=str,
        default=DEFAULT_OUT_SCRIPT,
        help=f"Name of generated bash script (default: {DEFAULT_OUT_SCRIPT})"
    )
    
    parser.add_argument(
        "--show-id",
        type=str,
        default=DEFAULT_SHOW_ID,
        help=f"Show ID prefix for filenames (default: {DEFAULT_SHOW_ID})"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of entries to process (default: all)"
    )
    
    parser.add_argument(
        "--generate-script",
        action="store_true",
        help="Generate bash script instead of directly cutting videos (legacy mode)"
    )
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    input_video = Path(args.input_video)
    if not input_video.exists():
        print(f"WARNING: INPUT_VIDEO does not exist yet: {input_video}", file=sys.stderr)
        print("Fix INPUT_VIDEO in the script before running the generated .sh file.\n", file=sys.stderr)
    
    out_dir = Path(args.output_dir)
    out_script_path = Path(args.script_name)
    
    # Read spotting data
    try:
        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)
    except Exception as e:
        print(f"ERROR: Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Filter rows that have start/end timecodes
    rows = []
    for i, row in enumerate(raw_rows):
        if args.limit and i >= args.limit:
            break
        start_tc = (row.get("Event Start Time") or "").strip()
        end_tc = (row.get("Event End Time") or "").strip()
        if not start_tc or not end_tc:
            continue
        rows.append(row)
    
    if not rows:
        print("ERROR: No usable rows found with Event Start Time / Event End Time.", file=sys.stderr)
        sys.exit(1)
    
    # Sort by start time (frames at 24fps) to keep order clean
    def sort_key(row):
        try:
            return tc24_to_frames((row.get("Event Start Time") or "").strip())
        except ValueError:
            return 0
    
    rows.sort(key=sort_key)
    
    # If not generating script, cut directly
    if not args.generate_script:
        return cut_videos_directly(args, input_video, out_dir, rows)
    
    # Prepare shell script
    script_lines = []
    script_lines.append("#!/usr/bin/env bash")
    script_lines.append("set -euo pipefail")
    script_lines.append("")
    script_lines.append(f'INPUT="{input_video}"')
    script_lines.append(f'OUTDIR="{out_dir}"')
    script_lines.append("")
    script_lines.append('echo "========================================="')
    script_lines.append('echo "Creating Vub Shots"')
    script_lines.append('echo "========================================="')
    script_lines.append('echo "Input video: $INPUT"')
    script_lines.append('echo "Output dir: $OUTDIR"')
    script_lines.append('echo ""')
    script_lines.append('mkdir -p "$OUTDIR"')
    script_lines.append("")
    
    seen_pairs = set()
    clip_index = 1
    skipped = 0
    
    for row in rows:
        event_id = (row.get("Event Id") or "").strip()
        event_name = (row.get("Event Name") or "").strip()
        desc = (row.get("Description") or "").strip()
        start_tc = (row.get("Event Start Time") or "").strip()
        end_tc = (row.get("Event End Time") or "").strip()
        
        pair_key = (start_tc, end_tc)
        if pair_key in seen_pairs:
            script_lines.append(
                f'echo "Skipping duplicate timecodes {start_tc} -> {end_tc} (Event Id {event_id})" >&2'
            )
            skipped += 1
            continue
        seen_pairs.add(pair_key)
        
        # Convert timecodes to seconds using frame-accurate method
        try:
            def tc_to_seconds_frame_accurate(tc, fps=FPS_23976):
                h, m, s, f = map(int, tc.split(":"))
                # Convert to absolute frame number
                total_frames = int(((h * 3600) + (m * 60) + s) * fps + f)
                # Convert frame number to seconds
                return total_frames / fps
            
            start_sec = tc_to_seconds_frame_accurate(start_tc, FPS_23976)
            end_sec = tc_to_seconds_frame_accurate(end_tc, FPS_23976)
            duration = end_sec - start_sec
        except ValueError as e:
            script_lines.append(f'echo "Skipping row with bad timecode: {e}" >&2')
            skipped += 1
            continue
        
        # Format with enough precision for frame accuracy
        start_str = f"{start_sec:.6f}"
        dur_str = f"{duration:.6f}"
        
        # Build label
        cat_code = severity_code(event_name, desc)
        clip_num = f"{clip_index:04d}"
        start_tc_safe = start_tc.replace(":", "-")
        end_tc_safe = end_tc.replace(":", "-")
        filename = f"{args.show_id}_{clip_num}_{cat_code}_{start_tc_safe}_{end_tc_safe}.mov"
        
        # Debug echo
        script_lines.append(
            f'echo "[{clip_index}/{len(rows)}] Clip {clip_num} [{cat_code}] {start_tc} -> {end_tc} '
            f'| {start_str}s for {dur_str}s"'
        )
        
        # ffmpeg command (copy, no re-encode) with explicit audio mapping
        # Using -ss before -i is fine for ProRes (intra); this will be fast and frame-accurate.
        script_lines.append(
            f'ffmpeg -hide_banner -loglevel error -y -ss {start_str} -i "$INPUT" -t {dur_str} -map 0:v -map 0:a -c:v copy -c:a copy "$OUTDIR/{filename}"'
        )
        script_lines.append("")
        
        clip_index += 1
    
    # Add summary
    script_lines.append('echo ""')
    script_lines.append('echo "========================================="')
    script_lines.append(f'echo "Summary: {clip_index - 1} clips created, {skipped} skipped"')
    script_lines.append('echo "========================================="')
    
    # Write script file
    try:
        out_script_path.write_text("\n".join(script_lines), encoding="utf-8")
        out_script_path.chmod(0o755)
    except Exception as e:
        print(f"ERROR: Failed to write script: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ Generated script: {out_script_path}")
    print(f"✓ It will write {clip_index - 1} clips into: {out_dir}")
    if skipped > 0:
        print(f"⚠ Skipped {skipped} duplicate/invalid entries")
    print("\nRun it with:\n")
    print(f"    ./{out_script_path.name}\n")


def cut_videos_directly(args, input_video: Path, output_dir: Path, rows: list):
    """Directly cut videos instead of generating a script."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading CSV and processing {len(rows)} entries...")
    print(f"Input video: {input_video}")
    print(f"Output directory: {output_dir}")
    print()
    
    successful = 0
    failed = 0
    seen_pairs = set()
    clip_index = 1
    
    for row in rows:
        event_id = (row.get("Event Id") or "").strip()
        event_name = (row.get("Event Name") or "").strip()
        desc = (row.get("Description") or "").strip()
        start_tc = (row.get("Event Start Time") or "").strip()
        end_tc = (row.get("Event End Time") or "").strip()
        
        pair_key = (start_tc, end_tc)
        if pair_key in seen_pairs:
            print(f"Skipping duplicate timecodes {start_tc} -> {end_tc} (Event Id {event_id})", file=sys.stderr)
            failed += 1
            continue
        seen_pairs.add(pair_key)
        
        try:
            # Parse timecode directly - no FPS conversion, just use timecodes as-is
            # Timecode format: HH:MM:SS:FF
            # Convert directly to seconds: HH*3600 + MM*60 + SS + FF/fps
            # We need to detect video FPS or use a standard approach
            # For now, parse timecode and convert to seconds assuming the timecode frame rate matches video
            def tc_to_seconds(tc):
                """Convert timecode HH:MM:SS:FF to seconds."""
                h, m, s, f = map(int, tc.split(":"))
                # Parse as time: hours, minutes, seconds, and frames
                # Convert frames to seconds using 24fps (standard for timecodes)
                # This is just parsing the timecode value, not doing conversion
                total_seconds = (h * 3600) + (m * 60) + s + (f / 24.0)
                return total_seconds
            
            start_sec = tc_to_seconds(start_tc)
            end_sec = tc_to_seconds(end_tc)
            duration = end_sec - start_sec
            
            # For frame-accurate cutting, we also need frame numbers
            # Parse timecode to get frame number at 24fps (timecode standard)
            def tc_to_frames_24(tc):
                """Convert timecode to frame number at 24fps."""
                h, m, s, f = map(int, tc.split(":"))
                return int(((h * 3600) + (m * 60) + s) * 24 + f)
            
            start_frame = tc_to_frames_24(start_tc)
            end_frame = tc_to_frames_24(end_tc)
            duration_frames = end_frame - start_frame
        except ValueError as e:
            print(f"Skipping row with bad timecode: {e}", file=sys.stderr)
            failed += 1
            continue
        
        # Get category code
        cat_code = severity_code(event_name, desc)
        
        # Build filename: SHOW001_0001_VUB_00-00-15-01_00-00-17-07.mov
        clip_num = f"{clip_index:04d}"
        start_tc_safe = start_tc.replace(":", "-")
        end_tc_safe = end_tc.replace(":", "-")
        filename = f"{args.show_id}_{clip_num}_{cat_code}_{start_tc_safe}_{end_tc_safe}.mov"
        output_file = output_dir / filename
        
        print(f"[{clip_index}/{len(rows)}] Cutting {start_tc} -> {end_tc} ({duration:.2f}s, frames {start_frame}-{end_frame-1}) [{cat_code}] -> {filename}")
        
        # Run ffmpeg with frame-accurate extraction using copy mode
        # End timecode is EXCLUSIVE - we want frames start_frame to end_frame-1 (inclusive)
        # For ProRes (all frames are keyframes), -ss before -i is fast and frame-accurate
        
        # For 24fps video, use 24fps for frame calculations
        video_fps = 24.0  # Original video is 24fps
        
        # Calculate exact times from frame numbers at video FPS
        # Start exactly at start_frame boundary
        # For ProRes, -ss before -i seeks to exact frame boundaries
        start_sec_precise = start_frame / video_fps
        
        end_frame_inclusive = end_frame - 1
        # Duration should capture frames start_frame through end_frame_inclusive
        # That's exactly (end_frame - start_frame) frames
        duration_exact = (end_frame_inclusive - start_frame + 1) / video_fps
        
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-ss", f"{start_sec_precise:.9f}",  # Seek before input (fast and accurate for ProRes)
            "-i", str(input_video),
            "-t", f"{duration_exact:.9f}",  # Exact duration
            "-map", "0:v",  # Map video stream
            "-map", "0:a",  # Map audio stream
            "-c:v", "copy",  # Copy video codec (no re-encoding)
            "-c:a", "copy",  # Copy audio codec (no re-encoding)
            str(output_file)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                successful += 1
            else:
                print(f"  ERROR: {result.stderr}", file=sys.stderr)
                failed += 1
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            failed += 1
        
        clip_index += 1
    
    print()
    print("=" * 50)
    print(f"Summary: {successful} successful, {failed} failed")
    print(f"Output directory: {output_dir}")
    print("=" * 50)


if __name__ == "__main__":
    main()

