/**
 * Tests for the top navigation bar component.
 */
import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { Navbar } from './Navbar'

describe('Navbar Component', () => {
  // Verify branding and navigation items render properly for the user.
  it('renders application branding and active tabs', () => {
    const handleTabChange = mock(() => {})

    const { getByText } = render(
      <Navbar
        activeTab="capture"
        setActiveTab={handleTabChange}
        recipeCount={5}
        pantryCount={12}
      />
    )

    // Brand title must be visible to identify the application.
    expect(getByText('Iðunn')).toBeDefined()
    expect(getByText('v0.1.0')).toBeDefined()

    // Tab badges must display real inventory and recipe counts.
    expect(getByText('5')).toBeDefined()
    expect(getByText('12')).toBeDefined()
  })

  // Verify tab clicks invoke parent callback to drive view routing.
  it('triggers setActiveTab when navigation tab is clicked', () => {
    const handleTabChange = mock(() => {})

    const { getByText } = render(
      <Navbar
        activeTab="capture"
        setActiveTab={handleTabChange}
        recipeCount={2}
        pantryCount={4}
      />
    )

    // User click on Pantry tab must notify parent component.
    const pantryButton = getByText('Pantry').closest('button')
    expect(pantryButton).toBeDefined()
    if (pantryButton) {
      fireEvent.click(pantryButton)
    }

    expect(handleTabChange).toHaveBeenCalledWith('pantry')
  })
})
