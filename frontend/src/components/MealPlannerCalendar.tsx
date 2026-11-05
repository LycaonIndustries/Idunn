/**
 * 7-Day Responsive Meal Planning Calendar with Recipe Picker and Serving Scalers.
 */

import { useEffect, useState, useMemo } from 'react'
import type { MealSlotUpdateRequest, MealType, Recipe, WeeklyMealPlan } from '../types'
import { fetchWeeklyMealPlan, updateMealSlot } from '../api'

interface MealPlannerCalendarProps {
  recipes: Recipe[]
  onSelectRecipe?: (recipe: Recipe) => void
}

interface ActiveSlotTarget {
  dayOfWeek: string
  mealType: MealType
}

const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner']
const SERVING_OPTIONS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]

export function MealPlannerCalendar({ recipes, onSelectRecipe }: MealPlannerCalendarProps) {
  const [plan, setPlan] = useState<WeeklyMealPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeSlot, setActiveSlot] = useState<ActiveSlotTarget | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let isMounted = true
    const initPlan = async () => {
      try {
        setLoading(true)
        const data = await fetchWeeklyMealPlan()
        if (isMounted) setPlan(data)
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load meal plan')
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    void initPlan()
    return () => { isMounted = false }
  }, [])

  const filteredRecipes = useMemo(() => {
    if (!searchQuery.trim()) return recipes
    const q = searchQuery.toLowerCase()
    return recipes.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        r.cuisine_type?.toLowerCase().includes(q) ||
        r.ingredients.some((i) => i.name.toLowerCase().includes(q)),
    )
  }, [recipes, searchQuery])

  // Mutate a planned meal slot on the backend and synchronize local state.
  const mutateSlot = async (slotUpdate: MealSlotUpdateRequest): Promise<boolean> => {
    if (!plan) return false
    const planId = plan._id || plan.id || ''
    try {
      const updated = await updateMealSlot(planId, slotUpdate)
      setPlan(updated)
      return true
    } catch (err: any) {
      console.error('Failed to update meal slot:', err)
      return false
    }
  }

  const handleAssignRecipe = async (recipe: Recipe) => {
    if (!activeSlot) return
    const ok = await mutateSlot({
      day_of_week: activeSlot.dayOfWeek,
      meal_type: activeSlot.mealType,
      recipe_id: recipe._id || recipe.id,
      recipe_title: recipe.title,
      servings_multiplier: 1.0,
    })
    if (ok) {
      setActiveSlot(null)
      setSearchQuery('')
    }
  }

  const handleClearSlot = (dayOfWeek: string, mealType: MealType) =>
    void mutateSlot({ day_of_week: dayOfWeek, meal_type: mealType, recipe_id: null, recipe_title: null, servings_multiplier: 1.0 })

  const handleScaleServings = (dayOfWeek: string, mealType: MealType, multiplier: number, recipeId?: string | null, recipeTitle?: string | null) =>
    void mutateSlot({ day_of_week: dayOfWeek, meal_type: mealType, recipe_id: recipeId, recipe_title: recipeTitle, servings_multiplier: multiplier })

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-stone-500">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-orange-500 border-t-transparent" />
          <span>Loading weekly meal planner...</span>
        </div>
      </div>
    )
  }

  if (error || !plan) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-center text-red-300">
        <p>{error || 'Meal plan unavailable'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-stone-100">Weekly Meal Planner</h2>
          <p className="text-sm text-stone-400">Week of {plan.week_start_date} • 7-day schedule with serving scalers</p>
        </div>
      </div>

      {/* 7-Day Monday to Sunday Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-7">
        {plan.days.map((day) => (
          <div key={day.date} className="flex flex-col rounded-xl border border-stone-800 bg-stone-900/60 p-3 shadow-sm">
            <div className="mb-3 border-b border-stone-800/80 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-orange-400">{day.day_of_week}</span>
              <p className="text-sm font-medium text-stone-200">{day.date.slice(5)}</p>
            </div>

            <div className="flex flex-1 flex-col gap-3">
              {MEAL_TYPES.map((type) => {
                const slot = day.slots.find((s) => s.meal_type === type)
                const hasRecipe = Boolean(slot?.recipe_title)
                const currentMultiplier = slot?.servings_multiplier || 1.0

                return (
                  <div
                    key={type}
                    className={`flex flex-col rounded-lg border p-2.5 transition-colors ${
                      hasRecipe ? 'border-orange-500/30 bg-orange-950/10' : 'border-dashed border-stone-800 bg-stone-950/30'
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between text-xs font-medium uppercase text-stone-400">
                      <span>{type}</span>
                      {hasRecipe && (
                        <button
                          type="button"
                          aria-label={`Remove recipe from ${day.day_of_week} ${type}`}
                          onClick={() => handleClearSlot(day.day_of_week, type)}
                          className="text-stone-500 hover:text-red-400"
                        >✕</button>
                      )}
                    </div>

                    {hasRecipe ? (
                      <div className="space-y-2">
                        <button
                          type="button"
                          className="text-left font-semibold text-stone-100 hover:text-orange-400 line-clamp-2 text-sm"
                          onClick={() => {
                            const rec = recipes.find((r) => (r._id || r.id) === slot?.recipe_id)
                            if (rec && onSelectRecipe) onSelectRecipe(rec)
                          }}
                        >
                          {slot?.recipe_title}
                        </button>

                        <div className="flex items-center justify-between pt-1 text-xs">
                          <span className="text-stone-400">Scale:</span>
                          <select
                            aria-label={`Serving scale for ${day.day_of_week} ${type}`}
                            value={currentMultiplier}
                            onChange={(e) =>
                              handleScaleServings(
                                day.day_of_week,
                                type,
                                parseFloat(e.target.value),
                                slot?.recipe_id,
                                slot?.recipe_title,
                              )
                            }
                            className="rounded border border-stone-700 bg-stone-800 px-1.5 py-0.5 text-xs text-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-500"
                          >
                            {SERVING_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>{opt.toFixed(1)}x</option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ) : (
                      <button
                        type="button"
                        aria-label={`Add recipe to ${day.day_of_week} ${type}`}
                        onClick={() => setActiveSlot({ dayOfWeek: day.day_of_week, mealType: type })}
                        className="mt-1 flex items-center justify-center rounded border border-dashed border-stone-700/60 py-2 text-xs font-medium text-stone-400 hover:border-orange-500 hover:text-orange-400"
                      >
                        + Add Recipe
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Recipe Picker Modal */}
      {activeSlot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-stone-800 bg-stone-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4">
              <div>
                <h3 className="text-lg font-bold text-stone-100">
                  Assign Recipe ({activeSlot.dayOfWeek} {activeSlot.mealType})
                </h3>
                <p className="text-xs text-stone-400">Choose a recipe from your Recipe Vault</p>
              </div>
              <button
                type="button"
                aria-label="Close recipe picker"
                onClick={() => setActiveSlot(null)}
                className="rounded-lg p-1.5 text-stone-400 hover:bg-stone-800 hover:text-stone-100"
              >✕</button>
            </div>

            <div className="mb-4">
              <input
                type="text"
                placeholder="Search by title, cuisine, or ingredient..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-xl border border-stone-800 bg-stone-950 px-3 py-2 text-sm text-stone-100 placeholder-stone-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {filteredRecipes.length === 0 ? (
                <div className="py-8 text-center text-sm text-stone-500">
                  No recipes found matching your query.
                </div>
              ) : (
                filteredRecipes.map((r) => (
                  <button
                    key={r._id || r.id}
                    type="button"
                    onClick={() => handleAssignRecipe(r)}
                    className="flex w-full items-center justify-between rounded-xl border border-stone-800/80 bg-stone-950/40 p-3 text-left transition hover:border-orange-500/50 hover:bg-orange-950/10"
                  >
                    <div>
                      <h4 className="text-sm font-semibold text-stone-100">{r.title}</h4>
                      <p className="text-xs text-stone-400">
                        {r.cuisine_type || 'General'} • {(r.prep_time_minutes || 0) + (r.cook_time_minutes || 0)}m • {r.servings} servings
                      </p>
                    </div>
                    <span className="rounded-lg bg-orange-500/10 px-2 py-1 text-xs font-semibold text-orange-400">
                      Select
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
