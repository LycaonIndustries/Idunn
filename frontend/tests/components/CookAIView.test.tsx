/**
 * Unit tests for the CookAIView component.
 */
import { describe, expect, it, beforeEach, afterEach, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { CookAIView } from '../../src/components/CookAIView'
import type { PantryMatchResult, SubstitutionSuggestion } from '../../src/types'

describe('CookAIView Component', () => {
  const originalFetch = globalThis.fetch

  const mockMatches: PantryMatchResult[] = [
    { recipe_id: 'rec_101', recipe_title: 'Jeera Aloo', coverage_percentage: 100.0, matched_ingredients: ['potato', 'cumin'], missing_ingredients: [], expiry_urgency_score: 5.0, can_cook_now: true },
    { recipe_id: 'rec_102', recipe_title: 'Paneer Makhani', coverage_percentage: 50.0, matched_ingredients: ['butter'], missing_ingredients: ['paneer', 'heavy cream'], expiry_urgency_score: 0.0, can_cook_now: false },
  ]

  const mockSubstitutions: SubstitutionSuggestion[] = [
    { target_ingredient: 'heavy cream', substitute_name: 'greek yogurt', category: 'dairy', ratio: '1:1', in_pantry: true, notes: 'Thick and tangy' },
  ]

  beforeEach(() => {
    globalThis.fetch = mock(async (url: string | URL | Request) => {
      const urlStr = url.toString()
      if (urlStr.includes('/api/v1/cook-ai/what-can-i-cook')) {
        return new Response(JSON.stringify(mockMatches), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      if (urlStr.includes('/api/v1/cook-ai/substitutions')) {
        return new Response(JSON.stringify(mockSubstitutions), { status: 200, headers: { 'Content-Type': 'application/json' } })
      }
      return new Response('{}', { status: 200 })
    }) as any
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('renders ranked vault recipes and urgency badge', async () => {
    const { findByText, getByText } = render(<CookAIView />)
    expect(await findByText('Jeera Aloo')).toBeDefined()
    expect(getByText('100% in stock')).toBeDefined()
    expect(getByText('Ready to Cook')).toBeDefined()
    expect(getByText('Uses Expiring Items!')).toBeDefined()
    expect(getByText('Paneer Makhani')).toBeDefined()
    expect(getByText('50% in stock')).toBeDefined()
  })

  it('opens substitution modal with in-pantry recommendations', async () => {
    const { findByText, getByText } = render(<CookAIView />)
    expect(await findByText('Jeera Aloo')).toBeDefined()
    fireEvent.click(getByText('heavy cream (find sub)'))
    expect(await findByText('greek yogurt')).toBeDefined()
    expect(getByText('In Your Pantry!')).toBeDefined()
  })

  it('switches to Pantry to Plate Chef tab', async () => {
    const { getByText, findByText } = render(<CookAIView />)
    fireEvent.click(getByText('Pantry to Plate Chef'))
    expect(await findByText(/On-Demand Chef Recipe Synthesis/i)).toBeDefined()
    expect(getByText('Synthesize Custom Recipe from Pantry')).toBeDefined()
  })
})
