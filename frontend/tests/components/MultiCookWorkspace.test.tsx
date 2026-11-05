import { describe, expect, it, mock } from 'bun:test'
import { fireEvent, render, screen } from '@testing-library/react'
import { MultiCookProvider } from '../../src/context/MultiCookContext'
import { useMultiCook } from '../../src/context/useMultiCook'
import { MultiCookWorkspace } from '../../src/components/MultiCookWorkspace'
import type { Recipe } from '../../src/types'

const recipeA: Recipe = {
  _id: 'rec_dal',
  title: 'Tadka Dal',
  ingredients: [],
  steps: [{ step_number: 1, instruction: 'Boil dal' }, { step_number: 2, instruction: 'Prepare tadka' }],
}

const recipeB: Recipe = {
  _id: 'rec_rice',
  title: 'Jeera Rice',
  ingredients: [],
  steps: [{ step_number: 1, instruction: 'Wash rice' }],
}

function MultiCookTestHarness({ onSelect }: { onSelect: (r: Recipe) => void }) {
  const { startCooking, addTimer } = useMultiCook()

  return (
    <div>
      <button
        onClick={() => {
          startCooking(recipeA)
          startCooking(recipeB)
          addTimer('rec_dal', 'Simmer', 300)
        }}
      >
        Start Both
      </button>
      <MultiCookWorkspace onSelectRecipe={onSelect} />
    </div>
  )
}

describe('MultiCookWorkspace Component', () => {
  it('does not render when fewer than two dishes are active', () => {
    const onSelect = mock(() => {})
    render(
      <MultiCookProvider>
        <MultiCookWorkspace onSelectRecipe={onSelect} />
      </MultiCookProvider>
    )

    expect(screen.queryByText(/Multi-Cook:/i)).toBeNull()
  })

  it('renders dish tabs and timer badges when multi-cook is active', () => {
    const onSelect = mock(() => {})
    render(
      <MultiCookProvider>
        <MultiCookTestHarness onSelect={onSelect} />
      </MultiCookProvider>
    )

    fireEvent.click(screen.getByText('Start Both'))

    expect(screen.getByText(/Multi-Cook:/i)).toBeDefined()
    expect(screen.getByText('Tadka Dal')).toBeDefined()
    expect(screen.getByText('Jeera Rice')).toBeDefined()
    expect(screen.getAllByText('Step 1').length).toBe(2)
    expect(screen.getByText(/300s/)).toBeDefined()
  })

  it('switches active dish when tab is clicked', () => {
    const onSelect = mock(() => {})
    render(
      <MultiCookProvider>
        <MultiCookTestHarness onSelect={onSelect} />
      </MultiCookProvider>
    )

    fireEvent.click(screen.getByText('Start Both'))
    fireEvent.click(screen.getByText('Jeera Rice'))

    expect(onSelect).toHaveBeenCalledTimes(1)
  })

  it('removes dish when close button is clicked', () => {
    const onSelect = mock(() => {})
    render(
      <MultiCookProvider>
        <MultiCookTestHarness onSelect={onSelect} />
      </MultiCookProvider>
    )

    fireEvent.click(screen.getByText('Start Both'))
    const closeButtons = screen.getAllByTitle('Close dish from multi-cook')
    fireEvent.click(closeButtons[0])

    // After closing one of the two dishes, multi-cook bar collapses because length <= 1.
    expect(screen.queryByText(/Multi-Cook:/i)).toBeNull()
  })
})
