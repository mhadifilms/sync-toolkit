#!/usr/bin/env python3
"""
Timecode conversion utilities for frame rate conversion.

Supports conversion between any frame rates, with common presets for standard rates.
"""
import csv
import sys
import argparse
from pathlib import Path
from typing import Optional

# Common frame rate presets
FPS_23_976 = 24000.0 / 1001.0  # 23.976023... fps (NTSC film)
FPS_24 = 24.0                   # 24 fps (film standard)
FPS_25 = 25.0                   # 25 fps (PAL)
FPS_29_97 = 30000.0 / 1001.0   # 29.97 fps (NTSC video)
FPS_30 = 30.0                   # 30 fps
FPS_50 = 50.0                   # 50 fps (PAL)
FPS_59_94 = 60000.0 / 1001.0   # 59.94 fps (NTSC)
FPS_60 = 60.0                   # 60 fps

# Legacy aliases for backward compatibility
FPS_23976 = FPS_23_976


def parse_fps(fps_input: str) -> float:
    """
    Parse frame rate from string input.
    Supports numeric values and preset names.
    
    Args:
        fps_input: Frame rate as number (e.g., "24", "23.976") or preset name (e.g., "24fps", "ntsc")
    
    Returns:
        Frame rate as float
    
    Raises:
        ValueError: If frame rate cannot be parsed
    
    Examples:
        >>> parse_fps("24")
        24.0
        >>> parse_fps("23.976")
        23.976023...
        >>> parse_fps("ntsc")
        29.970029...
    """
    fps_input = fps_input.lower().strip()
    
    # Preset names
    presets = {
        "23.976": FPS_23_976,
        "23976": FPS_23_976,
        "24": FPS_24,
        "24fps": FPS_24,
        "25": FPS_25,
        "25fps": FPS_25,
        "29.97": FPS_29_97,
        "2997": FPS_29_97,
        "ntsc": FPS_29_97,
        "30": FPS_30,
        "30fps": FPS_30,
        "50": FPS_50,
        "50fps": FPS_50,
        "59.94": FPS_59_94,
        "5994": FPS_59_94,
        "60": FPS_60,
        "60fps": FPS_60,
    }
    
    if fps_input in presets:
        return presets[fps_input]
    
    # Try parsing as float
    try:
        return float(fps_input)
    except ValueError:
        raise ValueError(f"Invalid frame rate: {fps_input}. Use a number or preset name (24, 23.976, 25, 29.97, 30, 50, 59.94, 60)")


def timecode_to_frames(tc: str, fps: float) -> int:
    """
    Convert HH:MM:SS:FF timecode string to absolute frame index.
    
    Args:
        tc: Timecode string in format HH:MM:SS:FF
        fps: Frame rate
    
    Returns:
        Absolute frame index
    
    Raises:
        ValueError: If timecode format is invalid
    
    Example:
        >>> timecode_to_frames("00:00:15:01", 24.0)
        361
    """
    try:
        h, m, s, f = map(int, tc.split(":"))
    except ValueError:
        raise ValueError(f"Bad timecode format: {tc!r}. Expected HH:MM:SS:FF")
    
    if f >= fps:
        raise ValueError(f"Frame number {f} exceeds frame rate {fps}")
    
    total_frames = int(((h * 3600) + (m * 60) + s) * fps + f)
    return total_frames


def frames_to_timecode(frames: int, fps: float) -> str:
    """
    Convert absolute frame index to HH:MM:SS:FF timecode string.
    
    Args:
        frames: Absolute frame index
        fps: Frame rate
    
    Returns:
        Timecode string in format HH:MM:SS:FF
    
    Example:
        >>> frames_to_timecode(361, 24.0)
        '00:00:15:01'
    """
    total_seconds = frames / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frame = int(frames % fps)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame:02d}"


def frames_to_seconds(frames: int, fps: float) -> float:
    """
    Convert frame index to seconds on a given timeline.
    
    Args:
        frames: Frame index
        fps: Target frame rate
    
    Returns:
        Time in seconds
    
    Example:
        >>> frames_to_seconds(361, 23.976)
        15.054...
    """
    return frames / fps


def convert_timecode(tc: str, source_fps: float, target_fps: float, preserve_frames: bool = True) -> str:
    """
    Convert timecode from one frame rate to another.
    
    Args:
        tc: Timecode string in format HH:MM:SS:FF
        source_fps: Source frame rate
        target_fps: Target frame rate
        preserve_frames: If True, preserves frame numbers (same frame, different time).
                        If False, treats timecode as time value and scales by frame rate ratio.
                        Default: True (frame-preserving conversion)
    
    Returns:
        Converted timecode string
    
    Example:
        >>> convert_timecode("00:00:15:01", 24.0, 23.976)
        '00:00:15:01'  # Same frame number, different time position
    """
    if preserve_frames:
        # Frame-preserving: same frame number, different time position
        frames = timecode_to_frames(tc, source_fps)
        return frames_to_timecode(frames, target_fps)
    else:
        # Time-preserving: scale by frame rate ratio
        frames = timecode_to_frames(tc, source_fps)
        time_seconds = frames_to_seconds(frames, source_fps)
        target_frames = int(time_seconds * target_fps)
        return frames_to_timecode(target_frames, target_fps)


