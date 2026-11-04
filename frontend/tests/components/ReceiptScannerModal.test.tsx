/**
 * Unit tests for the ReceiptScannerModal component.
 */
import { describe, expect, it, mock } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { ReceiptScannerModal } from '../../src/components/ReceiptScannerModal'

describe('ReceiptScannerModal Component', () => {
  // Test modal invisibility when isOpen is false.
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <ReceiptScannerModal isOpen={false} onClose={() => {}} onConfirmed={() => {}} />
    )
    expect(container.innerHTML).toBe('')
  })

  // Test modal rendering when open.
  it('renders store platform selector and dropzone when open', () => {
    const { getByText } = render(
      <ReceiptScannerModal isOpen={true} onClose={() => {}} onConfirmed={() => {}} />
    )

    expect(getByText('Scan Receipt or Bill')).toBeDefined()
    expect(getByText('Blinkit')).toBeDefined()
    expect(getByText('Zepto')).toBeDefined()
    expect(getByText('Instamart')).toBeDefined()
    expect(getByText('Click to upload receipt or screenshot')).toBeDefined()
    expect(getByText('Extract Items with OCR')).toBeDefined()
  })

  // Test close handler.
  it('invokes onClose when close button is clicked', () => {
    const onCloseMock = mock(() => {})
    const { container } = render(
      <ReceiptScannerModal isOpen={true} onClose={onCloseMock} onConfirmed={() => {}} />
    )

    const closeBtn = container.querySelector('button')
    if (closeBtn) {
      fireEvent.click(closeBtn)
      expect(onCloseMock).toHaveBeenCalled()
    }
  })

  // Test selecting store platform.
  it('allows selecting different quick-commerce platform chips', () => {
    const { getByText } = render(
      <ReceiptScannerModal isOpen={true} onClose={() => {}} onConfirmed={() => {}} />
    )

    const zeptoBtn = getByText('Zepto')
    fireEvent.click(zeptoBtn)
    expect(zeptoBtn.className).toContain('bg-emerald-500')
  })
})
