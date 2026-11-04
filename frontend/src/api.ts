import type {
  InventoryCreate,
  InventoryItem,
  Recipe,
  SettingsStatus,
  UpdateSettingsPayload,
} from './types'

const BASE_URL = ''

function parseErrorDetail(err: any): string {
  if (!err) return 'Operation failed'
  if (typeof err.detail === 'string') return err.detail
  if (Array.isArray(err.detail)) {
    return err.detail
      .map((d: any) => {
        if (typeof d === 'string') return d
        const loc = Array.isArray(d.loc) ? d.loc.filter((l: string) => l !== 'body' && l !== 'query').join('.') : ''
        const prefix = loc ? `${loc}: ` : ''
        return `${prefix}${d.msg || JSON.stringify(d)}`
      })
      .join('; ')
  }
  if (typeof err.detail === 'object' && err.detail !== null) {
    return err.detail.msg || err.detail.detail || JSON.stringify(err.detail)
  }
  if (typeof err.message === 'string') return err.message
  return JSON.stringify(err)
}

export async function fetchRecipes(): Promise<Recipe[]> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

export async function fetchRecipeById(id: string): Promise<Recipe> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/${id}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
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
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

export async function deleteRecipe(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
}

// Ingestion streams
export async function ingestUrl(url: string): Promise<Recipe> {
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
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

export async function ingestText(text: string, sourceName = 'Pasted recipe'): Promise<Recipe> {
  const res = await fetch(`${BASE_URL}/api/v1/recipes/ingest/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source_name: sourceName }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
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
    throw new Error(parseErrorDetail(err))
  }
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
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
    throw new Error(parseErrorDetail(err))
  }
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
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
    throw new Error(parseErrorDetail(err))
  }
  const result = await res.json()
  return fetchRecipeById(result.recipe_id)
}

// Inventory
export async function fetchInventory(): Promise<InventoryItem[]> {
  const res = await fetch(`${BASE_URL}/api/v1/inventory`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
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
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}

export async function deleteInventoryItem(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/inventory/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
}

// Settings & BYOK
export async function fetchSettingsStatus(): Promise<SettingsStatus> {
  const res = await fetch(`${BASE_URL}/api/v1/settings`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(parseErrorDetail(err))
  }
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
    throw new Error(parseErrorDetail(err))
  }
  return res.json()
}
