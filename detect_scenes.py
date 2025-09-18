#!/usr/bin/env python3
import os, re, sys, math, csv, shlex, subprocess
from pathlib import Path

# ------- Tunables -------
PSD_THRESHOLD = 22.0        # PySceneDetect sensitivity (lower = more cuts). Try 18–28.
PSD_MIN_FRAMES = 8          # Min scene length in frames (~0.33s @24fps)
FFMPEG_SCENE = 0.30         # ffmpeg scene threshold (lower = more cuts). Try 0.25–0.45
MIN_GAP_SEC = 0.33          # Merge near-duplicate cuts (≈8 frames @24fps)
MAX_OUTPUTS = 10000         # Safety guard

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr

def need(tool):
    rc,_,_ = run([tool, "-version"])
    if rc != 0:
        print(f"{tool} not found on PATH. Install it (e.g., brew install ffmpeg).", file=sys.stderr)
        sys.exit(1)

def norm_path(user_input: str) -> str:
    """
    Accepts raw input from paste/drag-and-drop.
    Supports:
      - Backslash-escaped spaces (Finder → Terminal):   /path/with\ spaces/file.mov
      - Quoted paths:                                   "/path/with spaces/file.mov"
    """
    s = (user_input or "").strip()
    # If there are backslash-escapes or quotes, shlex.split resolves them.
    try:
        parts = shlex.split(s)
        if len(parts) >= 1:
            s = parts[0]
    except Exception:
        # Fallback: unescape spaces only
        s = s.replace(r"\ ", " ")
    s = os.path.expanduser(s)
    s = os.path.abspath(s)
    return s

def ffprobe_duration(path):
    rc,out,err = run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=noprint_wrappers=1:nokey=1", path])
    if rc != 0:
        raise RuntimeError(err)
    d = float(out.strip())
    if not math.isfinite(d) or d <= 0:
        raise RuntimeError(f"Bad duration from ffprobe: {out!r}")
    return d

def detect_cuts_ffmpeg(path, thr):
    filt = f"select='gt(scene\\,{thr})',showinfo"
    rc,out,err = run(["ffmpeg","-hide_banner","-i",path,"-filter_complex",filt,"-an","-f","null","-"])
    pts = []
    for line in err.splitlines():
        if "showinfo" in line and "pts_time:" in line:
            m = re.search(r"pts_time:([0-9]+(?:\.[0-9]+)?)", line)
            if m:
                t = float(m.group(1))
                if t >= 0:
                    pts.append(t)
    return sorted(set(round(t,6) for t in pts))

