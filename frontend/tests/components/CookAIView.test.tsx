/**
 * Tests for the CookAIView component.
 */

import { describe, expect, it, afterEach, mock } from 'bun:test'
import React from 'react'
import { render, waitFor, fireEvent } from '@testing-library/react'
import { CookAIView } from '../../src/components/CookAIView'

describe('CookAIView Component', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  // Test rendering recipe match results
  it('renders ranked recipe matches with coverage badges and expiry boosts', async () => {
    const mockMatches = [
      {
        recipe_id: 'rec_1',
        recipe_title: 'Paneer Butter Masala',
        coverage_percentage: 100,
        can_cook_now: true,
        matched_ingredients: ['paneer', 'butter', 'tomato'],
        missing_ingredients: [],
        expiry_urgency_score: 8,
        expiring_ingredients_used: ['paneer'],
      },
      {
        recipe_id: 'rec_2',
        recipe_title: 'Dal Tadka',
        coverage_percentage: 67,
        can_cook_now: false,
        matched_ingredients: ['toor dal', 'garlic'],
        missing_ingredients: ['ghee'],
        expiry_urgency_score: 0,
        expiring_ingredients_used: [],
      },
    ]

    globalThis.fetch = mock(async () => {
      return new Response(JSON.stringify(mockMatches), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const handleSelectRecipe = mock(() => {})
    const { getByText } = render(
      <CookAIView onSelectRecipe={handleSelectRecipe} />
    )

    await waitFor(() => {
      expect(getByText('Paneer Butter Masala')).toBeDefined()
      expect(getByText('Ready to Cook')).toBeDefined()
      expect(getByText('Uses soon-to-expire stock')).toBeDefined()
      expect(getByText('Dal Tadka')).toBeDefined()
      expect(getByText('Missing 1')).toBeDefined()
    })

    // Clicking recipe invokes callback
    const recipeTitle = getByText('Paneer Butter Masala')
    fireEvent.click(recipeTitle)
    expect(handleSelectRecipe).toHaveBeenCalledWith('rec_1')
  })

  // Test opening substitution modal on missing ingredient click
  it('opens substitution modal and checks in-stock replacements', async () => {
    const mockMatches = [
      {
        recipe_id: 'rec_2',
        recipe_title: 'Dal Tadka',
        match_percentage: 67,
        can_cook_now: false,
        matched_ingredients: ['toor dal', 'garlic'],
        missing_ingredients: ['ghee'],
        expiry_urgency_score: 0,
        expiring_ingredients_used: [],
      },
    ]

    const mockSub = {
      missing_ingredient: 'ghee',
      substitute_item: 'mustard oil',
      ratio_or_amount: '1:1 ratio',
      reason: 'Traditional Indian cooking fat alternative',
    }

    globalThis.fetch = mock(async (url: any) => {
      if (String(url).includes('/substitutions')) {
        return new Response(JSON.stringify(mockSub), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify(mockMatches), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { getByText } = render(
      <CookAIView onSelectRecipe={() => {}} />
    )

    await waitFor(() => {
      expect(getByText('ghee')).toBeDefined()
    })

    // Click the missing ingredient tag
    const missingPill = getByText('ghee')
    fireEvent.click(missingPill)

    await waitFor(() => {
      expect(getByText('In-Stock Substitute Available!')).toBeDefined()
      expect(getByText('mustard oil')).toBeDefined()
      expect(getByText('Blinkit ⚡')).toBeDefined()
    })
  })

  // Test Pantry to Plate tab switching and generation
  it('switches to Pantry-to-Plate generator and creates a meal', async () => {
    const mockMealResponse = {
      title: 'Skillet Jeera Aloo',
      description: 'Quick spiced cumin potatoes',
      cuisine: 'North Indian',
      prep_time_minutes: 5,
      cook_time_minutes: 15,
      servings: 2,
      difficulty: 'easy',
      ingredients: [
        { item: 'potato', amount: 3, unit: 'count' },
        { item: 'cumin', amount: 1, unit: 'tsp' },
      ],
      steps: ['Boil potatoes', 'Toss with cumin and ghee'],
      used_expiring_items: ['potato'],
      estimated_macros: { calories: 180, protein_g: 3, carbs_g: 30, fat_g: 6 },
    }

    globalThis.fetch = mock(async (url: any, init: any) => {
      if (init?.method === 'POST') {
        return new Response(JSON.stringify(mockMealResponse), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const { getByText } = render(
      <CookAIView onSelectRecipe={() => {}} />
    )

    // Switch to Pantry to Plate subtab
    const generatorTab = getByText('Pantry-to-Plate Chef')
    fireEvent.click(generatorTab)

    expect(getByText('Generate Recipe')).toBeDefined()

    // Click Generate Recipe
    const generateBtn = getByText('Generate Recipe')
    fireEvent.click(generateBtn)

    await waitFor(() => {
      expect(getByText('Skillet Jeera Aloo')).toBeDefined()
      expect(getByText('Quick spiced cumin potatoes')).toBeDefined()
      expect(getByText('Save to Vault')).toBeDefined()
    })
  })
})
