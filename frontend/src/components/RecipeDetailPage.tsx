/**
 * Full-page interactive recipe detail viewer for Iðunn Kitchen OS.
 * Features hero photo rendering, dynamic ingredient serving scaler (0.5x to 4x),
 * step completion checkboxes, nutrition macro progress bars, and clipboard sharing.
 */

import React, { useState } from 'react'
import {
  ArrowLeft,
  Clock,
  Users,
  Flame,
  ChefHat,
  ExternalLink,
  Trash2,
  Check,
  CheckCircle2,
  Sparkles,
  Utensils,
  Share2,
  Activity,
  AlertTriangle,
  Loader2,
  X,
  ShoppingBag,
} from 'lucide-react'
import type { DeductionReport, Recipe } from '../types'
import { cookRecipe, addShoppingListBatch } from '../api'

/**
 * Properties for RecipeDetailPage component.
 */
interface RecipeDetailPageProps {
  /** Recipe document to display in detail. */
  recipe: Recipe
  /** Callback to return to the recipe vault grid. */
  onBack: () => void
  /** Callback to remove this recipe from the vault. */
  onDelete: (id: string) => void
}

/**
 * Detailed recipe view with interactive scaling and cooking progress tracking.
 *
 * @param props - Component properties.
 * @returns RecipeDetailPage JSX element.
 */
