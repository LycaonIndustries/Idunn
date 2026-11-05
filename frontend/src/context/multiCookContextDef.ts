import { createContext } from 'react'
import type { Recipe } from '../types'

export interface ActiveCookTimer {
  id: string
  label: string
  remainingSeconds: number
  totalSeconds: number
  isRunning: boolean
}

export interface ActiveCookItem {
  recipe: Recipe
  activeStep: number | null
  completedSteps: Record<number, boolean>
  timers: ActiveCookTimer[]
}

export interface MultiCookContextValue {
  sessions: ActiveCookItem[]
  activeRecipeId: string | null
  startCooking: (recipe: Recipe) => void
  stopCooking: (recipeId: string) => void
  setActiveRecipeId: (recipeId: string) => void
  setActiveStep: (recipeId: string, stepNumber: number | null) => void
  toggleStepCompleted: (recipeId: string, stepNumber: number) => void
  addTimer: (recipeId: string, label: string, durationSeconds: number) => void
  toggleTimer: (recipeId: string, timerId: string) => void
  resetTimer: (recipeId: string, timerId: string) => void
}

export const DEFAULT_VALUE: MultiCookContextValue = {
  sessions: [],
  activeRecipeId: null,
  startCooking: () => {},
  stopCooking: () => {},
  setActiveRecipeId: () => {},
  setActiveStep: () => {},
  toggleStepCompleted: () => {},
  addTimer: () => {},
  toggleTimer: () => {},
  resetTimer: () => {},
}

export const STORAGE_KEY = 'idunn_multi_cook_v1'
export const MultiCookContext = createContext<MultiCookContextValue>(DEFAULT_VALUE)
