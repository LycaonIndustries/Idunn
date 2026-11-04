/**
 * Typed HTTP API client for Iðunn Kitchen OS.
 * Communicates with the FastAPI backend mounted on the same host and port.
 */

import type {
  DeductionReport,
  InventoryCreate,
  InventoryItem,
  Receipt,
  ReceiptConfirmPayload,
  ReceiptConfirmResponse,
  Recipe,
  SettingsStatus,
  ShoppingListItem,
  ShoppingListItemCreate,
  ShoppingListItemUpdate,
  UpdateSettingsPayload,
} from './types'

// Leave BASE_URL empty so requests use relative paths against the current origin.
// In both production and dev single-port mode, FastAPI mounts the frontend directly at root.
const BASE_URL = ''

/**
 * Format FastAPI and Pydantic validation errors into human-readable messages.
 *
 * @param err - Raw JSON error object received from the backend response.
 * @returns Formatted single-line error message for user notifications.
 */
function parseErrorDetail(err: any): string {
  // If the server returned an empty body or non-JSON response, fall back to generic text.
  if (!err) return 'Operation failed'

  // FastAPI HTTPException with a string detail (e.g. status 400, 404, 500).
  if (typeof err.detail === 'string') return err.detail

  // Pydantic validation error returns an array of error objects with 'loc' and 'msg'.
  // Flatten array into field: message pairs so users know which input field was rejected.
  if (Array.isArray(err.detail)) {
    return err.detail
      .map((d: any) => {
        if (typeof d === 'string') return d
        const loc = Array.isArray(d.loc)
          ? d.loc.filter((l: string) => l !== 'body' && l !== 'query').join('.')
          : ''
        const prefix = loc ? `${loc}: ` : ''
        return `${prefix}${d.msg || JSON.stringify(d)}`
      })
      .join('; ')
  }

  // Handle nested object details or standard Error objects.
  if (typeof err.detail === 'object' && err.detail !== null) {
    return err.detail.msg || err.detail.detail || JSON.stringify(err.detail)
  }
  if (typeof err.message === 'string') return err.message
  return JSON.stringify(err)
}

/**
 * Fetch all stored recipes from the vault.
 *
 * @returns Array of recipes sorted by creation date.
 * @throws Error if network request fails or server returns an error status.
 */
