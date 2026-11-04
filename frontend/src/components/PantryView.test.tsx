/**
 * Tests for the PantryView inventory component.
 */
import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { PantryView } from './PantryView'
import type { InventoryItem } from '../types'

describe('PantryView Component', () => {
  const sampleItems: InventoryItem[] = [
    {
      id: 'item_1',
      name: 'Paneer',
      quantity: 500,
      unit: 'g',
      location: 'fridge',
      expiry_date: '2026-11-10T00:00:00.000Z',
      consumed: false,
      added_at: '2026-11-01T00:00:00.000Z',
      updated_at: '2026-11-01T00:00:00.000Z',
    },
    {
      id: 'item_2',
      name: 'Garam Masala',
      quantity: 2,
      unit: 'packet',
      location: 'spice_box',
      expiry_date: null,
      consumed: false,
      added_at: '2026-11-01T00:00:00.000Z',
      updated_at: '2026-11-01T00:00:00.000Z',
    },
  ]

  // Verify inventory items and locations render.
  it('renders tracked pantry items with quantities and locations', () => {
    const { getByText } = render(
      <PantryView
        items={sampleItems}
        loading={false}
        onRefresh={() => {}}
        onItemAdded={() => {}}
        onItemDeleted={() => {}}
      />
    )

    expect(getByText('Kitchen Pantry')).toBeDefined()
    expect(getByText(/2 items tracked/i)).toBeDefined()

    expect(getByText('Paneer')).toBeDefined()
    expect(getByText('500')).toBeDefined()
    expect(getByText('g')).toBeDefined()

    expect(getByText('Garam Masala')).toBeDefined()
    expect(getByText('2')).toBeDefined()
  })

  // Verify add modal opens when button is clicked.
  it('opens add item modal when Add Item button is clicked', () => {
    const { getByText, getByPlaceholderText } = render(
      <PantryView
        items={sampleItems}
        loading={false}
        onRefresh={() => {}}
        onItemAdded={() => {}}
        onItemDeleted={() => {}}
      />
    )

    const addButton = getByText('Add Item')
    fireEvent.click(addButton)

    expect(getByPlaceholderText(/e\.g\. Paneer, Onions, Toor Dal/i)).toBeDefined()
    expect(getByText('Save Item')).toBeDefined()
  })

  // Verify empty state display when no pantry items are logged.
  it('renders empty pantry message when item list is empty', () => {
    const { getByText } = render(
      <PantryView
        items={[]}
        loading={false}
        onRefresh={() => {}}
        onItemAdded={() => {}}
        onItemDeleted={() => {}}
      />
    )

    expect(getByText('Your pantry is empty')).toBeDefined()
    expect(getByText('Add Your First Item')).toBeDefined()
  })
})
