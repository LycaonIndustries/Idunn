import React, { createContext, useContext, useEffect, useState } from 'react'
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

interface MultiCookContextValue {
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

const DEFAULT_VALUE: MultiCookContextValue = {
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

const STORAGE_KEY = 'idunn_multi_cook_v1'
const MultiCookContext = createContext<MultiCookContextValue>(DEFAULT_VALUE)

export function MultiCookProvider({ children }: { children: React.ReactNode }) {
  // Load saved multi-dish cooking sessions from local storage.
  const [sessions, setSessions] = useState<ActiveCookItem[]>(() => {
    if (typeof window === 'undefined') return []
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })

  const [activeRecipeId, setActiveRecipeId] = useState<string | null>(() => {
    return sessions.length > 0 ? (sessions[0].recipe.id || sessions[0].recipe._id || null) : null
  })

  // Synchronize active session state to storage to protect against page refreshes.
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    } catch {
      // Ignore quota storage limits gracefully.
    }
  }, [sessions])

  // Decrement all active cooking timers concurrently across all dishes.
  useEffect(() => {
    const hasRunningTimers = sessions.some((s) => s.timers.some((t) => t.isRunning))
    if (!hasRunningTimers) return

    const timer = setInterval(() => {
      setSessions((prev) =>
        prev.map((item) => ({
          ...item,
          timers: item.timers.map((t) => {
            if (!t.isRunning) return t
            if (t.remainingSeconds <= 1) {
              return { ...t, remainingSeconds: 0, isRunning: false }
            }
            return { ...t, remainingSeconds: t.remainingSeconds - 1 }
          }),
        }))
      )
    }, 1000)

    return () => clearInterval(timer)
  }, [sessions])

  const startCooking = (recipe: Recipe) => {
    const rId = recipe.id || recipe._id || ''
    setSessions((prev) => {
      if (prev.some((item) => (item.recipe.id || item.recipe._id) === rId)) {
        return prev
      }
      // Maximum 3 simultaneous dishes to fit domestic Indian burner capacity.
      const capped = prev.length >= 3 ? prev.slice(1) : prev
      return [
        ...capped,
        {
          recipe,
          activeStep: recipe.steps && recipe.steps.length > 0 ? recipe.steps[0].step_number : 1,
          completedSteps: {},
          timers: [],
        },
      ]
    })
    setActiveRecipeId(rId)
  }

  const stopCooking = (recipeId: string) => {
    setSessions((prev) => {
      const filtered = prev.filter((item) => (item.recipe.id || item.recipe._id) !== recipeId)
      if (activeRecipeId === recipeId) {
        setActiveRecipeId(
          filtered.length > 0 ? (filtered[0].recipe.id || filtered[0].recipe._id || null) : null
        )
      }
      return filtered
    })
  }

  const setActiveStep = (recipeId: string, stepNumber: number | null) => {
    setSessions((prev) =>
      prev.map((item) =>
        (item.recipe.id || item.recipe._id) === recipeId
          ? { ...item, activeStep: stepNumber }
          : item
      )
    )
  }

  const toggleStepCompleted = (recipeId: string, stepNumber: number) => {
    setSessions((prev) =>
      prev.map((item) => {
        if ((item.recipe.id || item.recipe._id) !== recipeId) return item
        const current = Boolean(item.completedSteps[stepNumber])
        return {
          ...item,
          completedSteps: { ...item.completedSteps, [stepNumber]: !current },
        }
      })
    )
  }

  const addTimer = (recipeId: string, label: string, durationSeconds: number) => {
    const newTimer: ActiveCookTimer = {
      id: Math.random().toString(36).substring(2, 9),
      label,
      remainingSeconds: durationSeconds,
      totalSeconds: durationSeconds,
      isRunning: true,
    }
    setSessions((prev) =>
      prev.map((item) =>
        (item.recipe.id || item.recipe._id) === recipeId
          ? { ...item, timers: [...item.timers, newTimer] }
          : item
      )
    )
  }

  const toggleTimer = (recipeId: string, timerId: string) => {
    setSessions((prev) =>
      prev.map((item) =>
        (item.recipe.id || item.recipe._id) === recipeId
          ? {
              ...item,
              timers: item.timers.map((t) =>
                t.id === timerId ? { ...t, isRunning: !t.isRunning } : t
              ),
            }
          : item
      )
    )
  }

  const resetTimer = (recipeId: string, timerId: string) => {
    setSessions((prev) =>
      prev.map((item) =>
        (item.recipe.id || item.recipe._id) === recipeId
          ? {
              ...item,
              timers: item.timers.map((t) =>
                t.id === timerId ? { ...t, remainingSeconds: t.totalSeconds, isRunning: false } : t
              ),
            }
          : item
      )
    )
  }

  return (
    <MultiCookContext.Provider
      value={{
        sessions,
        activeRecipeId,
        startCooking,
        stopCooking,
        setActiveRecipeId,
        setActiveStep,
        toggleStepCompleted,
        addTimer,
        toggleTimer,
        resetTimer,
      }}
    >
      {children}
    </MultiCookContext.Provider>
  )
}

export function useMultiCook() {
  return useContext(MultiCookContext)
}
