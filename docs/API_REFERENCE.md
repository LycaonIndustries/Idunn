# API Reference

All REST endpoints are namespaced under `/api/v1`. Interactive OpenAPI documentation is accessible at `/docs` when the server is running.

---

## 1. Inventory & Pantry Management

### `GET /api/v1/inventory`
Retrieve active pantry inventory items.
- **Query Parameters**:
  - `location` *(optional, string)*: Filter items by location (e.g., `fridge`, `pantry`, `spice_rack`).
  - `limit` *(optional, integer, default: 50)*
  - `offset` *(optional, integer, default: 0)*
- **Response**: Array of `ItemResponse` objects.

### `POST /api/v1/inventory`
Create a new pantry item.
- **Request Body**:
  ```json
  {
    "name": "Paneer",
    "quantity": 200,
    "unit": "g",
    "location": "fridge",
    "expiry_date": "2026-11-10T00:00:00Z"
  }
  ```

### `GET /api/v1/inventory/expiring`
Retrieve items expiring within a given time window (FEFO ordering).
- **Query Parameters**:
  - `days` *(optional, integer, default: 7)*

### `PATCH /api/v1/inventory/{id}`
Update item quantity, location, or expiry.

### `POST /api/v1/inventory/{id}/consume`
Record partial or full item consumption.

### `DELETE /api/v1/inventory/{id}`
Remove an item from inventory.

---

## 2. Recipe Ingestion & Vault

### `GET /api/v1/recipes`
List recipes in the vault.
- **Query Parameters**:
  - `query` *(optional, string)*: Search title, ingredients, tags.
  - `cuisine_type` *(optional, string)*: `veg`, `non_veg`, `egg`, `vegan`.
  - `limit` *(optional, integer, default: 50)*

### `POST /api/v1/recipes/ingest`
Ingest a recipe from a URL (YouTube, recipe blog, schema.org JSON-LD).
- **Request Body** *(or Query Parameter `url`)*:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=..."
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "recipe_id": "673f8a...",
    "confidence": 0.95,
    "needs_review": false,
    "warnings": []
  }
  ```

### `POST /api/v1/recipes/ingest/text`
Ingest unstructured recipe text, family heirloom notes, or WhatsApp recipe forwards.
- **Request Body**:
  ```json
  {
    "text": "1 cup besan, 1/2 cup ghee, 1/2 tsp elaichi...",
    "source_name": "Family Notebook"
  }
  ```

### `POST /api/v1/recipes/ingest/image`
Upload a cookbook photo or recipe screenshot for multimodal vision extraction.
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (image/jpeg, image/png, image/webp), `source_name` (optional).

### `POST /api/v1/recipes/ingest/audio`
Upload an audio memo or voice note for transcription and recipe extraction.
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (audio/mpeg, audio/wav, audio/m4a), `source_name` (optional).

### `POST /api/v1/recipes/ingest/video`
Upload a silent video reel or short for keyframe extraction and vision parsing.
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (video/mp4, video/quicktime), `source_name` (optional).

### `GET /api/v1/recipes/{id}`
Retrieve complete recipe details including nutritional macros, scaled ingredients, and cooking steps.

### `DELETE /api/v1/recipes/{id}`
Delete a recipe from the vault.

---

## 3. Settings & BYOK Management

### `GET /api/v1/settings`
Get active configuration status (masked API keys, active database backend, provider flags).

### `POST /api/v1/settings`
Update BYOK keys at runtime with automated `.env` file persistence.
- **Request Body**:
  ```json
  {
    "gemini_api_key": "AIzaSy...",
    "supabase_url": "https://xyz.supabase.co",
    "supabase_key": "sb_publishable_..."
  }
  ```