export const RecipeDetailPage: React.FC<RecipeDetailPageProps> = ({
  recipe,
  onBack,
  onDelete,
}) => {
  // Real-time scaling factor for ingredient quantities (0.5x, 1x, 1.5x, 2x, 4x).
  const [multiplier, setMultiplier] = useState<number>(1)

  // Track checked ingredients during kitchen prep.
  const [checkedIngredients, setCheckedIngredients] = useState<Record<number, boolean>>({})

  // Highlight currently focused step for hands-free or counter cooking.
  const [activeStep, setActiveStep] = useState<number | null>(null)

  // Track completed cooking steps to maintain position in long recipes.
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({})

  // Visual confirmation timer for link clipboard copy.
  const [copied, setCopied] = useState(false)

  // Track automatic pantry deduction request and result report.
  const [cooking, setCooking] = useState(false)
  const [deductionReport, setDeductionReport] = useState<DeductionReport | null>(null)
  const [cookError, setCookError] = useState<string | null>(null)

  // Track shopping list batch addition state.
  const [addingToShoppingList, setAddingToShoppingList] = useState(false)
  const [shoppingListSuccess, setShoppingListSuccess] = useState<string | null>(null)

  // Add all recipe ingredients directly to shopping list.
  const handleAddAllToShoppingList = async () => {
    try {
      setAddingToShoppingList(true)
      const itemsToAdd = recipe.ingredients.map((ing) => ({
        name: ing.name,
        quantity: ing.quantity ? Math.round(ing.quantity * multiplier * 100) / 100 : 1,
        unit: ing.unit || 'count',
        recipe_id: recipeId,
      }))
      const res = await addShoppingListBatch(itemsToAdd)
      setShoppingListSuccess(`Added ${res.length} items to shopping list`)
      setTimeout(() => setShoppingListSuccess(null), 3000)
    } catch (err: any) {
      alert(err.message || 'Failed to add items to shopping list')
    } finally {
      setAddingToShoppingList(false)
    }
  }

  // Resolve recipe ID handling MongoDB (_id) and Supabase (id) naming conventions.
  const recipeId = recipe.id || recipe._id || ''
  const baseServings = recipe.servings || 2
  const currentServings = Math.round(baseServings * multiplier * 10) / 10

  // Toggle ingredient checked state when clicked.
  const toggleIngredient = (idx: number) => {
    setCheckedIngredients((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  // Toggle step completion status to strike out finished instructions.
  const toggleStep = (stepNum: number) => {
    setCompletedSteps((prev) => ({ ...prev, [stepNum]: !prev[stepNum] }))
  }

  // Copy current recipe browser URL to clipboard for family sharing.
  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Prompt confirmation dialog before permanent deletion from vault.
  const handleDelete = () => {
    if (window.confirm(`Are you sure you want to delete "${recipe.title}" from your vault?`)) {
      onDelete(recipeId)
      onBack()
    }
  }

  // Execute automatic ingredient deduction from pantry stock.
  const handleCookRecipe = async () => {
    if (!recipeId) return
    setCooking(true)
    setCookError(null)
    try {
      // Trigger backend FEFO deduction using current serving scaling multiplier.
      const report = await cookRecipe(recipeId, multiplier)
      setDeductionReport(report)
    } catch (err: unknown) {
      setCookError(err instanceof Error ? err.message : 'Failed to deduct ingredients.')
    } finally {
      setCooking(false)
    }
  }

  const totalTime = (recipe.prep_time_minutes || 0) + (recipe.cook_time_minutes || 0)
  const nutrition = recipe.nutrition

  return (
    <div className="max-w-5xl mx-auto py-6 px-4 sm:px-6">
      {/* Top action bar: back navigation, share button, and delete trigger */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-slate-400 hover:text-orange-400 transition-colors text-sm font-medium py-1.5 px-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Vault</span>
        </button>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCookRecipe}
            disabled={cooking}
            className="flex items-center space-x-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 px-3.5 py-1.5 rounded-xl transition-all shadow-md shadow-emerald-600/20 cursor-pointer"
          >
            {cooking ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Utensils className="w-3.5 h-3.5" />
            )}
            <span>I Cooked This</span>
          </button>

          <button
            onClick={handleShare}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl transition-colors cursor-pointer"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <Share2 className="w-3.5 h-3.5" />
            )}
            <span>{copied ? 'Link Copied' : 'Share'}</span>
          </button>

          <button
            onClick={handleDelete}
            title="Delete recipe"
            className="text-slate-400 hover:text-red-400 bg-slate-900 border border-slate-800 p-2 rounded-xl transition-colors cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Hero Header Card with source photo and metadata overlays */}
      <div className="relative rounded-3xl overflow-hidden border border-slate-800 bg-slate-900/90 shadow-2xl mb-8">
        {recipe.image_url ? (
          <div className="relative w-full h-72 sm:h-96 overflow-hidden bg-slate-950">
            <img
              src={recipe.image_url}
              alt={recipe.title}
              className="w-full h-full object-cover object-center transform hover:scale-105 transition-transform duration-700"
            />
            {/* Gradient overlay ensures title readability over arbitrary hero images */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent" />
          </div>
        ) : (
          <div className="relative w-full h-48 sm:h-56 bg-gradient-to-br from-orange-950/40 via-slate-900 to-slate-950 flex items-center justify-center border-b border-slate-800">
            <div className="text-center p-6">
              <div className="w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/20 text-orange-400 flex items-center justify-center mx-auto mb-3 shadow-inner">
                <ChefHat className="w-8 h-8" />
              </div>
              <p className="text-xs uppercase tracking-wider text-orange-400 font-semibold">
                Iðunn Vault Recipe
              </p>
            </div>
          </div>
        )}

        {/* Content Header: badges, title, description, and key statistics */}
        <div className="p-6 sm:p-8 -mt-16 sm:-mt-24 relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            {recipe.cuisine_type && (
              <span
                className={`text-xs font-semibold px-3 py-1 rounded-full border shadow-sm ${
                  recipe.cuisine_type === 'veg'
                    ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60'
                    : 'bg-rose-950/80 text-rose-400 border-rose-800/60'
                }`}
              >
                {recipe.cuisine_type.toUpperCase()}
              </span>
            )}
            {recipe.region && (
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-800/90 text-slate-300 border border-slate-700">
                {recipe.region.replace('_', ' ')}
              </span>
            )}
            {recipe.difficulty && (
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-800/90 text-slate-300 border border-slate-700">
                {recipe.difficulty}
              </span>
            )}
            {recipe.source_name && (
              <span className="text-xs text-slate-400 bg-slate-950/70 border border-slate-800 px-3 py-1 rounded-full flex items-center gap-1.5">
                <span>Via {recipe.source_name}</span>
                {recipe.source_url && (
                  <a
                    href={recipe.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-orange-400 hover:text-orange-300 inline-flex items-center"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </span>
            )}
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-50 tracking-tight leading-tight mb-3">
            {recipe.title}
          </h1>

          {recipe.description && (
            <p className="text-base text-slate-300 leading-relaxed max-w-3xl mb-6">
              {recipe.description}
            </p>
          )}

          {/* Quick Metrics Bar: Total Time, Portions, Prep/Cook split, Ingredient Count */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/80 border border-slate-800/90 rounded-2xl p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20">
                <Clock className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Total Time</div>
                <div className="text-sm font-bold text-slate-100">
                  {totalTime ? `${totalTime} min` : 'Unspecified'}
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Servings</div>
                <div className="text-sm font-bold text-slate-100">{currentServings}</div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Flame className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Prep / Cook</div>
                <div className="text-sm font-bold text-slate-100">
                  {recipe.prep_time_minutes || 0}m / {recipe.cook_time_minutes || 0}m
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-400 font-medium">Ingredients</div>
                <div className="text-sm font-bold text-slate-100">
                  {recipe.ingredients.length} items
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Nutrition Information Panel with macro progress meters */}
      <div className="bg-slate-900/90 rounded-3xl border border-slate-800 p-6 sm:p-7 shadow-lg mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Nutritional Facts</h2>
              <p className="text-xs text-slate-400">Captured & calculated per serving</p>
            </div>
          </div>
          {nutrition?.calories && (
            <div className="text-right">
              <span className="text-2xl font-black text-orange-400">{nutrition.calories}</span>
              <span className="text-xs font-semibold text-slate-400 ml-1">kcal</span>
            </div>
          )}
        </div>

        {nutrition ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {/* Protein Card */}
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-3.5">
              <div className="text-xs text-slate-400 font-medium mb-1">Protein</div>
              <div className="text-lg font-bold text-emerald-400">
                {nutrition.protein !== null && nutrition.protein !== undefined
                  ? `${nutrition.protein}g`
                  : '—'}
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, ((nutrition.protein || 0) / 30) * 100)}%` }}
                />
              </div>
            </div>

            {/* Carbohydrates Card */}
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-3.5">
              <div className="text-xs text-slate-400 font-medium mb-1">Carbohydrates</div>
              <div className="text-lg font-bold text-amber-400">
                {nutrition.carbs !== null && nutrition.carbs !== undefined
                  ? `${nutrition.carbs}g`
                  : '—'}
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-amber-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, ((nutrition.carbs || 0) / 60) * 100)}%` }}
                />
              </div>
            </div>

            {/* Fat Card */}
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-3.5">
              <div className="text-xs text-slate-400 font-medium mb-1">Total Fat</div>
              <div className="text-lg font-bold text-rose-400">
                {nutrition.fat !== null && nutrition.fat !== undefined ? `${nutrition.fat}g` : '—'}
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-rose-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, ((nutrition.fat || 0) / 25) * 100)}%` }}
                />
              </div>
            </div>

            {/* Dietary Fiber Card */}
            <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-3.5">
              <div className="text-xs text-slate-400 font-medium mb-1">Dietary Fiber</div>
              <div className="text-lg font-bold text-sky-400">
                {nutrition.fiber !== null && nutrition.fiber !== undefined
                  ? `${nutrition.fiber}g`
                  : '—'}
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-sky-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, ((nutrition.fiber || 0) / 10) * 100)}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-5 text-center text-sm text-slate-400">
            Nutrition information is being estimated from recipe ingredients. Macro breakdown will
            appear once synced.
          </div>
        )}
      </div>

      {/* Main Recipe Body (Ingredients & Instructions) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Ingredients & Serving Scaler */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900/90 rounded-3xl border border-slate-800 p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <Utensils className="w-5 h-5 text-orange-400" />
                <h2 className="text-lg font-bold text-slate-100">Ingredients</h2>
              </div>
              <span className="text-xs text-slate-400">{recipe.ingredients.length} items</span>
            </div>

            {/* Serving Scaler Buttons */}
            <div className="bg-slate-950/70 border border-slate-800/80 rounded-2xl p-3.5 mb-5">
              <div className="text-xs font-medium text-slate-400 mb-2 flex items-center justify-between">
                <span>Scale Servings:</span>
                <span className="text-orange-400 font-bold">{currentServings} servings</span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {[0.5, 1, 1.5, 2, 4].map((scale) => (
                  <button
                    key={scale}
                    onClick={() => setMultiplier(scale)}
                    className={`py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      multiplier === scale
                        ? 'bg-orange-500 text-white shadow-md shadow-orange-500/20'
                        : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    {scale}×
                  </button>
                ))}
              </div>
            </div>

            {/* Add All Ingredients to Shopping List */}
            <div className="mb-4">
              <button
                type="button"
                onClick={handleAddAllToShoppingList}
                disabled={addingToShoppingList}
                className="w-full py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-2 transition-colors disabled:opacity-50"
              >
                <ShoppingBag className="w-3.5 h-3.5 text-orange-400" />
                <span>
                  {addingToShoppingList
                    ? 'Adding to Shopping List...'
                    : 'Add All Ingredients to Shopping List'}
                </span>
              </button>
              {shoppingListSuccess && (
                <p className="text-xs text-emerald-400 text-center mt-1.5 font-medium">
                  {shoppingListSuccess}
                </p>
              )}
            </div>

            {/* Ingredient Checklist items */}
            <div className="space-y-2">
              {recipe.ingredients.map((item, idx) => {
                const scaledQty = item.quantity
                  ? Math.round(item.quantity * multiplier * 100) / 100
                  : null
                const isChecked = Boolean(checkedIngredients[idx])

                return (
                  <div
                    key={idx}
                    onClick={() => toggleIngredient(idx)}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start space-x-3 ${
                      isChecked
                        ? 'bg-slate-950/40 border-slate-800/50 opacity-50'
                        : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div
                      className={`mt-0.5 w-5 h-5 rounded-lg border flex items-center justify-center transition-colors flex-shrink-0 ${
                        isChecked
                          ? 'bg-emerald-500 border-emerald-500 text-white'
                          : 'border-slate-600 bg-slate-900'
                      }`}
                    >
                      {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>

                    <div className="flex-1 text-sm">
                      <div className="flex items-baseline justify-between gap-2">
                        <span
                          className={`font-semibold ${
                            isChecked ? 'line-through text-slate-400' : 'text-slate-100'
                          }`}
                        >
                          {item.name}
                        </span>
                        {scaledQty !== null && (
                          <span className="text-xs font-bold text-orange-400 whitespace-nowrap bg-orange-950/40 border border-orange-900/50 px-2 py-0.5 rounded-lg">
                            {scaledQty} {item.unit || ''}
                          </span>
                        )}
                      </div>
                      {item.notes && <p className="text-xs text-slate-400 mt-0.5">{item.notes}</p>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Step-by-Step Cooking Method */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900/90 rounded-3xl border border-slate-800 p-6 shadow-lg">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center space-x-2">
                <ChefHat className="w-5 h-5 text-orange-400" />
                <h2 className="text-lg font-bold text-slate-100">Cooking Method</h2>
              </div>
              <span className="text-xs text-slate-400">{recipe.steps.length} steps</span>
            </div>

            <div className="space-y-4">
              {recipe.steps.map((step) => {
                const isCompleted = Boolean(completedSteps[step.step_number])
                const isSelected = activeStep === step.step_number

                return (
                  <div
                    key={step.step_number}
                    onClick={() => setActiveStep(step.step_number)}
                    className={`p-5 rounded-2xl border transition-all cursor-pointer relative ${
                      isCompleted
                        ? 'bg-slate-950/40 border-slate-800/50 opacity-60'
                        : isSelected
                          ? 'bg-slate-950 border-orange-500/60 ring-1 ring-orange-500/40 shadow-lg'
                          : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start space-x-3.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleStep(step.step_number)
                        }}
                        className={`w-7 h-7 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors cursor-pointer ${
                          isCompleted
                            ? 'bg-emerald-500 text-white'
                            : 'bg-orange-500/10 text-orange-400 border border-orange-500/30 hover:bg-orange-500 hover:text-white'
                        }`}
                      >
                        {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : step.step_number}
                      </button>

                      <div className="flex-1">
                        <p
                          className={`text-sm sm:text-base leading-relaxed ${
                            isCompleted ? 'line-through text-slate-400' : 'text-slate-100'
                          }`}
                        >
                          {step.instruction}
                        </p>

                        {step.time_minutes && (
                          <div className="mt-2.5 inline-flex items-center space-x-1.5 text-xs font-semibold text-orange-400 bg-orange-950/40 border border-orange-900/50 px-2.5 py-1 rounded-lg">
                            <Clock className="w-3.5 h-3.5" />
                            <span>{step.time_minutes} minutes</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Cooking deduction error alert banner */}
      {cookError && (
        <div className="fixed bottom-6 right-6 z-50 bg-red-950 border border-red-800 text-red-200 p-4 rounded-2xl shadow-2xl flex items-center space-x-3">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span className="text-sm">{cookError}</span>
          <button
            onClick={() => setCookError(null)}
            className="text-red-400 hover:text-red-200 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Deduction Report Dialog */}
      {deductionReport && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
                  <Utensils className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">Cooking Deduction Summary</h3>
                  <p className="text-xs text-slate-400">
                    Scaled for {deductionReport.servings_multiplier}x portions
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDeductionReport(null)}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Status overview */}
            {deductionReport.fully_satisfied ? (
              <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                <span>All ingredients were found and deducted from pantry using FEFO.</span>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-xs text-amber-300 flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span>Cooked with partial pantry shortages. Check deficits below.</span>
              </div>
            )}

            {/* Deducted items */}
            {deductionReport.deductions.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Deducted From Pantry
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {deductionReport.deductions.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs"
                    >
                      <span className="font-medium text-slate-200">{item.item_name}</span>
                      <span className="text-slate-400">
                        -{item.deducted_quantity} {item.unit}{' '}
                        {item.depleted ? (
                          <strong className="text-red-400">(Depleted)</strong>
                        ) : (
                          `(${item.remaining_quantity} left)`
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Missing Shortages */}
            {deductionReport.shortages.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">
                  Pantry Shortages
                </h4>
                <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  {deductionReport.shortages.map((shortage, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded-lg bg-amber-950/30 border border-amber-800/50 flex items-center justify-between text-xs"
                    >
                      <span className="font-medium text-amber-200">{shortage.ingredient_name}</span>
                      <span className="text-amber-400 font-semibold">
                        Missing {shortage.missing_quantity} {shortage.unit}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => setDeductionReport(null)}
              className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 text-sm font-medium transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default RecipeDetailPage
