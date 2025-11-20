#!/usr/bin/env python3
"""
Convert CSV timecodes from 24fps to 23.976fps.
"""
import csv
import sys
from pathlib import Path

# Import timecode utilities
_script_file = Path(__file__).resolve()
SCRIPT_DIR = _script_file.parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.timecode import tc24_to_frames, frames_to_tc, FPS_24, FPS_23976

def convert_tc_24_to_23976(tc_24: str) -> str:
    """
    Convert a 24fps timecode to 23.976fps timecode.
    Preserves frame numbers - same frame number, different time position.
    """
    # Convert to frame number at 24fps
    frames = tc24_to_frames(tc_24, FPS_24)
    
    # Convert frame number to 23.976fps timecode
    tc_23976 = frames_to_tc(frames, FPS_23976)
    
    return tc_23976

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert CSV timecodes from 24fps to 23.976fps"
    )
    
    parser.add_argument(
        "--input-csv",
        type=str,
        required=True,
        help="Input CSV file with 24fps timecodes"
    )
    
    parser.add_argument(
        "--output-csv",
        type=str,
        required=True,
        help="Output CSV file with 23.976fps timecodes"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    
    if not input_path.exists():
        print(f"ERROR: Input CSV not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading: {input_path}")
    print(f"Writing: {output_path}")
    
    # Read and convert
    rows = []
    with input_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # Convert Event Start Time and Event End Time
            start_tc_24 = row.get("Event Start Time", "").strip()
            end_tc_24 = row.get("Event End Time", "").strip()
            
            if start_tc_24 and end_tc_24:
                try:
                    start_tc_23976 = convert_tc_24_to_23976(start_tc_24)
                    end_tc_23976 = convert_tc_24_to_23976(end_tc_24)
                    
                    row["Event Start Time"] = start_tc_23976
                    row["Event End Time"] = end_tc_23976
                    
                    # Also update Event Duration if present
                    if "Event Duration" in row and row["Event Duration"]:
                        # Calculate duration from converted timecodes
                        start_frames = tc24_to_frames(start_tc_23976, FPS_23976)
                        end_frames = tc24_to_frames(end_tc_23976, FPS_23976)
                        duration_frames = end_frames - start_frames
                        duration_tc = frames_to_tc(duration_frames, FPS_23976)
                        row["Event Duration"] = duration_tc
                except ValueError as e:
                    print(f"Warning: Skipping row with invalid timecode: {e}", file=sys.stderr)
                    continue
            
            rows.append(row)
    
    # Write converted CSV
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Converted {len(rows)} rows")
    print(f"✓ Output written to: {output_path}")

if __name__ == "__main__":
    main()

