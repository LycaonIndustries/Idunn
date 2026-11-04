import React, { useState } from 'react'
import { Search, Filter, RefreshCw, PlusCircle, BookOpen } from 'lucide-react'
import type { Recipe } from '../types'
import { RecipeCard } from './RecipeCard'

/**
 * Properties for the RecipeVault component.
 */
interface RecipeVaultProps {
  /** Recipe collection fetched from the backend. */
  recipes: Recipe[]
  /** Indicates whether an active network fetch is running. */
  loading: boolean
  /** Callback to trigger an asynchronous reload of the recipe vault. */
  onRefresh: () => void
  /** Callback to delete a recipe by unique identifier. */
  onDeleteRecipe: (id: string) => void
  /** Callback to navigate to the AI ingest / capture tab. */
  onNavigateToCapture: () => void
  /** Callback to select a recipe and open its full detail view. */
  onSelectRecipe?: (recipe: Recipe) => void
}

/**
 * RecipeVault displays a searchable, filterable grid of all saved recipes.
 *
 * @param props - Component configuration and action handlers.
 * @returns Rendered React element containing search controls and recipe cards.
 */
export const RecipeVault: React.FC<RecipeVaultProps> = ({
  recipes,
  loading,
  onRefresh,
  onDeleteRecipe,
  onNavigateToCapture,
  onSelectRecipe,
}) => {
  // Store search terms locally to provide instant keystroke filtering.
  const [search, setSearch] = useState('')

  // Track the active dietary or difficulty filter preset.
  const [filterType, setFilterType] = useState<string>('all')

  // Execute filtering in memory to prevent slow round-trip queries to the server.
  const filtered = recipes.filter((r) => {
    // Normalise text to lowercase so user casing differences do not block matches.
    const term = search.toLowerCase()
    const matchesSearch =
      r.title.toLowerCase().includes(term) ||
      r.ingredients.some((i) => i.name.toLowerCase().includes(term)) ||
      (r.tags && r.tags.some((t) => t.toLowerCase().includes(term)))

    if (!matchesSearch) return false

    // Apply strict dietary filters so vegetarian users do not see meat recipes.
    if (filterType === 'all') return true
    if (filterType === 'veg') return r.cuisine_type === 'veg'
    if (filterType === 'non_veg') return r.cuisine_type === 'non_veg'
    if (filterType === 'easy') return r.difficulty === 'easy'
    return true
  })

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Display vault header with total counts and primary call-to-actions. */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">Recipe Vault</h1>
          <p className="mt-1 text-sm text-slate-400">
            {recipes.length} recipes in your personal library
          </p>
        </div>

        {/* Action buttons allow data synchronization and navigation to ingestion. */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onRefresh}
            title="Refresh recipes"
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={onNavigateToCapture}
            className="px-4 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-medium text-sm flex items-center space-x-2 shadow-lg shadow-orange-500/20 transition-all cursor-pointer"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Add Recipe</span>
          </button>
        </div>
      </div>

      {/* Render input field and dietary filter chips for rapid recipe discovery. */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search recipes, ingredients, tags (e.g. paneer, biryani)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-800 bg-slate-900/90 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
          />
        </div>

        {/* Quick-filter pill buttons filter by vegetarian status and cooking difficulty. */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Filter className="w-4 h-4 text-slate-500 mr-1 hidden sm:block" />
          {[
            { id: 'all', label: 'All' },
            { id: 'veg', label: 'Pure Veg' },
            { id: 'non_veg', label: 'Non-Veg' },
            { id: 'easy', label: 'Quick / Easy' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id)}
              className={`px-3 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all cursor-pointer ${
                filterType === f.id
                  ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                  : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Render grid when items match, or present a guided empty state. */}
      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((recipe, idx) => (
            <RecipeCard
              key={recipe.id || recipe._id || idx}
              recipe={recipe}
              onDelete={onDeleteRecipe}
              onSelect={onSelectRecipe}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-slate-900/90 rounded-2xl border border-dashed border-slate-800 p-8">
          <div className="w-12 h-12 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center mx-auto mb-3">
            <BookOpen className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-200">No recipes found</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-sm mx-auto">
            {search
              ? 'Try adjusting your search query or filter.'
              : 'Capture your first recipe from a cookbook photo, reel, or URL.'}
          </p>
          <button
            onClick={onNavigateToCapture}
            className="mt-4 px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-medium text-xs shadow-lg shadow-orange-500/20 transition-all cursor-pointer"
          >
            Go to AI Capture
          </button>
        </div>
      )}
    </div>
  )
}
