/**
 * Tests for the ShoppingListView component.
 */

import { describe, expect, it, afterEach, mock } from 'bun:test'
import React from 'react'
import { render, waitFor, fireEvent } from '@testing-library/react'
import { ShoppingListView } from '../../src/components/ShoppingListView'

describe('ShoppingListView Component', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  // Test empty state
  it('renders empty shopping list message when no items exist', async () => {
    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { getByText } = render(<ShoppingListView />)

    await waitFor(() => {
      expect(getByText('Your shopping list is empty')).toBeDefined()
    })
  })

  // Test rendering active and completed items
  it('renders shopping items with quick-commerce action links', async () => {
    const mockItems = [
      {
        id: 'shop_1',
        name: 'Curry Leaves',
        quantity: 1,
        unit: 'count',
        is_purchased: false,
        recipe_id: 'rec_sambar',
      },
      {
        id: 'shop_2',
        name: 'Mustard Seeds',
        quantity: 100,
        unit: 'g',
        is_purchased: true,
      },
    ]

    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify({ items: mockItems }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { getByText } = render(<ShoppingListView />)

    await waitFor(() => {
      expect(getByText('Curry Leaves')).toBeDefined()
      expect(getByText('From Recipe')).toBeDefined()
      expect(getByText('Mustard Seeds')).toBeDefined()
      expect(getByText('Instant Quick-Commerce Restock')).toBeDefined()
      expect(getByText('Blinkit')).toBeDefined()
      expect(getByText('Zepto')).toBeDefined()
      expect(getByText('Instamart')).toBeDefined()
    })
  })

  // Test adding an item through the quick add form
  it('submits new item and renders it in list', async () => {
    globalThis.fetch = mock(async (url: any, init: any) => {
      if (init?.method === 'POST') {
        const body = JSON.parse(String(init.body))
        return new Response(
          JSON.stringify({
            id: 'shop_new',
            name: body.name,
            quantity: body.quantity,
            unit: body.unit,
            is_purchased: false,
            category: 'other',
          }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { getByPlaceholderText, getByText } = render(<ShoppingListView />)

    await waitFor(() => {
      expect(getByPlaceholderText(/Add ingredient or item/i)).toBeDefined()
    })

    const input = getByPlaceholderText(/Add ingredient or item/i)
    fireEvent.change(input, { target: { value: 'Kasuri Methi' } })

    const form = input.closest('form')!
    fireEvent.submit(form)

    await waitFor(() => {
      expect(getByText('Kasuri Methi')).toBeDefined()
    })
  })
})