def detect_cuts_pyscenedetect(path, thr, min_frames):
    """Modern PySceneDetect API (no deprecated VideoManager)."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector
    except ImportError:
        print("PySceneDetect not installed; skipping that pass. Run: pip install scenedetect", file=sys.stderr)
        return []
    video = open_video(path)
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=thr, min_scene_len=min_frames))
    sm.detect_scenes(video=video)
    scenes = sm.get_scene_list()
    if not scenes:
        return []
    # Use scene starts (skip 0)
    return [round(s.get_seconds(), 6) for (s, _) in scenes[1:]]

def coalesce(times, min_gap):
    if not times:
        return []
    times = sorted(times)
    keep = [times[0]]
    for t in times[1:]:
        if t - keep[-1] >= min_gap:
            keep.append(t)
    return keep

def build_segments(duration, cut_times):
    edges = [0.0] + [t for t in cut_times if 0.0 < t < duration] + [duration]
    segs = []
    for i in range(len(edges) - 1):
        s, e = edges[i], edges[i+1]
        if e - s >= 1e-6:
            segs.append((s, e))
    return segs

def fmt_hmsf(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

def write_csv(segments, csv_path):
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index","start_sec","end_sec","start_tc","end_tc","duration_sec"])
        for i,(s,e) in enumerate(segments, start=1):
            w.writerow([i, f"{s:.3f}", f"{e:.3f}", fmt_hmsf(s), fmt_hmsf(e), f"{(e-s):.3f}"])

def split_video_copy(input_path, segments, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(input_path).suffix or ".mov"
    pad = max(2, len(str(len(segments))))
    for i,(s,e) in enumerate(segments, start=1):
        out_file = out_dir / f"vid_{i:0{pad}d}{ext}"
        rc,_,err = run([
            "ffmpeg","-hide_banner",
            "-ss", f"{s:.6f}", "-to", f"{e:.6f}",
            "-i", input_path,
            "-c","copy",
            "-y", str(out_file)
        ])
        if rc != 0:
            print(f"[!] Video split failed for {i} ({s:.3f}-{e:.3f})\n{err}", file=sys.stderr)
            sys.exit(2)
        print(f"[+] {out_file.name}  ({e-s:.3f}s)")

def probe_audio_pcm(audio_path):
    rc,out,err = run([
        "ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=sample_fmt,bits_per_raw_sample,channels",
        "-of","default=noprint_wrappers=1", audio_path
    ])
    sample_fmt = ""
    bprs = ""
    for line in (out or "").splitlines():
        if line.startswith("sample_fmt="):
            sample_fmt = line.split("=",1)[1].strip()
        elif line.startswith("bits_per_raw_sample="):
            bprs = line.split("=",1)[1].strip()
    if "flt" in sample_fmt:
        return "pcm_f32le"
    if bprs == "24":
        return "pcm_s24le"
    if bprs == "32" and "s32" in sample_fmt:
        return "pcm_s32le"
    return "pcm_s16le"

def split_audio_pcm(audio_path, segments, out_dir, pcm_codec):
    out_dir.mkdir(parents=True, exist_ok=True)
    pad = max(2, len(str(len(segments))))
    for i,(s,e) in enumerate(segments, start=1):
        out_file = out_dir / f"aud_{i:0{pad}d}.wav"
        rc,_,err = run([
            "ffmpeg","-hide_banner",
            "-ss", f"{s:.6f}", "-to", f"{e:.6f}",
            "-i", audio_path,
            "-map","0:a:0","-vn",
            "-c:a", pcm_codec,
            "-y", str(out_file)
        ])
        if rc != 0:
            print(f"[!] Audio split failed for {i} ({s:.3f}-{e:.3f})\n{err}", file=sys.stderr)
            sys.exit(2)
        print(f"[+] {out_file.name}  ({e-s:.3f}s)")

def main():
    import atexit

    need("ffmpeg"); need("ffprobe")

    # --- VIDEO path (drag-and-drop friendly) ---
    try:
        raw_video = input("Drop/paste VIDEO path and press Enter: ")
    except EOFError:
        print("No video path provided.", file=sys.stderr); sys.exit(1)
    video_in = norm_path(raw_video)
    if not os.path.exists(video_in):
        print(f"Not found: {video_in}", file=sys.stderr); sys.exit(1)

    print("\n--- scene_slicer_v3 (drag-drop) ---")
    print(f"Video: {video_in}")
    duration = ffprobe_duration(video_in)
    print(f"Duration: {duration:.3f}s")

    # --- Detect cuts (PySceneDetect + ffmpeg union) ---
    print(f"\nDetecting cuts with PySceneDetect (threshold={PSD_THRESHOLD}, min_frames={PSD_MIN_FRAMES})…")
    cuts_psd = detect_cuts_pyscenedetect(video_in, PSD_THRESHOLD, PSD_MIN_FRAMES)
    print(f"PySceneDetect cuts: {len(cuts_psd)}")

    print(f"Detecting cuts with ffmpeg (scene={FFMPEG_SCENE})…")
    cuts_ff = detect_cuts_ffmpeg(video_in, FFMPEG_SCENE)
    print(f"ffmpeg cuts: {len(cuts_ff)}")

    merged = sorted(set([*cuts_psd, *cuts_ff]))
    merged = coalesce(merged, MIN_GAP_SEC)
    print(f"Merged cuts after coalesce: {len(merged)}")

    segments = build_segments(duration, merged)
    if not segments:
        print("No segments found. Lower thresholds or check your source.", file=sys.stderr)
        sys.exit(0)

    # --- Output dir: "<script_dir>/Scenes" ---
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / "Scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput folder: {out_dir}")

    # --- Save reference CSV of exact timings ---
    csv_path = out_dir / "scene_cuts.csv"
    write_csv(segments, csv_path)
    print("[+] Wrote scene_cuts.csv")

    # Register CSV for deletion at exit
    def _delete_csv():
        try:
            if csv_path.exists():
                csv_path.unlink()
        except Exception as e:
            print(f"[!] Failed to delete temporary CSV: {csv_path} ({e})", file=sys.stderr)
    import atexit
    atexit.register(_delete_csv)

    # --- Split VIDEO (stream-copy, no recompression) ---
    print("\nSplitting VIDEO (stream-copy)…")
    split_video_copy(video_in, segments, out_dir)

    # --- AUDIO path (drag-and-drop friendly) ---
    try:
        raw_audio = input("\nDrop/paste matching AUDIO (WAV) path and press Enter (or leave blank to skip): ")
    except EOFError:
        raw_audio = ""
    if raw_audio.strip():
        audio_in = norm_path(raw_audio)
        if not os.path.exists(audio_in):
            print(f"Audio not found: {audio_in}", file=sys.stderr); sys.exit(1)
        pcm_codec = probe_audio_pcm(audio_in)
        print(f"Detected/selected PCM codec: {pcm_codec}")
        print("Splitting AUDIO (PCM, no compression)…")
        split_audio_pcm(audio_in, segments, out_dir, pcm_codec)
    else:
        print("No audio provided; skipped audio splits.")

    print(f"\n✅ Done. Segments: {len(segments)} → {out_dir}")
    print("Note: For H.264/H.265 sources, video trims are keyframe-accurate with -c copy.\n"
          "For exact frame cuts on those codecs, convert to intra (ProRes/DNxHR) first or re-encode only at boundaries.")

if __name__ == "__main__":
    main()
