"""Receipt and bill ingestion API endpoints for Iðunn."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..config import settings
from ..db import COLLECTION_ITEMS, COLLECTION_RECEIPTS, get_db
from ..models.receipt import Receipt, ReceiptConfirmRequest
from ..security.upload_validation import read_and_validate_upload
from ..services.receipt_ingest import ReceiptIngestService

router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])
Database = Annotated[AsyncIOMotorDatabase, Depends(get_db)]


def get_receipt_service() -> ReceiptIngestService:
    """Instantiate receipt extraction service with application settings.

    Returns:
        Configured ReceiptIngestService instance.
    """
    return ReceiptIngestService(settings)


ReceiptService = Annotated[ReceiptIngestService, Depends(get_receipt_service)]


class ReceiptConfirmResponse(BaseModel):
    """Result of confirming receipt items into active pantry."""

    receipt_id: str = Field(..., description="Target receipt identifier")
    confirmed_count: int = Field(..., ge=0, description="Number of items added to pantry")
    status: str = Field(default="confirmed", description="Confirmation status")


@router.post(
    "/ingest/image",
    response_model=Receipt,
    status_code=status.HTTP_200_OK,
)
async def ingest_receipt_image(
    service: ReceiptService,
    db: Database,
    file: UploadFile = File(...),
    store_hint: str | None = Form(None),
) -> Receipt:
    """Extract grocery candidate items from uploaded receipt image or app screenshot.

    Args:
        file: Uploaded image file (JPEG, PNG, WEBP).
        store_hint: Optional manual store name override.
        service: Injected receipt extraction service.
        db: Database session.

    Returns:
        Receipt model populated with candidate items and shelf life projections.

    Raises:
        HTTPException: If file is missing or extraction fails.
    """
    # Enforce size limits and magic byte verification to prevent DoS and malicious payloads.
    image_bytes, mime_type = await read_and_validate_upload(file)

    receipt = await service.extract_from_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        store_hint=store_hint,
    )

    # Persist unconfirmed receipt to allow user review before pantry addition.
    receipt_dict = receipt.model_dump(by_alias=True)
    await db[COLLECTION_RECEIPTS].insert_one(receipt_dict)

    return receipt


@router.post(
    "/confirm",
    response_model=ReceiptConfirmResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_receipt_items(
    payload: ReceiptConfirmRequest,
    db: Database,
) -> ReceiptConfirmResponse:
    """Commit verified candidate items from receipt into pantry inventory.

    Args:
        payload: Confirmation request payload containing candidate items.
        db: Injected database handle.

    Returns:
        ReceiptConfirmResponse confirming number of items added.

    Raises:
        HTTPException: If receipt identifier is missing or no items provided.
    """
    now = datetime.now(UTC)
    confirmed_count = 0

    # Add each approved candidate item to active pantry stock.
    for candidate in payload.items:
        expiry_date = candidate.calculate_expiry_date(reference_date=now)
        store_label = payload.store_name or "Receipt OCR"

        item_dict = {
            "name": candidate.name,
            "quantity": candidate.quantity,
            "unit": candidate.unit.value,
            "location": candidate.suggested_location,
            "expiry_date": expiry_date,
            "notes": f"Imported from {store_label}",
            "barcode": None,
            "added_at": now,
            "updated_at": now,
            "consumed": False,
        }
        await db[COLLECTION_ITEMS].insert_one(item_dict)
        confirmed_count += 1

    # Mark receipt record confirmed to avoid duplicate imports.
    await db[COLLECTION_RECEIPTS].update_one(
        {"_id": payload.receipt_id},
        {"$set": {"confirmed": True, "status": "confirmed", "updated_at": now}},
    )

    return ReceiptConfirmResponse(
        receipt_id=payload.receipt_id,
        confirmed_count=confirmed_count,
        status="confirmed",
    )


@router.get(
    "",
    response_model=list[Receipt],
    status_code=status.HTTP_200_OK,
)
async def list_receipts(
    db: Database,
    skip: int = 0,
    limit: int = 50,
) -> list[Receipt]:
    """Retrieve historical receipts ordered by purchase date descending.

    Args:
        skip: Pagination offset.
        limit: Maximum records to return.
        db: Injected database handle.

    Returns:
        List of historical receipts.
    """
    cursor = db[COLLECTION_RECEIPTS].find().sort("created_at", -1).skip(skip).limit(limit)
    raw_receipts = await cursor.to_list(length=limit)
    for rcpt in raw_receipts:
        if isinstance(rcpt.get("_id"), str):
            continue
        rcpt["_id"] = str(rcpt["_id"])
    return [Receipt(**r) for r in raw_receipts]
