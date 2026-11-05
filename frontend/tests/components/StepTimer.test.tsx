import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import { StepTimer } from '../../src/components/StepTimer'
import { extractStepDuration } from '../../src/utils/duration'

describe('StepTimer Component & extractStepDuration', () => {
  it('correctly extracts step duration in seconds from instructions', () => {
    expect(extractStepDuration('Simmer the gravy for 10 minutes', null)).toBe(600)
    expect(extractStepDuration('Boil for 5 mins over medium flame', null)).toBe(300)
    expect(extractStepDuration('Rest dough for 30 seconds', null)).toBe(30)
    expect(extractStepDuration('Mix thoroughly', 15)).toBe(900)
    expect(extractStepDuration('Garnish with coriander leaves', null)).toBeNull()
  })

  it('renders initial formatted time and label', () => {
    const { getByText, getByLabelText } = render(
      <StepTimer durationSeconds={125} label="Boil Dal" />
    )

    expect(getByText('Boil Dal:')).toBeDefined()
    expect(getByText('2:05')).toBeDefined()
    expect(getByLabelText('Start timer')).toBeDefined()
  })

  it('toggles running and pausing state when button clicked', () => {
    const { getByLabelText } = render(<StepTimer durationSeconds={60} />)

    const startBtn = getByLabelText('Start timer')
    fireEvent.click(startBtn)
    expect(getByLabelText('Pause timer')).toBeDefined()

    const pauseBtn = getByLabelText('Pause timer')
    fireEvent.click(pauseBtn)
    expect(getByLabelText('Start timer')).toBeDefined()
  })

  it('resets timer when reset button clicked', () => {
    const { getByLabelText, getByText } = render(<StepTimer durationSeconds={90} />)

    fireEvent.click(getByLabelText('Start timer'))
    fireEvent.click(getByLabelText('Reset timer'))

    expect(getByLabelText('Start timer')).toBeDefined()
    expect(getByText('1:30')).toBeDefined()
  })
})
