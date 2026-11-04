/**
 * Recipe card component for the vault grid view.
 * Displays title, dietary pill, hero image, preparation time, and quick view toggles.
 */

import React, { useState } from 'react'
import {
  Clock,
  Users,
  ChevronDown,
  ChevronUp,
  Trash2,
  CheckSquare,
  Square,
  Sparkles,
  ExternalLink,
  Flame,
} from 'lucide-react'
import type { Recipe } from '../types'

/**
 * Properties for RecipeCard component.
 */
interface RecipeCardProps {
  /** Recipe document to render. */
  recipe: Recipe
  /** Callback to trigger recipe deletion. */
  onDelete: (id: string) => void
  /** Callback to open dedicated full-page recipe view. */
  onSelect?: (recipe: Recipe) => void
}

/**
 * Interactive card displaying summary metrics, serving scaler, and ingredient checklist.
 *
 * @param props - Component properties.
 * @returns Recipe card JSX element.
 */
export const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onDelete, onSelect }) => {
  // Toggle inline expanded view without leaving the main vault grid.
  const [expanded, setExpanded] = useState(false)

  // Serving scaling factor (0.5x, 1x, 2x, 4x) for real-time ingredient quantity adjustments.
  const [servingMultiplier, setServingMultiplier] = useState(1)

  // Track checked ingredients locally during active kitchen preparation.
  const [checkedIngredients, setCheckedIngredients] = useState<Record<number, boolean>>({})

  // Resolve recipe ID handling MongoDB (_id) and Supabase (id) naming conventions.
  const recipeId = recipe.id || recipe._id || ''
  const baseServings = recipe.servings || 2
  const scaledServings = Math.round(baseServings * servingMultiplier * 10) / 10

  // Toggle strikethrough state on ingredients as user prepares items.
  const toggleCheck = (idx: number) => {
    setCheckedIngredients((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  // Confirm before deletion to prevent accidental loss of recipes.
  // Stop click propagation so opening the delete dialog does not trigger card selection.
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Delete "${recipe.title}" from recipe vault?`)) {
      onDelete(recipeId)
    }
  }

  return (
    <div className="bg-slate-900/90 rounded-2xl shadow-sm border border-slate-800 overflow-hidden hover:border-slate-700 transition-all flex flex-col justify-between group">
      <div>
        {/* Hero image banner with calorie badge overlay */}
        {recipe.image_url ? (
          <div
            onClick={() => onSelect?.(recipe)}
            className="relative h-44 w-full overflow-hidden bg-slate-950 cursor-pointer"
          >
            <img
              src={recipe.image_url}
              alt={recipe.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            {/* Subtle gradient overlay to enhance title legibility against bright photos */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent" />
            {recipe.nutrition?.calories && (
              <div className="absolute bottom-2.5 right-2.5 flex items-center space-x-1 bg-slate-950/80 backdrop-blur-sm text-orange-400 border border-orange-500/30 px-2.5 py-1 rounded-xl text-xs font-bold shadow-md">
                <Flame className="w-3.5 h-3.5" />
                <span>{recipe.nutrition.calories} kcal</span>
              </div>
            )}
          </div>
        ) : recipe.nutrition?.calories ? (
          <div className="pt-4 px-6 flex justify-end">
            <span className="flex items-center space-x-1 bg-slate-950/70 text-orange-400 border border-orange-500/30 px-2.5 py-0.5 rounded-xl text-xs font-bold">
              <Flame className="w-3 h-3" />
              <span>{recipe.nutrition.calories} kcal</span>
            </span>
          </div>
        ) : null}

        {/* Card header with dietary tag, regional badge, and title */}
        <div className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 cursor-pointer" onClick={() => onSelect?.(recipe)}>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                {recipe.cuisine_type && (
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      recipe.cuisine_type === 'veg'
                        ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                        : 'bg-rose-950/60 text-rose-400 border border-rose-800/50'
                    }`}
                  >
                    {recipe.cuisine_type.toUpperCase()}
                  </span>
                )}
                {recipe.region && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {recipe.region.replace('_', ' ')}
                  </span>
                )}
                {recipe.difficulty && (
                  <span className="text-xs font-medium text-slate-400">• {recipe.difficulty}</span>
                )}
              </div>

              <h3 className="text-xl font-bold text-slate-100 group-hover:text-orange-400 transition-colors leading-snug">
                {recipe.title}
              </h3>
              {recipe.description && (
                <p className="text-sm text-slate-400 mt-1 line-clamp-2">{recipe.description}</p>
              )}
            </div>

            <button
              onClick={handleDelete}
              title="Delete recipe"
              className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          {/* Quick metrics grid: Total Cooking Time, Portions, Ingredient Count */}
          <div className="grid grid-cols-3 gap-2 mt-4 text-xs text-slate-300 bg-slate-950/60 border border-slate-800/80 p-2.5 rounded-xl">
            <div className="flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 text-orange-400" />
              <span>{(recipe.prep_time_minutes || 0) + (recipe.cook_time_minutes || 0)} min</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Users className="w-3.5 h-3.5 text-orange-400" />
              <span>{scaledServings} serv</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-orange-400" />
              <span>{recipe.ingredients.length} items</span>
            </div>
          </div>

          {/* Action Row: dedicated page navigation and inline accordion toggle */}
          <div className="grid grid-cols-2 gap-2 mt-4">
            <button
              onClick={() => onSelect?.(recipe)}
              className="py-2 px-3 flex items-center justify-center space-x-1 text-xs font-bold text-orange-400 bg-orange-500/10 hover:bg-orange-500 hover:text-white border border-orange-500/20 rounded-xl transition-all cursor-pointer shadow-sm"
            >
              <span>Recipe Page</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => setExpanded(!expanded)}
              className="py-2 px-3 flex items-center justify-center space-x-1 text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800 rounded-xl transition-colors cursor-pointer"
            >
              <span>{expanded ? 'Hide' : 'Quick View'}</span>
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Quick Details Drawer */}
      {expanded && (
        <div className="p-6 pt-0 border-t border-slate-800 bg-slate-950/40">
          {/* Real-time Serving Scaler Buttons */}
          <div className="flex items-center justify-between py-3 border-b border-slate-800 mb-4">
            <span className="text-xs font-semibold text-slate-300">Scale Ingredients:</span>
            <div className="flex space-x-1">
              {[0.5, 1, 2, 4].map((mult) => (
                <button
                  key={mult}
                  onClick={() => setServingMultiplier(mult)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                    servingMultiplier === mult
                      ? 'bg-orange-500 text-white shadow-sm'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  {mult}×
                </button>
              ))}
            </div>
          </div>

          {/* Interactive ingredient checklist with strikethrough */}
          <div className="mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Ingredients ({recipe.ingredients.length})
            </h4>
            <div className="space-y-1.5">
              {recipe.ingredients.map((ing, idx) => {
                const scaledQty = ing.quantity
                  ? (ing.quantity * servingMultiplier).toFixed(1).replace(/\.0$/, '')
                  : null
                const isChecked = !!checkedIngredients[idx]

                return (
                  <div
                    key={idx}
                    onClick={() => toggleCheck(idx)}
                    className={`flex items-center justify-between p-2 rounded-xl cursor-pointer transition-colors text-sm ${
                      isChecked
                        ? 'bg-slate-900/40 text-slate-500 line-through'
                        : 'hover:bg-slate-900/80 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      {isChecked ? (
                        <CheckSquare className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-600 flex-shrink-0" />
                      )}
                      <span className="font-medium">{ing.name}</span>
                    </div>

                    {(scaledQty || ing.unit) && (
                      <span className="text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                        {scaledQty ? `${scaledQty} ` : ''}
                        {ing.unit || ''}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Step-by-step instructions */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Instructions ({recipe.steps.length} Steps)
            </h4>
            <ol className="space-y-3">
              {recipe.steps.map((step, idx) => (
                <li key={idx} className="flex space-x-3 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-bold text-xs flex items-center justify-center">
                    {step.step_number || idx + 1}
                  </span>
                  <div className="flex-1">
                    <p className="text-slate-300 leading-relaxed">{step.instruction}</p>
                    {step.time_minutes && (
                      <span className="inline-flex items-center space-x-1 text-xs text-orange-400 mt-1">
                        <Clock className="w-3 h-3" />
                        <span>{step.time_minutes} min timer</span>
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  )
}

export default RecipeCard
