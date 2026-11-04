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
} from 'lucide-react'
import type { Recipe } from '../types'

interface RecipeCardProps {
  recipe: Recipe
  onDelete: (id: string) => void
}

export const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onDelete }) => {
  const [expanded, setExpanded] = useState(false)
  const [servingMultiplier, setServingMultiplier] = useState(1)
  const [checkedIngredients, setCheckedIngredients] = useState<Record<number, boolean>>({})

  const recipeId = recipe.id || recipe._id || ''
  const baseServings = recipe.servings || 2
  const scaledServings = baseServings * servingMultiplier

  const toggleCheck = (idx: number) => {
    setCheckedIngredients((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Delete "${recipe.title}" from recipe vault?`)) {
      onDelete(recipeId)
    }
  }

  return (
    <div className="bg-slate-900/90 rounded-2xl shadow-sm border border-slate-800 overflow-hidden hover:border-slate-700 transition-all">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
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
                <span className="text-xs font-medium text-slate-400">
                  • {recipe.difficulty}
                </span>
              )}
            </div>

            <h3 className="text-xl font-bold text-slate-100 leading-snug">{recipe.title}</h3>
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

        {/* Info Grid */}
        <div className="grid grid-cols-3 gap-2 mt-4 text-xs text-slate-300 bg-slate-950/60 border border-slate-800/80 p-2.5 rounded-xl">
          <div className="flex items-center space-x-1.5">
            <Clock className="w-3.5 h-3.5 text-orange-400" />
            <span>{(recipe.prep_time_minutes || 0) + (recipe.cook_time_minutes || 0)} min total</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Users className="w-3.5 h-3.5 text-orange-400" />
            <span>{scaledServings} servings</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-orange-400" />
            <span>{recipe.ingredients.length} items</span>
          </div>
        </div>

        {/* Toggle Expand */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 w-full py-2 flex items-center justify-center space-x-1 text-xs font-semibold text-slate-400 hover:text-orange-400 bg-slate-950/40 hover:bg-slate-800/50 rounded-xl transition-colors cursor-pointer"
        >
          <span>{expanded ? 'Hide Recipe Details' : 'View Ingredients & Steps'}</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="p-6 pt-0 border-t border-slate-800 bg-slate-950/40">
          {/* Serving Scaler */}
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

          {/* Ingredients Checklist */}
          <div className="mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Ingredients ({recipe.ingredients.length})
            </h4>
            <div className="space-y-1.5">
              {recipe.ingredients.map((ing, idx) => {
                const scaledQty = ing.quantity ? (ing.quantity * servingMultiplier).toFixed(1).replace(/\.0$/, '') : null
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
                        {scaledQty ? `${scaledQty} ` : ''}{ing.unit || ''}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Steps */}
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
