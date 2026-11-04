/**
 * Unit tests for the frontend HTTP API client module.
 */
import { describe, expect, it, afterEach, mock } from 'bun:test'
import {
  confirmReceiptItems,
  cookRecipe,
  createInventoryItem,
  deleteInventoryItem,
  fetchInventory,
  fetchRecipes,
  fetchSettingsStatus,
  ingestReceiptImage,
  ingestText,
  ingestUrl,
  updateSettings,
} from './api'

describe('API Client', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    // Restore native global fetch after each mock execution.
    globalThis.fetch = originalFetch
  })

  // Test recipe fetching.
  it('fetchRecipes returns recipe list on 200 response', async () => {
    const mockRecipes = [
      {
        id: 'rec_1',
        title: 'Paneer Butter Masala',
        ingredients: [{ name: 'Paneer' }],
        steps: [{ step_number: 1, instruction: 'Sauté onions' }],
      },
    ]

    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify(mockRecipes), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const result = await fetchRecipes()
    expect(result).toEqual(mockRecipes as any)
  })

  // Test error handling when backend returns an HTTP 500 error.
  it('fetchRecipes throws formatted error message on failure', async () => {
    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify({ detail: 'Database unavailable' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    expect(fetchRecipes()).rejects.toThrow('Database unavailable')
  })

  // Test inventory fetching.
  it('fetchInventory returns inventory items list', async () => {
    const mockItems = [
      {
        id: 'item_1',
        name: 'Mustard Seeds',
        quantity: 100,
        unit: 'g',
        location: 'spice_box',
      },
    ]

    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify(mockItems), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const result = await fetchInventory()
    expect(result).toEqual(mockItems as any)
  })

  // Test inventory item creation.
  it('createInventoryItem submits POST request and returns created item', async () => {
    const payload = {
      name: 'Toor Dal',
      quantity: 1,
      unit: 'kg',
      location: 'pantry',
      expiry_date: null,
    }

    const createdItem = { id: 'dal_123', ...payload, consumed: false }

    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('POST')
      return new Response(JSON.stringify(createdItem), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const result = await createInventoryItem(payload)
    expect(result.id).toBe('dal_123')
    expect(result.name).toBe('Toor Dal')
  })

  // Test inventory item deletion.
  it('deleteInventoryItem sends DELETE request for target item id', async () => {
    let calledUrl = ''
    globalThis.fetch = mock(async (url: any, init: any) => {
      calledUrl = String(url)
      expect(init?.method).toBe('DELETE')
      return new Response(null, { status: 204 })
    }) as any

    await deleteInventoryItem('item_999')
    expect(calledUrl).toContain('/api/v1/inventory/item_999')
  })

  // Test settings fetching and status response.
  it('fetchSettingsStatus returns system provider configuration', async () => {
    const statusData = {
      database_backend: 'supabase',
      supabase_configured: true,
      gemini_configured: true,
      gemini_model: 'gemini-2.5-flash',
      active_llm_provider: 'gemini',
      env_file_exists: true,
    }

    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify(statusData), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const status = await fetchSettingsStatus()
    expect(status.database_backend).toBe('supabase')
    expect(status.active_llm_provider).toBe('gemini')
  })

  // Test updating BYOK settings.
  it('updateSettings sends PATCH/POST payload and returns updated status', async () => {
    const updatePayload = {
      gemini_api_key: 'AIzaSyTestKey',
      gemini_model: 'gemini-2.5-flash',
    }

    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('POST')
      return new Response(
        JSON.stringify({
          database_backend: 'supabase',
          gemini_configured: true,
          gemini_api_key_masked: 'AIza...yTestKey',
          active_llm_provider: 'gemini',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }) as any

    const updated = await updateSettings(updatePayload)
    expect(updated.gemini_configured).toBe(true)
  })

  // Test URL recipe ingestion.
  it('ingestUrl sends url parameter and parses returned recipe result', async () => {
    const ingestData = {
      recipe_id: 'rec_555',
      confidence: 0.95,
      source_type: 'json-ld',
    }

    const fullRecipe = {
      id: 'rec_555',
      title: 'Dal Tadka',
      ingredients: [],
      steps: [],
    }

    globalThis.fetch = mock(async (url: any) => {
      const urlStr = String(url)
      if (urlStr.includes('/api/v1/recipes/ingest?url=')) {
        return new Response(JSON.stringify(ingestData), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      if (urlStr.includes('/api/v1/recipes/rec_555')) {
        return new Response(JSON.stringify(fullRecipe), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('Not found', { status: 404 })
    }) as any

    const result = await ingestUrl('https://hebbarskitchen.com/dal-tadka')
    expect(result.title).toBe('Dal Tadka')
    expect(result.id).toBe('rec_555')
  })

  // Test text recipe ingestion.
  it('ingestText posts pasted recipe content and attribution name', async () => {
    const textResult = {
      recipe_id: 'rec_888',
      confidence: 0.88,
      source_type: 'text',
    }

    const fullRecipe = {
      id: 'rec_888',
      title: 'Jeera Rice',
      ingredients: [],
      steps: [],
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      const urlStr = String(url)
      if (urlStr.includes('/api/v1/recipes/ingest/text')) {
        const body = JSON.parse(String(init?.body))
        expect(body.text).toContain('Basmati rice and cumin')
        return new Response(JSON.stringify(textResult), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      if (urlStr.includes('/api/v1/recipes/rec_888')) {
        return new Response(JSON.stringify(fullRecipe), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('Not found', { status: 404 })
    }) as any

    const result = await ingestText('Basmati rice and cumin', 'Family Notebook')
    expect(result.title).toBe('Jeera Rice')
    expect(result.id).toBe('rec_888')
  })

  // Test receipt image ingestion.
  it('ingestReceiptImage posts multipart form data and receives parsed receipt', async () => {
    const mockReceipt = {
      _id: 'rcpt_777',
      store_name: 'Blinkit',
      items: [
        {
          raw_text: 'Amul Milk 500ml',
          name: 'Amul Milk',
          quantity: 500,
          unit: 'ml',
          category: 'dairy',
          estimated_shelf_life_days: 3,
          suggested_location: 'fridge',
        },
      ],
      confidence: 0.95,
      confirmed: false,
      status: 'pending',
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      expect(String(url)).toContain('/api/v1/receipts/ingest/image')
      expect(init?.method).toBe('POST')
      expect(init?.body instanceof FormData).toBe(true)
      return new Response(JSON.stringify(mockReceipt), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const fakeFile = new File(['fake content'], 'bill.jpg', { type: 'image/jpeg' })
    const receipt = await ingestReceiptImage(fakeFile, 'Blinkit')
    expect(receipt._id).toBe('rcpt_777')
    expect(receipt.store_name).toBe('Blinkit')
    expect(receipt.items.length).toBe(1)
  })

  // Test receipt items confirmation.
  it('confirmReceiptItems posts payload and returns confirmation count', async () => {
    const confirmPayload = {
      receipt_id: 'rcpt_777',
      store_name: 'Blinkit',
      items: [
        {
          raw_text: 'Amul Milk 500ml',
          name: 'Amul Milk',
          quantity: 500,
          unit: 'ml',
          category: 'dairy',
          estimated_shelf_life_days: 3,
          suggested_location: 'fridge',
        },
      ],
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      expect(String(url)).toContain('/api/v1/receipts/confirm')
      expect(init?.method).toBe('POST')
      const body = JSON.parse(String(init?.body))
      expect(body.receipt_id).toBe('rcpt_777')
      return new Response(
        JSON.stringify({ receipt_id: 'rcpt_777', confirmed_count: 1, status: 'confirmed' }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }) as any

    const res = await confirmReceiptItems(confirmPayload)
    expect(res.confirmed_count).toBe(1)
    expect(res.status).toBe('confirmed')
  })

  // Test cooking deduction endpoint.
  it('cookRecipe posts recipe cook action and receives deduction report', async () => {
    const mockReport = {
      recipe_id: 'rec_555',
      servings_multiplier: 1.5,
      deductions: [
        {
          item_id: 'item_1',
          item_name: 'Toor Dal',
          deducted_quantity: 150,
          unit: 'g',
          depleted: false,
          remaining_quantity: 350,
        },
      ],
      shortages: [],
      fully_satisfied: true,
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      expect(String(url)).toContain('/api/v1/recipes/rec_555/cook?servings_multiplier=1.5')
      expect(init?.method).toBe('POST')
      return new Response(JSON.stringify(mockReport), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const report = await cookRecipe('rec_555', 1.5)
    expect(report.fully_satisfied).toBe(true)
    expect(report.deductions.length).toBe(1)
    expect(report.deductions[0].item_name).toBe('Toor Dal')
  })
})
