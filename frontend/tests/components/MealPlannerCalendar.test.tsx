/**
 * Unit tests for the MealPlannerCalendar component.
 */
import { describe, expect, it, beforeEach, afterEach, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent, waitFor } from '@testing-library/react'
import { MealPlannerCalendar } from '../../src/components/MealPlannerCalendar'
import type { Recipe, WeeklyMealPlan } from '../../src/types'

describe('MealPlannerCalendar Component', () => {
  const originalFetch = globalThis.fetch
  const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
  const mockPlan: WeeklyMealPlan = {
    _id: 'plan_123',
    owner_id: 'test_user',
    week_start_date: '2026-11-09',
    days: DAYS.map((d, i) => ({
      date: `2026-11-0${9 + i}`,
      day_of_week: d,
      slots: [
        { meal_type: 'breakfast' as const, recipe_id: d === 'monday' ? 'rec_1' : undefined, recipe_title: d === 'monday' ? 'Masala Omelette' : undefined, servings_multiplier: 1.0 },
        { meal_type: 'lunch' as const, servings_multiplier: 1.0 },
        { meal_type: 'dinner' as const, servings_multiplier: 1.0 },
      ],
    })),
  }

  const mockRecipes: Recipe[] = [
    { _id: 'rec_1', title: 'Masala Omelette', description: 'Quick egg breakfast', prep_time_minutes: 5, cook_time_minutes: 5, servings: 2, cuisine_type: 'Indian', ingredients: [{ name: 'Eggs', quantity: 2, unit: 'whole' }], steps: [{ step_number: 1, instruction: 'Beat eggs and fry.' }], tags: ['breakfast'], created_at: '', updated_at: '' },
    { _id: 'rec_2', title: 'Paneer Butter Masala', description: 'Rich tomato gravy', prep_time_minutes: 15, cook_time_minutes: 20, servings: 4, cuisine_type: 'North Indian', ingredients: [{ name: 'Paneer', quantity: 200, unit: 'g' }], steps: [{ step_number: 1, instruction: 'Cook gravy.' }], tags: ['dinner'], created_at: '', updated_at: '' },
  ]

  let lastPatchPayload: any = null

  beforeEach(() => {
    lastPatchPayload = null
    globalThis.fetch = mock(async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = url.toString()
      if (urlStr.includes('/api/v1/planner') && init?.method === 'PATCH') {
        lastPatchPayload = JSON.parse(init.body as string)
      }
      return new Response(JSON.stringify(mockPlan), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }) as any
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  it('renders weekly meal planner calendar with 7 days and meal slots', async () => {
    const { findByText, getAllByText } = render(<MealPlannerCalendar recipes={mockRecipes} />)
    expect(await findByText('Weekly Meal Planner')).toBeDefined()
    expect(getAllByText('monday').length).toBeGreaterThan(0)
    expect(getAllByText('sunday').length).toBeGreaterThan(0)
    expect(await findByText('Masala Omelette')).toBeDefined()
  })

  it('opens recipe picker drawer and assigns recipe to empty slot', async () => {
    const { findByText, getByPlaceholderText } = render(<MealPlannerCalendar recipes={mockRecipes} />)
    expect(await findByText('Weekly Meal Planner')).toBeDefined()

    const addButtons = document.querySelectorAll('button[aria-label="Add recipe to monday lunch"]')
    expect(addButtons.length).toBe(1)
    fireEvent.click(addButtons[0])

    expect(await findByText('Assign Recipe (monday lunch)')).toBeDefined()
    expect(await findByText('Paneer Butter Masala')).toBeDefined()

    const searchInput = getByPlaceholderText('Search by title, cuisine, or ingredient...')
    fireEvent.change(searchInput, { target: { value: 'Paneer' } })

    const selectButtons = document.querySelectorAll('button')
    const paneerCard = Array.from(selectButtons).find((b) => b.textContent?.includes('Paneer Butter Masala'))
    expect(paneerCard).toBeDefined()
    fireEvent.click(paneerCard!)

    await waitFor(() => {
      expect(lastPatchPayload).not.toBeNull()
      expect(lastPatchPayload.day_of_week).toBe('monday')
      expect(lastPatchPayload.meal_type).toBe('lunch')
      expect(lastPatchPayload.recipe_title).toBe('Paneer Butter Masala')
    })
  })

  it('clears an assigned recipe slot when remove button is clicked', async () => {
    const { findByLabelText } = render(<MealPlannerCalendar recipes={mockRecipes} />)
    const removeButton = await findByLabelText('Remove recipe from monday breakfast')
    fireEvent.click(removeButton)

    await waitFor(() => {
      expect(lastPatchPayload).not.toBeNull()
      expect(lastPatchPayload.day_of_week).toBe('monday')
      expect(lastPatchPayload.meal_type).toBe('breakfast')
      expect(lastPatchPayload.recipe_id).toBeNull()
    })
  })

  it('adjusts serving scale multiplier', async () => {
    const { findByLabelText } = render(<MealPlannerCalendar recipes={mockRecipes} />)
    const scaleSelect = await findByLabelText('Serving scale for monday breakfast')
    fireEvent.change(scaleSelect, { target: { value: '2' } })

    await waitFor(() => {
      expect(lastPatchPayload).not.toBeNull()
      expect(lastPatchPayload.servings_multiplier).toBe(2)
    })
  })
})
