/**
 * Tests for the RecipeCard presentation component.
 */
import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { RecipeCard } from '../../src/components/RecipeCard'
import type { Recipe } from '../../src/types'

describe('RecipeCard Component', () => {
  const sampleRecipe: Recipe = {
    id: 'rec_101',
    title: 'Hyderabadi Biryani',
    description: 'Fragrant layered basmati rice with aromatic spices.',
    ingredients: [
      { name: 'Basmati Rice', quantity: 2, unit: 'katori' },
      { name: 'Ghee', quantity: 2, unit: 'tbsp' },
    ],
    steps: [
      { step_number: 1, instruction: 'Wash basmati rice thoroughly' },
      { step_number: 2, instruction: 'Cook with spices on dum' },
    ],
    cuisine_type: 'non_veg',
    difficulty: 'medium',
    prep_time_minutes: 20,
    cook_time_minutes: 40,
    servings: 4,
    tags: ['rice', 'royal', 'dinner'],
  }

  // Verify core recipe information renders correctly for user.
  it('renders recipe title, time, and tag metadata', () => {
    const handleSelect = mock(() => {})
    const handleDelete = mock(() => {})

    const { getByText } = render(
      <RecipeCard
        recipe={sampleRecipe}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />
    )

    expect(getByText('Hyderabadi Biryani')).toBeDefined()
    expect(getByText('Fragrant layered basmati rice with aromatic spices.')).toBeDefined()
    expect(getByText(/60\s*min/i)).toBeDefined()
    expect(getByText(/medium/i)).toBeDefined()
    expect(getByText('NON_VEG')).toBeDefined()
  })

  // Verify selecting card invokes onSelect callback.
  it('invokes onSelect callback when recipe card is clicked', () => {
    const handleSelect = mock(() => {})
    const handleDelete = mock(() => {})

    const { getByText } = render(
      <RecipeCard
        recipe={sampleRecipe}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />
    )

    const card = getByText('Hyderabadi Biryani').closest('div')
    expect(card).toBeDefined()
    if (card) {
      fireEvent.click(card)
    }

    expect(handleSelect).toHaveBeenCalledWith(sampleRecipe)
  })

  // Verify delete button requires user confirmation before invoking onDelete.
  it('invokes onDelete when delete button is confirmed', () => {
    const handleSelect = mock(() => {})
    const handleDelete = mock(() => {})

    // Mock browser window.confirm to return true.
    const originalConfirm = window.confirm
    window.confirm = () => true

    const { getByTitle } = render(
      <RecipeCard
        recipe={sampleRecipe}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />
    )

    const deleteButton = getByTitle('Delete recipe')
    expect(deleteButton).toBeDefined()
    fireEvent.click(deleteButton)

    expect(handleDelete).toHaveBeenCalledWith('rec_101')

    window.confirm = originalConfirm
  })
})
