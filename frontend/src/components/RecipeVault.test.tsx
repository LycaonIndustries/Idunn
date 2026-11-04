/**
 * Tests for the RecipeVault search and filtering grid component.
 */
import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { RecipeVault } from './RecipeVault'
import type { Recipe } from '../types'

describe('RecipeVault Component', () => {
  const recipes: Recipe[] = [
    {
      id: 'rec_veg',
      title: 'Palak Paneer',
      description: 'Spinach and cottage cheese gravy.',
      ingredients: [{ name: 'Paneer' }, { name: 'Spinach' }],
      steps: [{ step_number: 1, instruction: 'Blanch spinach' }],
      cuisine_type: 'veg',
      difficulty: 'easy',
      tags: ['curry', 'healthy'],
    },
    {
      id: 'rec_nonveg',
      title: 'Chicken Chettinad',
      description: 'Spicy South Indian chicken curry.',
      ingredients: [{ name: 'Chicken' }, { name: 'Fennel' }],
      steps: [{ step_number: 1, instruction: 'Roast whole spices' }],
      cuisine_type: 'non_veg',
      difficulty: 'medium',
      tags: ['chettinad', 'spicy'],
    },
  ]

  // Verify full list renders initially.
  it('renders all recipes by default', () => {
    const { getByText } = render(
      <RecipeVault
        recipes={recipes}
        loading={false}
        onRefresh={() => {}}
        onDeleteRecipe={() => {}}
        onNavigateToCapture={() => {}}
      />
    )

    expect(getByText('Palak Paneer')).toBeDefined()
    expect(getByText('Chicken Chettinad')).toBeDefined()
    expect(getByText('2 recipes in your personal library')).toBeDefined()
  })

  // Verify search text filters recipes instantaneously.
  it('filters recipes by search query matching ingredient or title', () => {
    const { getByText, queryByText, getByPlaceholderText } = render(
      <RecipeVault
        recipes={recipes}
        loading={false}
        onRefresh={() => {}}
        onDeleteRecipe={() => {}}
        onNavigateToCapture={() => {}}
      />
    )

    const searchInput = getByPlaceholderText(/Search recipes, ingredients/i)
    fireEvent.change(searchInput, { target: { value: 'Paneer' } })

    expect(getByText('Palak Paneer')).toBeDefined()
    expect(queryByText('Chicken Chettinad')).toBeNull()
  })

  // Verify vegetarian filter hides non-veg items.
  it('filters by pure veg dietary filter chip', () => {
    const { getByText, queryByText } = render(
      <RecipeVault
        recipes={recipes}
        loading={false}
        onRefresh={() => {}}
        onDeleteRecipe={() => {}}
        onNavigateToCapture={() => {}}
      />
    )

    const vegButton = getByText('Pure Veg')
    fireEvent.click(vegButton)

    expect(getByText('Palak Paneer')).toBeDefined()
    expect(queryByText('Chicken Chettinad')).toBeNull()
  })

  // Verify empty state display when search yields no matches.
  it('renders empty state when search finds no results', () => {
    const { getByText, getByPlaceholderText } = render(
      <RecipeVault
        recipes={recipes}
        loading={false}
        onRefresh={() => {}}
        onDeleteRecipe={() => {}}
        onNavigateToCapture={() => {}}
      />
    )

    const searchInput = getByPlaceholderText(/Search recipes, ingredients/i)
    fireEvent.change(searchInput, { target: { value: 'Nonexistent Recipe XYZ' } })

    expect(getByText('No recipes found')).toBeDefined()
    expect(getByText('Try adjusting your search query or filter.')).toBeDefined()
  })
})
