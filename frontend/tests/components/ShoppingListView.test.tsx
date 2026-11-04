/**
 * Unit tests for the ShoppingListView component.
 */
import { describe, expect, it, beforeEach, afterEach, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { ShoppingListView } from '../../src/components/ShoppingListView'
import type { ShoppingListItem } from '../../src/types'

describe('ShoppingListView Component', () => {
  const originalFetch = globalThis.fetch

  const mockItems: ShoppingListItem[] = [
    {
      _id: 'item_1',
      name: 'Greek Yogurt',
      quantity: 2,
      unit: 'cup',
      checked: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      quick_links: {
        blinkit: 'https://blinkit.com/s/?q=Greek%20Yogurt',
        zepto: 'https://www.zeptonow.com/search?q=Greek%20Yogurt',
        instamart: 'https://www.swiggy.com/instamart/search?query=Greek%20Yogurt',
      },
    },
    {
      _id: 'item_2',
      name: 'Olive Oil',
      quantity: 1,
      unit: 'bottle',
      checked: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      quick_links: {},
    },
  ]

  beforeEach(() => {
    globalThis.fetch = mock(async (url: string | URL | Request, _init?: RequestInit) => {
      const urlStr = url.toString()
      if (urlStr.includes('/api/v1/shopping-list')) {
        return new Response(JSON.stringify(mockItems), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('{}', { status: 200 })
    }) as any
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('renders shopping items and quick-commerce order links', async () => {
    const { getByText, findByText } = render(<ShoppingListView />)

    expect(await findByText('Greek Yogurt')).toBeDefined()
    expect(getByText('Blinkit')).toBeDefined()
    expect(getByText('Zepto')).toBeDefined()
    expect(getByText('Instamart')).toBeDefined()
    expect(getByText('Purchased (1)')).toBeDefined()
  })

  it('toggles item checked state when checkbox clicked', async () => {
    let patchCalled = false
    globalThis.fetch = mock(async (_url: string | URL | Request, init?: RequestInit) => {
      if (init?.method === 'PATCH') {
        patchCalled = true
        return new Response(
          JSON.stringify({
            ...mockItems[0],
            checked: true,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new Response(JSON.stringify(mockItems), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { findByText, container } = render(<ShoppingListView />)
    await findByText('Greek Yogurt')

    const checkboxes = container.querySelectorAll('input[type="checkbox"]')
    expect(checkboxes.length).toBeGreaterThan(0)
    fireEvent.click(checkboxes[0])

    await waitFor(() => {
      expect(patchCalled).toBe(true)
    })
  })

  it('renders empty state when shopping list has no items', async () => {
    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { findByText } = render(<ShoppingListView />)
    expect(await findByText(/Your shopping list is empty/i)).toBeDefined()
  })
})
