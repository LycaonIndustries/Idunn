import type { InventoryCreate, InventoryItem, Recipe, SettingsStatus, UpdateSettingsPayload } from './types'

const BASE_URL = ''

export async function fetchRecipes(): Promise<Recipe[]> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes`)
  if (!res.ok) throw new Error(`Failed to fetch recipes: ${res.statusText}`)
  return res.json()
}

export async function createRecipe(recipe: Partial<Recipe>): Promise<Recipe> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(recipe),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to save recipe')
  }
  return res.json()
}

export async function deleteRecipe(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete recipe')
}

// Ingestion streams
export async function ingestUrl(url: string): Promise<Recipe> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'URL ingestion failed')
  }
  return res.json()
}

export async function ingestText(text: string, sourceName = 'Pasted recipe'): Promise<Recipe> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source_name: sourceName }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Text ingestion failed')
  }
  return res.json()
}

export async function ingestImage(file: File, sourceName = 'Photo Upload'): Promise<Recipe> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/image`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Image ingestion failed')
  }
  return res.json()
}

export async function ingestAudio(file: File, sourceName = 'Voice Note'): Promise<Recipe> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/audio`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Audio ingestion failed')
  }
  return res.json()
}

export async function ingestVideo(file: File, sourceName = 'Cooking Reel'): Promise<Recipe> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_name', sourceName)

  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/video`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Video ingestion failed')
  }
  return res.json()
}

// Inventory
export async function fetchInventory(): Promise<InventoryItem[]> {
  const res = await fetch(`${BASE_URL}/api/v1/inventory`)
  if (!res.ok) throw new Error('Failed to fetch inventory')
  return res.json()
}

export async function createInventoryItem(item: InventoryCreate): Promise<InventoryItem> {
  const res = await fetch(`${BASE_URL}/api/v1/inventory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(item),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to add item')
  }
  return res.json()
}

export async function deleteInventoryItem(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/inventory/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete item')
}

// Settings & BYOK
export async function fetchSettingsStatus(): Promise<SettingsStatus> {
  const res = await fetch(`${BASE_URL}/api/v1/settings`)
  if (!res.ok) throw new Error('Failed to fetch settings status')
  return res.json()
}

export async function updateSettings(payload: UpdateSettingsPayload): Promise<SettingsStatus> {
  const res = await fetch(`${BASE_URL}/api/v1/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to update settings')
  }
  return res.json()
}
