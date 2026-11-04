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
    """Find ffmpeg on system path or standard Windows install directories.

    Returns:
        The executable command name or full path to ffmpeg.exe.
    """
    # Check system PATH first for portable deployment across operating systems.
    found = shutil.which("ffmpeg")
    if found:
        return found

    # On Windows workstations, ffmpeg is commonly installed in standard Chocolatey or local
    # folders.
    # Check these directories before failing to simplify developer setup.
    common_locations = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    for loc in common_locations:
        if os.path.exists(loc):
            return loc
    return "ffmpeg"


def extract_frames_sync(video_path: Path, output_dir: Path, fps: int = 1) -> list[Path]:
    """Run ffmpeg synchronously to sample frames at given fps.

    Args:
        video_path: Path to the input video file on disk.
        output_dir: Directory where JPEG frames are written.
        fps: Number of frames per second to sample.

    Returns:
        Sorted list of paths to sampled JPEG frame files.

    Raises:
        ExtractionError: If ffmpeg fails, times out, or produces zero frames.
    """
    ffmpeg = get_ffmpeg_executable()
    output_pattern = str(output_dir / "frame_%04d.jpg")

    # Sample video at 1 frame per second and cap total frames at 120.
    # This keeps extraction fast and limits disk storage for large video files.
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

    # Set timeout to prevent corrupt or non-terminating video streams from locking worker
    # processes.
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="ignore")[:300]
            raise ExtractionError(f"ffmpeg video decoding failed: {err}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise ExtractionError("ffmpeg frame extraction timed out or is unavailable.") from exc

    # Confirm extracted frames exist on disk before returning.
    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise ExtractionError("No video frames could be decoded from this video.")
    return frames


async def sample_video_keyframes(video_bytes: bytes, max_frames: int = 15) -> list[bytes]:
    """Extract and evenly sample keyframes from raw video bytes.

    Args:
        video_bytes: Raw binary video file content.
        max_frames: Maximum number of frames to return.

    Returns:
        List of JPEG-encoded byte arrays for each sampled keyframe.
    """
    # Use temporary directory context to ensure all intermediate frame files delete automatically.
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        video_file = tmp_path / "input_video.mp4"
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        # Write uploaded bytes to disk because ffmpeg requires seekable filesystem input.
        video_file.write_bytes(video_bytes)

        # Offload ffmpeg process execution to a worker thread so the async loop remains
        # responsive.
        frame_paths = await asyncio.to_thread(extract_frames_sync, video_file, frames_dir, 1)

        # Downsample frames uniformly across the video timeline.
        # This keeps multimodal LLM payload sizes within token and context limits.
        total = len(frame_paths)
        if total <= max_frames:
            selected_paths = frame_paths
        else:
            step = total / max_frames
            indices = [int(i * step) for i in range(max_frames)]
            selected_paths = [frame_paths[idx] for idx in indices]

        return [path.read_bytes() for path in selected_paths]
