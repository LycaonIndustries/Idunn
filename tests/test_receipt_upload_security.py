"""Security tests for receipt upload size limits, MIME magic byte checks, and sandboxing."""

from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile, status

from backend.security.upload_validation import (
    MAX_RECEIPT_UPLOAD_SIZE,
    read_and_validate_upload,
    sandboxed_upload_path,
    validate_image_magic_bytes,
    validate_upload_size,
)


@pytest.fixture
def client(api_client):
    """Reuse test client fixture."""
    return api_client


def test_validate_image_magic_bytes_valid_jpeg() -> None:
    """Ensure valid JPEG magic bytes return image/jpeg MIME type."""
    jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    mime = validate_image_magic_bytes(jpeg_header)
    assert mime == "image/jpeg"


def test_validate_image_magic_bytes_valid_png() -> None:
    """Ensure valid PNG magic bytes return image/png MIME type."""
    png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    mime = validate_image_magic_bytes(png_header)
    assert mime == "image/png"


def test_validate_image_magic_bytes_valid_webp() -> None:
    """Ensure valid WebP magic bytes return image/webp MIME type."""
    webp_header = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00"
    mime = validate_image_magic_bytes(webp_header)
    assert mime == "image/webp"


def test_validate_image_magic_bytes_rejects_executable_or_script() -> None:
    """Verify that disguised executable or HTML script payloads trigger 415 error."""
    disguised_payload = b"<html><script>alert('xss')</script></html>"
    with pytest.raises(HTTPException) as exc_info:
        validate_image_magic_bytes(disguised_payload)
    assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert "not a valid JPEG, PNG, or WebP" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_upload_size_rejects_oversized_stream() -> None:
    """Verify that streams exceeding max limit raise 413 Request Entity Too Large."""
    oversized_data = b"X" * (MAX_RECEIPT_UPLOAD_SIZE + 10)
    file = UploadFile(file=BytesIO(oversized_data), filename="huge.jpg")

    with pytest.raises(HTTPException) as exc_info:
        await validate_upload_size(file, max_bytes=MAX_RECEIPT_UPLOAD_SIZE)
    assert exc_info.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert "File size exceeds maximum permitted limit" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_and_validate_upload_rejects_empty_file() -> None:
    """Verify that zero-byte uploads raise 400 Bad Request."""
    empty_file = UploadFile(file=BytesIO(b""), filename="empty.jpg")

    with pytest.raises(HTTPException) as exc_info:
        await read_and_validate_upload(empty_file)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Uploaded file is empty" in exc_info.value.detail


def test_sandboxed_upload_path_creates_and_cleans_file() -> None:
    """Verify sandboxed temporary file is safely created and automatically deleted on exit."""
    sample_content = b"\xff\xd8\xff\xe0testcontent"
    created_path = None

    with sandboxed_upload_path(sample_content, prefix="test_receipt_") as path:
        created_path = path
        assert path.exists()
        assert path.is_file()
        assert path.read_bytes() == sample_content
        # Confirm sandbox resides in dedicated temp directory outside public web root
        assert "idunn_uploads" in str(path)

    # File must be deleted after exiting context manager
    assert not created_path.exists()


def test_api_receipt_ingest_rejects_spoofed_mime_type(client) -> None:
    """Verify endpoint rejects files claiming to be image/jpeg but containing HTML text."""
    spoofed_bytes = b"<!DOCTYPE html><html><body>Fake Receipt</body></html>"
    response = client.post(
        "/api/v1/receipts/ingest/image",
        files={"file": ("receipt.jpg", spoofed_bytes, "image/jpeg")},
    )
    assert response.status_code == 415
    assert "not a valid JPEG, PNG, or WebP" in response.json()["detail"]


def test_api_receipt_ingest_rejects_oversized_file(client) -> None:
    """Verify endpoint rejects uploads exceeding 10MB limit with 413 status."""
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (MAX_RECEIPT_UPLOAD_SIZE + 10)
    response = client.post(
        "/api/v1/receipts/ingest/image",
        files={"file": ("receipt.jpg", oversized_bytes, "image/jpeg")},
    )
    assert response.status_code == 413
    assert "File size exceeds maximum permitted limit" in response.json()["detail"]


def test_api_receipt_ingest_rejects_empty_file(client) -> None:
    """Verify endpoint returns 400 for empty upload file."""
    response = client.post(
        "/api/v1/receipts/ingest/image",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]
