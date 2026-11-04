import React, { useState } from 'react'
import { Search, Filter, RefreshCw, PlusCircle, BookOpen } from 'lucide-react'
import type { Recipe } from '../types'
import { RecipeCard } from './RecipeCard'

interface RecipeVaultProps {
  recipes: Recipe[]
  loading: boolean
  onRefresh: () => void
  onDeleteRecipe: (id: string) => void
  onNavigateToCapture: () => void
  onSelectRecipe?: (recipe: Recipe) => void
}

export const RecipeVault: React.FC<RecipeVaultProps> = ({
  recipes,
  loading,
  onRefresh,
  onDeleteRecipe,
  onNavigateToCapture,
  onSelectRecipe,
}) => {
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState<string>('all')

  const filtered = recipes.filter((r) => {
    const matchesSearch =
      r.title.toLowerCase().includes(search.toLowerCase()) ||
      r.ingredients.some((i) => i.name.toLowerCase().includes(search.toLowerCase())) ||
      (r.tags && r.tags.some((t) => t.toLowerCase().includes(search.toLowerCase())))

    if (!matchesSearch) return false

    if (filterType === 'all') return true
    if (filterType === 'veg') return r.cuisine_type === 'veg'
    if (filterType === 'non_veg') return r.cuisine_type === 'non_veg'
    if (filterType === 'easy') return r.difficulty === 'easy'
    return true
  })

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">Recipe Vault</h1>
          <p className="mt-1 text-sm text-slate-400">
            {recipes.length} recipes in your personal library
          </p>
        </div>

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

      {/* Search & Filter Bar */}
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

      {/* Grid or Empty State */}
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
            {search ? 'Try adjusting your search query or filter.' : 'Capture your first recipe from a cookbook photo, reel, or URL.'}
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
