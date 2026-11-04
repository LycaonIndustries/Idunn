"""Extract representative keyframes from video files for multimodal vision extraction."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .ingest_errors import ExtractionError


def get_ffmpeg_executable() -> str:
    """Find ffmpeg on system path or standard directories."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    common_locations = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for loc in common_locations:
        if os.path.exists(loc):
            return loc
    return "ffmpeg"


def extract_frames_sync(video_path: Path, output_dir: Path, fps: int = 1) -> list[Path]:
    """Run ffmpeg synchronously to sample frames at given fps."""
    ffmpeg = get_ffmpeg_executable()
    output_pattern = str(output_dir / "frame_%04d.jpg")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps}",
        "-frames:v",
        "120",  # Limit to max 120 raw frames before downsampling
        "-q:v",
        "3",  # High quality jpeg
        output_pattern,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="ignore")[:300]
            raise ExtractionError(f"ffmpeg video decoding failed: {err}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise ExtractionError("ffmpeg frame extraction timed out or is unavailable.") from exc

    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise ExtractionError("No video frames could be decoded from this video.")
    return frames


async def sample_video_keyframes(video_bytes: bytes, max_frames: int = 15) -> list[bytes]:
    """Extract and evenly sample keyframes from raw video bytes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        video_file = tmp_path / "input_video.mp4"
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        video_file.write_bytes(video_bytes)

        frame_paths = await asyncio.to_thread(extract_frames_sync, video_file, frames_dir, 1)

        # Evenly downsample to max_frames
        total = len(frame_paths)
        if total <= max_frames:
            selected_paths = frame_paths
        else:
            step = total / max_frames
            indices = [int(i * step) for i in range(max_frames)]
            selected_paths = [frame_paths[idx] for idx in indices]

        return [path.read_bytes() for path in selected_paths]
