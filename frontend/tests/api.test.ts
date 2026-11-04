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
  fetchWhatCanICook,
  fetchSubstitutions,
  generatePantryMeal,
  fetchShoppingList,
  addShoppingListItem,
  addShoppingListBatch,
  updateShoppingListItem,
  deleteShoppingListItem,
  clearPurchasedShoppingItems,
} from '../src/api'

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

  // Test what-can-i-cook endpoint.
  it('fetchWhatCanICook fetches ranked recipe matches with ready_only filter', async () => {
    const mockMatches = [
      {
        recipe_id: 'rec_101',
        recipe_title: 'Jeera Aloo',
        match_percentage: 100,
        can_cook_now: true,
        matched_ingredients: ['potato', 'cumin'],
        missing_ingredients: [],
        expiry_urgency_score: 5,
        expiring_ingredients_used: ['potato'],
      },
    ]

    globalThis.fetch = mock(async (url: any) => {
      expect(String(url)).toContain('/api/v1/cook-ai/what-can-i-cook?ready_only=true')
      return new Response(JSON.stringify(mockMatches), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const results = await fetchWhatCanICook(true)
    expect(results.length).toBe(1)
    expect(results[0].recipe_title).toBe('Jeera Aloo')
    expect(results[0].can_cook_now).toBe(true)
  })

  // Test substitution suggestions endpoint.
  it('fetchSubstitutions returns culinary replacement suggestion', async () => {
    const mockSub = {
      missing_ingredient: 'sour cream',
      substitute_item: 'yogurt',
      ratio_or_amount: '1:1 ratio',
      reason: 'Similar acidity and moisture profile',
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      expect(String(url)).toContain('/api/v1/cook-ai/substitutions')
      expect(init?.method).toBe('POST')
      const body = JSON.parse(String(init?.body))
      expect(body.missing_ingredient).toBe('sour cream')
      return new Response(JSON.stringify(mockSub), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const res = await fetchSubstitutions('sour cream')
    expect(res?.substitute_item).toBe('yogurt')
  })

  // Test pantry-to-plate generative meal planner.
  it('generatePantryMeal calls pantry-to-plate endpoint and receives recipe', async () => {
    const mockResponse = {
      title: 'Aloo Methi Stir Fry',
      description: 'Quick skillet meal',
      cuisine: 'North Indian',
      prep_time_minutes: 10,
      cook_time_minutes: 15,
      servings: 2,
      difficulty: 'easy',
      ingredients: [{ name: 'potato', quantity: 2, unit: 'count' }],
      steps: ['Chop potatoes', 'Cook with spices'],
      used_expiring_items: ['potato'],
      estimated_macros: { calories: 220, protein_g: 4, carbs_g: 35, fat_g: 8 },
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      expect(String(url)).toContain('/api/v1/cook-ai/pantry-to-plate')
      expect(init?.method).toBe('POST')
      const body = JSON.parse(String(init?.body))
      expect(body.dietary_preference).toBe('vegetarian')
      return new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const result = await generatePantryMeal({ dietary_preference: 'vegetarian', max_prep_time_minutes: 30 })
    expect(result.title).toBe('Aloo Methi Stir Fry')
    expect(result.cook_time_minutes).toBe(15)
  })

  // Test shopping list operations.
  it('manages shopping list: fetch, add, update, batch, and clear', async () => {
    const mockList = {
      items: [
        {
          id: 'shop_1',
          name: 'Paneer',
          quantity: 200,
          unit: 'g',
          is_purchased: false,
          created_at: '2026-11-05T00:00:00Z',
        },
      ],
    }

    // 1. Fetch
    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify(mockList), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any
    const list = await fetchShoppingList()
    expect(list.items.length).toBe(1)
    expect(list.items[0].name).toBe('Paneer')

    // 2. Add single item
    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('POST')
      return new Response(JSON.stringify({ ...mockList.items[0], id: 'shop_2', name: 'Curry Leaves' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any
    const added = await addShoppingListItem({ name: 'Curry Leaves', quantity: 1, unit: 'count' })
    expect(added.id).toBe('shop_2')

    // 3. Batch add
    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('POST')
      return new Response(
        JSON.stringify([
          { ...mockList.items[0], id: 'shop_b1', name: 'Mustard Seeds' },
          { ...mockList.items[0], id: 'shop_b2', name: 'Cumin Seeds' },
        ]),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }) as any
    const batchRes = await addShoppingListBatch([{ name: 'Mustard Seeds', quantity: 50, unit: 'g' }])
    expect(batchRes.length).toBe(2)

    // 4. Update item status
    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('PATCH')
      return new Response(JSON.stringify({ ...mockList.items[0], is_purchased: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any
    const updated = await updateShoppingListItem('shop_1', true)
    expect(updated.is_purchased).toBe(true)

    // 5. Delete item
    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('DELETE')
      return new Response(JSON.stringify({ status: 'deleted' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any
    const deleted = await deleteShoppingListItem('shop_1')
    expect(deleted.status).toBe('deleted')

    // 6. Clear purchased
    globalThis.fetch = mock(async (_url: any, init: any) => {
      expect(init?.method).toBe('POST')
      return new Response(JSON.stringify({ cleared_count: 3 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any
    const cleared = await clearPurchasedShoppingItems()
    expect(cleared.cleared_count).toBe(3)
  })
})