export async function fetchRecipes(): Promise<Recipe[]> {
  // Query the recipes endpoint to load cards into the vault grid view.
  const res = await fetch(`${BASE_URL}/api/v1/recipes`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Fetch a single recipe record by its identifier.
 *
 * @param id - MongoDB ObjectId or Supabase UUID string.
 * @returns Complete recipe document including ingredients and steps.
 * @throws Error if the recipe is not found or request fails.
 */
export async function fetchRecipeById(id: string): Promise<Recipe> {
  // Retrieve full recipe details when navigating into the dedicated detail view.
  const res = await fetch(`${BASE_URL}/api/v1/recipes/${id}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Create a new recipe manually.
 *
 * @param recipe - Partial recipe fields from form input.
 * @returns Created and persisted Recipe document.
 * @throws Error if required fields fail validation.
 */
export async function createRecipe(recipe: Partial<Recipe>): Promise<Recipe> {
  // Persist manually authored recipes with JSON payload headers.
  const res = await fetch(`${BASE_URL}/api/v1/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(recipe),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Permanently delete a recipe from the vault.
 *
 * @param id - Recipe identifier to remove.
 * @throws Error if deletion fails or item is not found.
 */
export async function deleteRecipe(id: string): Promise<void> {
  // Send DELETE request to clean up unwanted or duplicate recipe cards.
  const res = await fetch(`${BASE_URL}/api/v1/recipes/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
}

/**
 * Ingest a recipe from a web URL or YouTube link.
 *
 * @param url - Source web URL.
 * @returns Ingested and stored Recipe document.
 * @throws Error if extraction fails or URL is unreachable.
 */
export async function ingestUrl(url: string): Promise<Recipe> {
  // Pass URL as query parameter and JSON body to support both query and payload parsers.
  const encodedUrl = encodeURIComponent(url.trim())
  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest?url=${encodedUrl}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: url.trim() }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }

  // The ingestion endpoint returns an IngestResult metadata object containing recipe_id.
  // Fetch the full recipe record immediately so the UI can navigate straight to the created card.
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

/**
 * Ingest a recipe from raw pasted text or WhatsApp notes.
 *
 * @param text - Raw recipe instructions and ingredients.
 * @param sourceName - Optional attribution string.
 * @returns Ingested and stored Recipe document.
 * @throws Error if text extraction fails.
 */
export async function ingestText(text: string, sourceName = 'Pasted recipe'): Promise<Recipe> {
  // Send text payload to the LLM extraction service.
  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source_name: sourceName }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }

  // Load the newly persisted recipe to render full step details in the view.
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

/**
 * Ingest a recipe from an uploaded cookbook photo or screenshot.
 *
 * @param file - Binary image file (JPEG, PNG, WebP).
 * @param sourceName - User label for the source.
 * @returns Ingested Recipe document.
 * @throws Error if image upload or OCR extraction fails.
 */
export async function ingestImage(file: File, sourceName = 'Photo Upload'): Promise<Recipe> {
  // Use FormData to transfer binary files via multipart/form-data encoding.
  // Do not set Content-Type header manually so the browser calculates multipart boundaries.
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/image`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }

  // Retrieve the saved document with its stored base64 image data URI.
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

/**
 * Ingest a recipe from an audio voice note or voice recording.
 *
 * @param file - Audio file (MP3, WAV, M4A, WebM).
 * @param sourceName - Label for the voice memo.
 * @returns Ingested Recipe document.
 * @throws Error if audio file exceeds limits or contains no speech.
 */
export async function ingestAudio(file: File, sourceName = 'Voice Note'): Promise<Recipe> {
  // Multipart upload sends raw audio bytes directly to the backend transcription service.
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/audio`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }

  // Fetch created recipe using returned recipe identifier.
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

/**
 * Ingest a recipe from a silent video reel by sampling video frames.
 *
 * @param file - Video file (MP4, WebM, MOV).
 * @param sourceName - Reel label.
 * @returns Ingested Recipe document.
 * @throws Error if video processing or vision parsing fails.
 */
export async function ingestVideo(file: File, sourceName = 'Cooking Reel'): Promise<Recipe> {
  // Upload video via multipart form data for server-side keyframe sampling.
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/video`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }

  // Fetch full recipe and display cover thumbnail extracted from sampled video frame.
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

/**
 * Fetch active kitchen pantry inventory.
 *
 * @returns List of pantry items sorted by expiration urgency.
 * @throws Error if inventory request fails.
 */
export async function fetchInventory(): Promise<InventoryItem[]> {
  // Query inventory items to populate the Pantry FEFO status view.
  const res = await fetch(`${BASE_URL}/api/v1/inventory`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Add a new item to pantry stock.
 *
 * @param item - New inventory item payload.
 * @returns Created InventoryItem with server-assigned ID and expiry countdown.
 * @throws Error if payload validation fails.
 */
export async function createInventoryItem(item: InventoryCreate): Promise<InventoryItem> {
  // Send JSON body to create inventory records with Indian units and locations.
  const res = await fetch(`${BASE_URL}/api/v1/inventory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Delete or consume an item from pantry stock.
 *
 * @param id - Identifier of the inventory item.
 * @throws Error if item removal fails.
 */
export async function deleteInventoryItem(id: string): Promise<void> {
  // Remove item from database when depleted or expired.
  const res = await fetch(`${BASE_URL}/api/v1/inventory/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
}

/**
 * Fetch current backend configuration and provider credential status.
 *
 * @returns SettingsStatus reporting active database and configured AI models.
 * @throws Error if settings fetch fails.
 */
export async function fetchSettingsStatus(): Promise<SettingsStatus> {
  // Query settings to determine which AI providers and databases are available.
  const res = await fetch(`${BASE_URL}/api/v1/settings`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Update server credentials and provider preferences.
 *
 * @param payload - Partial settings dictionary containing keys to update.
 * @returns Updated SettingsStatus with fresh masked credentials.
 * @throws Error if credential update fails.
 */
export async function updateSettings(payload: UpdateSettingsPayload): Promise<SettingsStatus> {
  // Post user-supplied API keys to update runtime settings and persistent .env store.
  const res = await fetch(`${BASE_URL}/api/v1/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Upload receipt image or screenshot for OCR and pantry item extraction.
 *
 * @param file - Receipt image file.
 * @param storeHint - Optional store or app name.
 * @returns Parsed Receipt entity with candidates and shelf-life estimates.
 * @throws Error if extraction fails.
 */
export async function ingestReceiptImage(
  file: File,
  storeHint?: string,
): Promise<Receipt> {
  // Transmit image using multipart form data to allow binary payload transport.
  const formData = new FormData()
  formData.append('file', file)
  if (storeHint) {
    formData.append('store_hint', storeHint)
  }

  const res = await fetch(`${BASE_URL}/api/v1/receipts/ingest/image`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Confirm candidate items from receipt OCR into active pantry stock.
 *
 * @param payload - Confirmation request payload.
 * @returns Confirmation response with added count.
 * @throws Error if confirmation fails.
 */
export async function confirmReceiptItems(
  payload: ReceiptConfirmPayload,
): Promise<ReceiptConfirmResponse> {
  // Send verified items to commit into inventory stock collection.
  const res = await fetch(`${BASE_URL}/api/v1/receipts/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Deduct ingredients used in cooking a recipe from pantry inventory.
 *
 * @param recipeId - Identifier of the cooked recipe.
 * @param servingsMultiplier - Portion multiplier scaling factor.
 * @returns DeductionReport detailing consumed pantry batches and shortages.
 * @throws Error if cooking deduction fails.
 */
export async function cookRecipe(
  recipeId: string,
  servingsMultiplier: number = 1.0,
): Promise<DeductionReport> {
  // Trigger backend FEFO deduction to keep pantry stock synchronized with cooked meals.
  const url = `${BASE_URL}/api/v1/recipes/${recipeId}/cook?servings_multiplier=${servingsMultiplier}`
  const res = await fetch(url, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}


/**
 * Retrieve all items on the shopping list.
 */
export async function fetchShoppingList(): Promise<ShoppingListItem[]> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Add an item to the shopping list.
 */
export async function createShoppingItem(
  payload: ShoppingListItemCreate,
): Promise<ShoppingListItem> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Batch add items to the shopping list.
 */
export async function createShoppingItemsBatch(
  items: ShoppingListItemCreate[],
): Promise<ShoppingListItem[]> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Update a shopping list item.
 */
export async function updateShoppingItem(
  itemId: string,
  payload: ShoppingListItemUpdate,
): Promise<ShoppingListItem> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list/items/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

/**
 * Delete a shopping list item.
 */
export async function deleteShoppingItem(itemId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list/items/${itemId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
}

/**
 * Remove all checked items from the shopping list.
 */
export async function clearPurchasedShoppingItems(): Promise<{ deleted_count: number }> {
  const res = await fetch(`${BASE_URL}/api/v1/shopping-list/clear-purchased`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}