def convert_csv_timecodes(
    input_csv: Path,
    output_csv: Path,
    source_fps: float,
    target_fps: float,
    start_column: str = "Event Start Time",
    end_column: str = "Event End Time",
    duration_column: Optional[str] = "Event Duration",
    preserve_frames: bool = True
) -> int:
    """
    Convert timecodes in a CSV file from one frame rate to another.
    
    Args:
        input_csv: Input CSV file path
        output_csv: Output CSV file path
        source_fps: Source frame rate
        target_fps: Target frame rate
        start_column: Column name for start timecode
        end_column: Column name for end timecode
        duration_column: Column name for duration (optional, will be recalculated)
        preserve_frames: If True, preserves frame numbers. Default: True
    
    Returns:
        Number of rows converted
    """
    rows = []
    converted_count = 0
    
    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        if not fieldnames:
            raise ValueError("CSV file has no headers")
        
        for row in reader:
            start_tc = row.get(start_column, "").strip()
            end_tc = row.get(end_column, "").strip()
            
            if start_tc and end_tc:
                try:
                    # Convert timecodes
                    start_tc_converted = convert_timecode(start_tc, source_fps, target_fps, preserve_frames)
                    end_tc_converted = convert_timecode(end_tc, source_fps, target_fps, preserve_frames)
                    
                    row[start_column] = start_tc_converted
                    row[end_column] = end_tc_converted
                    
                    # Recalculate duration if column exists
                    if duration_column and duration_column in row:
                        start_frames = timecode_to_frames(start_tc_converted, target_fps)
                        end_frames = timecode_to_frames(end_tc_converted, target_fps)
                        duration_frames = end_frames - start_frames
                        row[duration_column] = frames_to_timecode(duration_frames, target_fps)
                    
                    converted_count += 1
                except ValueError as e:
                    print(f"Warning: Skipping row with invalid timecode: {e}", file=sys.stderr)
                    continue
            
            rows.append(row)
    
    # Write converted CSV
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    return converted_count


# Legacy function names for backward compatibility
def tc24_to_frames(tc: str, fps: float = FPS_24) -> int:
    """Legacy alias for timecode_to_frames"""
    return timecode_to_frames(tc, fps)


def frames_to_tc(frames: int, fps: float = FPS_24) -> str:
    """Legacy alias for frames_to_timecode"""
    return frames_to_timecode(frames, fps)


def convert_tc_24_to_23976(tc_24: str, preserve_frames: bool = True) -> str:
    """Legacy function for 24fps to 23.976fps conversion"""
    return convert_timecode(tc_24, FPS_24, FPS_23_976, preserve_frames)


def main():
    """CLI entry point for timecode conversion"""
    parser = argparse.ArgumentParser(
        description="Convert timecodes between frame rates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert CSV timecodes from 24fps to 23.976fps
  %(prog)s --input-csv input.csv --output-csv output.csv --source-fps 24 --target-fps 23.976
  
  # Convert single timecode
  %(prog)s --timecode "00:00:15:01" --source-fps 24 --target-fps 23.976
  
  # Use preset names
  %(prog)s --input-csv input.csv --output-csv output.csv --source-fps 24fps --target-fps ntsc
        """
    )
    
    parser.add_argument(
        "--input-csv",
        type=str,
        help="Input CSV file with timecodes"
    )
    
    parser.add_argument(
        "--output-csv",
        type=str,
        help="Output CSV file with converted timecodes"
    )
    
    parser.add_argument(
        "--timecode",
        type=str,
        help="Single timecode to convert (format: HH:MM:SS:FF)"
    )
    
    parser.add_argument(
        "--source-fps",
        type=str,
        required=True,
        help="Source frame rate (number or preset: 24, 23.976, 25, 29.97, 30, 50, 59.94, 60)"
    )
    
    parser.add_argument(
        "--target-fps",
        type=str,
        required=True,
        help="Target frame rate (number or preset: 24, 23.976, 25, 29.97, 30, 50, 59.94, 60)"
    )
    
    parser.add_argument(
        "--start-column",
        type=str,
        default="Event Start Time",
        help="CSV column name for start timecode (default: Event Start Time)"
    )
    
    parser.add_argument(
        "--end-column",
        type=str,
        default="Event End Time",
        help="CSV column name for end timecode (default: Event End Time)"
    )
    
    parser.add_argument(
        "--duration-column",
        type=str,
        default="Event Duration",
        help="CSV column name for duration (default: Event Duration, set to empty to skip)"
    )
    
    parser.add_argument(
        "--preserve-frames",
        action="store_true",
        default=True,
        help="Preserve frame numbers (same frame, different time) - default"
    )
    
    parser.add_argument(
        "--preserve-time",
        action="store_true",
        help="Preserve time values (scale by frame rate ratio) instead of preserving frames"
    )
    
    args = parser.parse_args()
    
    # Parse frame rates
    try:
        source_fps = parse_fps(args.source_fps)
        target_fps = parse_fps(args.target_fps)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    preserve_frames = args.preserve_frames and not args.preserve_time
    
    # Single timecode conversion
    if args.timecode:
        try:
            converted = convert_timecode(args.timecode, source_fps, target_fps, preserve_frames)
            print(f"Source ({source_fps} fps): {args.timecode}")
            print(f"Target ({target_fps} fps): {converted}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # CSV conversion
    if args.input_csv and args.output_csv:
        input_path = Path(args.input_csv)
        output_path = Path(args.output_csv)
        
        if not input_path.exists():
            print(f"Error: Input CSV not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Reading: {input_path}")
        print(f"Writing: {output_path}")
        print(f"Converting from {source_fps} fps to {target_fps} fps")
        print(f"Mode: {'Frame-preserving' if preserve_frames else 'Time-preserving'}")
        
        try:
            duration_col = args.duration_column if args.duration_column else None
            converted_count = convert_csv_timecodes(
                input_path,
                output_path,
                source_fps,
                target_fps,
                args.start_column,
                args.end_column,
                duration_col,
                preserve_frames
            )
            
            print(f"✓ Converted {converted_count} rows")
            print(f"✓ Output written to: {output_path}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
    
    # No action specified
    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
