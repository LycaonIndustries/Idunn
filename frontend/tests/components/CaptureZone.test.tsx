/**
 * Tests for the CaptureZone component.
 * Verifies accessible dropzone keyboard navigation (Enter/Space) and file input triggering.
 */
import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { CaptureZone } from '../../src/components/CaptureZone'

describe('CaptureZone Component Accessibility', () => {
  it('triggers file selection when Enter or Space is pressed on image dropzone', () => {
    const handleRecipeSaved = mock(() => {})

    const { getByLabelText } = render(
      <CaptureZone onRecipeSaved={handleRecipeSaved} isByokConfigured={true} />
    )

    const dropzone = getByLabelText('Upload cookbook photo or recipe screenshot')
    expect(dropzone).toBeDefined()
    expect(dropzone.getAttribute('role')).toBe('button')
    expect(dropzone.getAttribute('tabIndex')).toBe('0')

    // Find hidden file input
    const fileInput = dropzone.querySelector('input[type="file"]') as HTMLInputElement
    expect(fileInput).toBeDefined()

    const clickSpy = mock(() => {})
    fileInput.click = clickSpy

    // Press Enter on dropzone
    fireEvent.keyDown(dropzone, { key: 'Enter' })
    expect(clickSpy).toHaveBeenCalledTimes(1)

    // Press Space on dropzone
    fireEvent.keyDown(dropzone, { key: ' ' })
    expect(clickSpy).toHaveBeenCalledTimes(2)
  })
})
