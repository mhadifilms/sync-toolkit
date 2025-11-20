#!/usr/bin/env python3
"""
Timecode conversion utilities for frame rate conversion.

Handles conversion between 24fps timecodes and 23.976fps (24000/1001) timelines.
"""

# Standard frame rates
FPS_24 = 24.0
FPS_23976 = 24000.0 / 1001.0  # 23.976023... fps


def tc24_to_frames(tc: str, fps: float = FPS_24) -> int:
    """
    Convert HH:MM:SS:FF timecode string to absolute frame index.
    
    Args:
        tc: Timecode string in format HH:MM:SS:FF
        fps: Frame rate (default: 24.0)
    
    Returns:
        Absolute frame index
    
    Raises:
        ValueError: If timecode format is invalid
    
    Example:
        >>> tc24_to_frames("00:00:15:01")
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


def frames_to_seconds(frames: int, fps: float = FPS_23976) -> float:
    """
    Convert frame index to seconds on a given timeline.
    
    Args:
        frames: Frame index
        fps: Target frame rate (default: 23.976fps)
    
    Returns:
        Time in seconds
    
    Example:
        >>> frames_to_seconds(361, FPS_23976)
        15.054...
    """
    return frames / fps


def frames_to_tc(frames: int, fps: float = FPS_24) -> str:
    """
    Convert absolute frame index to HH:MM:SS:FF timecode string.
    
    Args:
        frames: Absolute frame index
        fps: Frame rate (default: 24.0)
    
    Returns:
        Timecode string in format HH:MM:SS:FF
    
    Example:
        >>> frames_to_tc(361)
        '00:00:15:01'
    """
    total_seconds = frames / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frame = int(frames % fps)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frame:02d}"


def convert_tc_24_to_23976(tc_24: str, preserve_frames: bool = False) -> float:
    """
    Convert 24fps timecode to seconds on 23.976fps timeline.
    
    Args:
        tc_24: Timecode string in format HH:MM:SS:FF (24fps)
        preserve_frames: If True, preserves frame numbers. If False, treats as time value.
                        Default: False
    
    Returns:
        Time in seconds on 23.976fps timeline
    
    Raises:
        ValueError: If timecode format is invalid
    
    Example:
        >>> convert_tc_24_to_23976("00:00:15:01")
        15.056...
    """
    if preserve_frames:
        frames = tc24_to_frames(tc_24, FPS_24)
        seconds = frames_to_seconds(frames, FPS_23976)
    else:
        time_24 = tc24_to_time_seconds(tc_24)
        frame_rate_ratio = FPS_23976 / FPS_24
        seconds = time_24 * frame_rate_ratio
    return seconds


def tc24_to_time_seconds(tc: str) -> float:
    """
    Convert 24fps timecode to time in seconds (treating timecode as time value).
    
    This treats the timecode as a time position, not a frame number.
    Converts HH:MM:SS:FF to seconds where FF is fractional seconds.
    
    Args:
        tc: Timecode string in format HH:MM:SS:FF (24fps)
    
    Returns:
        Time in seconds
    
    Example:
        >>> tc24_to_time_seconds("00:00:15:01")
        15.041666...  # 15 seconds + 1/24 second
    """
    try:
        h, m, s, f = map(int, tc.split(":"))
    except ValueError:
        raise ValueError(f"Bad timecode format: {tc!r}. Expected HH:MM:SS:FF")
    
    if f >= FPS_24:
        raise ValueError(f"Frame number {f} exceeds frame rate {FPS_24}")
    
    # Convert to seconds: HH*3600 + MM*60 + SS + frames/24
    total_seconds = (h * 3600) + (m * 60) + s + (f / FPS_24)
    return total_seconds


def convert_tc_range_24_to_23976(start_tc: str, end_tc: str, preserve_frames: bool = False) -> tuple[float, float, float]:
    """
    Convert a range of 24fps timecodes to start/end/duration on 23.976fps timeline.
    
    Args:
        start_tc: Start timecode (24fps)
        end_tc: End timecode (24fps)
        preserve_frames: If True, preserves frame numbers (maps same frame to different time).
                        If False, treats timecodes as time values and scales by frame rate ratio.
                        Default: False (time-based conversion)
    
    Returns:
        Tuple of (start_seconds, end_seconds, duration_seconds) on 23.976fps timeline
    
    Raises:
        ValueError: If timecodes are invalid or end < start
    
    Example:
        >>> convert_tc_range_24_to_23976("00:00:15:01", "00:00:17:07")
        (15.056..., 17.308..., 2.252...)
    """
    if preserve_frames:
        # Original method: preserve frame numbers
        start_frames = tc24_to_frames(start_tc, FPS_24)
        end_frames = tc24_to_frames(end_tc, FPS_24)
        
        if end_frames <= start_frames:
            raise ValueError(f"End timecode {end_tc} must be after start timecode {start_tc}")
        
        start_sec = frames_to_seconds(start_frames, FPS_23976)
        end_sec = frames_to_seconds(end_frames, FPS_23976)
        duration = end_sec - start_sec
    else:
        # Frame-preserving conversion: map same frame number to different time positions
        # This is the correct method when timecodes represent frame numbers, not time positions
        # Convert frame numbers at 24fps to time positions at 23.976fps
        start_frames = tc24_to_frames(start_tc, FPS_24)
        end_frames = tc24_to_frames(end_tc, FPS_24)
        
        if end_frames <= start_frames:
            raise ValueError(f"End timecode {end_tc} must be after start timecode {start_tc}")
        
        # Convert frame numbers to seconds at 23.976fps
        # Same frame number = same content, just different time position
        start_sec = frames_to_seconds(start_frames, FPS_23976)
        end_sec = frames_to_seconds(end_frames, FPS_23976)
        duration = end_sec - start_sec
    
    return start_sec, end_sec, duration


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: timecode.py <timecode> [end_timecode]")
        print("Example: timecode.py 00:00:15:01")
        print("Example: timecode.py 00:00:15:01 00:00:17:07")
        sys.exit(1)
    
    start_tc = sys.argv[1]
    
    try:
        if len(sys.argv) == 2:
            # Single timecode conversion
            start_sec = convert_tc_24_to_23976(start_tc)
            print(f"24fps timecode: {start_tc}")
            print(f"23.976fps time: {start_sec:.6f} seconds")
        else:
            # Range conversion
            end_tc = sys.argv[2]
            start_sec, end_sec, duration = convert_tc_range_24_to_23976(start_tc, end_tc)
            print(f"24fps range: {start_tc} -> {end_tc}")
            print(f"23.976fps: {start_sec:.6f}s -> {end_sec:.6f}s (duration: {duration:.6f}s)")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

