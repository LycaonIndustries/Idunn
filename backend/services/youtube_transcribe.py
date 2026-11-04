"""Bounded child process: download one video and transcribe it with local Whisper."""

from __future__ import annotations

import sys
from pathlib import Path


def transcribe(
    url: str,
    output: Path,
    model: str,
    max_seconds: int,
    max_bytes: int,
    local_files_only: bool,
) -> None:
    """Download audio from a YouTube video and transcribe speech to text.

    Args:
        url: Direct YouTube video URL.
        output: Destination text file path for transcribed output.
        model: Whisper model variant identifier (e.g. "base", "tiny").
        max_seconds: Maximum allowed video duration in seconds.
        max_bytes: Maximum allowed audio file size in bytes.
        local_files_only: Whether to restrict Whisper to pre-cached local weights.

    Raises:
        ValueError: If video is live, duration is exceeded, audio size is invalid,
            or no speech could be transcribed.
    """
    from faster_whisper import WhisperModel
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    def check_progress(progress: dict) -> None:
        if progress.get("downloaded_bytes", 0) > max_bytes:
            raise DownloadError("Video audio exceeds the download limit.")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output.parent / "audio.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 1,
        "fragment_retries": 1,
        "max_filesize": max_bytes,
        "progress_hooks": [check_progress],
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=False)
        if not info or info.get("is_live") or not info.get("duration"):
            raise ValueError("Only recorded videos with a known duration are supported.")
        if info["duration"] > max_seconds:
            raise ValueError("Video is longer than VIDEO_MAX_SECONDS.")
        downloader.process_info(info)
        audio = Path(downloader.prepare_filename(info))
    if not audio.is_file() or audio.stat().st_size > max_bytes:
        raise ValueError("Video audio is missing or exceeds VIDEO_MAX_BYTES.")
    whisper = WhisperModel(
        model, device="cpu", compute_type="int8", local_files_only=local_files_only
    )
    segments, _ = whisper.transcribe(str(audio), vad_filter=True)
    text = "\n".join(segment.text.strip() for segment in segments)
    if not text.strip():
        raise ValueError("No speech was found in this video.")
    output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 7:
        sys.exit(2)
    transcribe(
        sys.argv[1],
        Path(sys.argv[2]),
        sys.argv[3],
        int(sys.argv[4]),
        int(sys.argv[5]),
        sys.argv[6] == "true",
    )
