/**
 * Tests for the RecipeDetailPage component.
 * Verifies clipboard resilience, destructive delete guards, and keyboard accessibility.
 */
import { describe, expect, it, mock, beforeEach, afterEach } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { RecipeDetailPage } from '../../src/components/RecipeDetailPage'
import type { Recipe } from '../../src/types'

describe('RecipeDetailPage Component', () => {
  const sampleRecipe: Recipe = {
    id: 'rec_detail_1',
    title: 'Butter Chicken',
    description: 'Rich tomato creamy curry with tender chicken pieces.',
    ingredients: [
      { name: 'Chicken', quantity: 500, unit: 'g' },
      { name: 'Butter', quantity: 50, unit: 'g' },
    ],
    steps: [
      { step_number: 1, instruction: 'Marinate chicken with yogurt and spices.' },
      { step_number: 2, instruction: 'Simmer gravy with butter and cream.' },
    ],
    servings: 4,
    prep_time_minutes: 15,
    cook_time_minutes: 30,
  }

  let originalClipboard: Clipboard
  let originalConfirm: typeof window.confirm
  let originalPrompt: typeof window.prompt

  beforeEach(() => {
    originalClipboard = navigator.clipboard
    originalConfirm = window.confirm
    originalPrompt = window.prompt
  })

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      configurable: true,
      writable: true,
    })
    window.confirm = originalConfirm
    window.prompt = originalPrompt
  })

  it('handles clipboard failure gracefully without uncaught rejection', async () => {
    // Mock navigator.clipboard.writeText to reject (e.g. permission denied or insecure context)
    const writeTextMock = mock(() => Promise.reject(new Error('Permission denied')))
    const promptMock = mock(() => null)
    window.prompt = promptMock

    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      configurable: true,
      writable: true,
    })

    const onBack = mock(() => {})
    const onDelete = mock(() => {})

    const { getByText } = render(
      <RecipeDetailPage
        recipe={sampleRecipe}
        onBack={onBack}
        onDelete={onDelete}
      />
    )

    const shareButton = getByText('Share').closest('button')
    expect(shareButton).toBeDefined()
    if (shareButton) {
      fireEvent.click(shareButton)
    }

    // Wait for the async handler to complete fallback safely
    await Promise.resolve()
    expect(writeTextMock).toHaveBeenCalled()
    expect(promptMock).toHaveBeenCalled()
  })

  it('guards against double-submit on delete action and disables delete button during processing', async () => {
    window.confirm = () => true
    const onBack = mock(() => {})

    let resolveDelete: () => void = () => {}
    const onDeletePromise = new Promise<void>((resolve) => {
      resolveDelete = resolve
    })
    const onDelete = mock(() => onDeletePromise)

    const { getByTitle } = render(
      <RecipeDetailPage
        recipe={sampleRecipe}
        onBack={onBack}
        onDelete={onDelete}
      />
    )

    const deleteButton = getByTitle('Delete recipe')
    expect(deleteButton).toBeDefined()

    // Trigger first delete click
    fireEvent.click(deleteButton)
    expect(onDelete).toHaveBeenCalledTimes(1)

    // Button should now be disabled and reflect pending deletion state
    expect(deleteButton.hasAttribute('disabled')).toBe(true)

    // Second click should be ignored due to deleting guard
    fireEvent.click(deleteButton)
    expect(onDelete).toHaveBeenCalledTimes(1)

    // Resolve deletion
    resolveDelete()
    await Promise.resolve()
  })

  it('toggles ingredient checklist via Enter or Space key', () => {
    const onBack = mock(() => {})
    const onDelete = mock(() => {})

    const { getByLabelText } = render(
      <RecipeDetailPage
        recipe={sampleRecipe}
        onBack={onBack}
        onDelete={onDelete}
      />
    )

    const ingredientRow = getByLabelText('Toggle ingredient Chicken')
    expect(ingredientRow).toBeDefined()
    expect(ingredientRow.getAttribute('role')).toBe('button')
    expect(ingredientRow.getAttribute('tabIndex')).toBe('0')

    // Press Enter to toggle
    fireEvent.keyDown(ingredientRow, { key: 'Enter' })
    expect(ingredientRow.className).toContain('opacity-50')

    // Press Space to toggle back
    fireEvent.keyDown(ingredientRow, { key: ' ' })
    expect(ingredientRow.className).not.toContain('opacity-50')
  })
})
