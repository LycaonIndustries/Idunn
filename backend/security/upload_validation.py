"""File upload validation and sandboxing guards to prevent DoS and malicious payloads."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import filetype
from fastapi import HTTPException, UploadFile, status

# Default 10 megabyte ceiling prevents memory exhaustion and server crashes from oversized files.
MAX_RECEIPT_UPLOAD_SIZE: int = 10 * 1024 * 1024

# Restrict allowed image types to safe formats supported by vision models.
ALLOWED_IMAGE_MIMES: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")


async def validate_upload_size(
    file: UploadFile,
    max_bytes: int = MAX_RECEIPT_UPLOAD_SIZE,
) -> None:
    """Validate that uploaded file does not exceed maximum permitted byte ceiling.

    Args:
        file: Incoming FastAPI upload file stream.
        max_bytes: Maximum allowed payload size in bytes.

    Returns:
        None.

    Raises:
        HTTPException: If file size exceeds maximum permitted limit.
    """
    # Check advertised file size early to reject oversized files without reading into memory.
    if file.size is not None and file.size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum permitted limit ({limit_mb}MB).",
        )

    # Read one byte beyond ceiling to detect oversized stream when size header is missing.
    chunk = await file.read(max_bytes + 1)
    if len(chunk) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds maximum permitted limit ({limit_mb}MB).",
        )

    # Reset file pointer so downstream handlers read complete content from beginning.
    await file.seek(0)


def validate_image_magic_bytes(
    header: bytes,
    allowed_mimes: tuple[str, ...] = ALLOWED_IMAGE_MIMES,
) -> str:
    """Inspect binary magic bytes to prevent file extension spoofing attacks.

    Args:
        header: Leading binary bytes of uploaded file.
        allowed_mimes: Tuple of authorized MIME type strings.

    Returns:
        Verified MIME type string.

    Raises:
        HTTPException: If header does not match authorized image formats.
    """
    # Inspect binary signature because client headers can be spoofed by attackers.
    kind = filetype.guess(header)
    if kind is None or kind.mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file is not a valid JPEG, PNG, or WebP image.",
        )
    return kind.mime


async def read_and_validate_upload(
    file: UploadFile,
    max_bytes: int = MAX_RECEIPT_UPLOAD_SIZE,
    allowed_mimes: tuple[str, ...] = ALLOWED_IMAGE_MIMES,
) -> tuple[bytes, str]:
    """Read upload content and enforce size limits and magic byte verification.

    Args:
        file: Incoming FastAPI upload file.
        max_bytes: Maximum allowed file size in bytes.
        allowed_mimes: Allowed MIME types for format verification.

    Returns:
        Tuple containing raw binary content and verified MIME type string.

    Raises:
        HTTPException: If file is empty, too large, or has unsupported media type.
    """
    # Reject oversized streams before full buffer allocation to protect memory.
    await validate_upload_size(file, max_bytes=max_bytes)

    # Read complete buffer after size validation passes.
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Verify signature against allowed formats to block executable or script payloads.
    verified_mime = validate_image_magic_bytes(content[:1024], allowed_mimes=allowed_mimes)
    return content, verified_mime


@contextmanager
def sandboxed_upload_path(
    content: bytes,
    prefix: str = "idunn_receipt_",
    suffix: str = ".img",
) -> Generator[Path]:
    """Persist upload bytes in secure temporary sandbox and remove on exit.

    Args:
        content: Binary content bytes to write.
        prefix: Filename prefix for temp file.
        suffix: Filename suffix for temp file.

    Returns:
        Context manager yielding Path to isolated temporary file.
    """
    # Isolate temporary files in private directory to prevent execution and path traversal.
    sandbox_dir = Path(tempfile.gettempdir()) / "idunn_uploads"
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary file with restricted read/write flags.
    fd, temp_file_path = tempfile.mkstemp(
        prefix=prefix,
        suffix=suffix,
        dir=str(sandbox_dir),
    )
    temp_path = Path(temp_file_path)

    try:
        # Write binary content and close descriptor.
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        yield temp_path
    finally:
        # Delete temporary file immediately after processing to prevent disk leaks.
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
