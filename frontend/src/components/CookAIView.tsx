/**
 * Cook AI workspace for pantry-to-plate meal generation and recipe readiness ranking.
 * Displays "What Can I Cook?" match results and interactive generative chef.
 */

import React, { useState, useEffect } from 'react'
import {
  Flame,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  Plus,
  RefreshCw,
  ShoppingBag,
  ChefHat,
} from 'lucide-react'
import type {
  PantryMatchResult,
  PantryToPlateResponse,
  Recipe,
  SubstitutionSuggestion,
} from '../types'
import {
  fetchWhatCanICook,
  fetchSubstitutions,
  generatePantryMeal,
  createRecipe,
  addShoppingListItem,
} from '../api'

interface CookAIViewProps {
  /** Callback when user selects a recipe to view details. */
  onSelectRecipe: (recipeId: string) => void
  /** Callback to trigger refresh of main recipe list. */
  onRecipeCreated?: () => void
  /** Switch to shopping list tab. */
  onOpenShoppingList?: () => void
}

export const CookAIView: React.FC<CookAIViewProps> = ({
  onSelectRecipe,
  onRecipeCreated,
  onOpenShoppingList,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'what-to-cook' | 'pantry-to-plate'>('what-to-cook')
  const [matches, setMatches] = useState<PantryMatchResult[]>([])
  const [filterReadyOnly, setFilterReadyOnly] = useState(false)
  const [loadingMatches, setLoadingMatches] = useState(false)
  const [matchError, setMatchError] = useState<string | null>(null)

  // Substitution modal state
  const [selectedMissingItem, setSelectedMissingItem] = useState<string | null>(null)
  const [subSuggestion, setSubSuggestion] = useState<SubstitutionSuggestion | null>(null)
  const [loadingSub, setLoadingSub] = useState(false)
  const [addedToListMessage, setAddedToListMessage] = useState<string | null>(null)

  // Pantry to Plate generator state
  const [dietary, setDietary] = useState<string>('vegetarian')
  const [maxMinutes, setMaxMinutes] = useState<number>(30)
  const [servings, setServings] = useState<number>(2)
  const [generating, setGenerating] = useState(false)
  const [generatorError, setGeneratorError] = useState<string | null>(null)
  const [generatedMeal, setGeneratedMeal] = useState<PantryToPlateResponse | null>(null)
  const [savingRecipe, setSavingRecipe] = useState(false)
  const [recipeSaved, setRecipeSaved] = useState(false)

  // Load "What can I cook?" matches on mount and filter changes.
  useEffect(() => {
    async function loadMatches() {
      setLoadingMatches(true)
      setMatchError(null)
      try {
        const results = await fetchWhatCanICook(filterReadyOnly)
        setMatches(results)
      } catch (err: any) {
        setMatchError(err.message || 'Failed to analyze pantry recipes')
      } finally {
        setLoadingMatches(false)
      }
    }
    if (activeSubTab === 'what-to-cook') {
      void loadMatches()
    }
  }, [filterReadyOnly, activeSubTab])

  // Open substitution inspection modal.
  async function handleInspectSubstitution(ingredient: string) {
    setSelectedMissingItem(ingredient)
    setSubSuggestion(null)
    setLoadingSub(true)
    setAddedToListMessage(null)
    try {
      const result = await fetchSubstitutions(ingredient)
      setSubSuggestion(result)
    } catch {
      setSubSuggestion(null)
    } finally {
      setLoadingSub(false)
    }
  }

  // Add missing item directly to shopping list.
  async function handleAddMissingToShoppingList(itemName: string) {
    try {
      await addShoppingListItem({
        name: itemName,
        quantity: 1.0,
        unit: 'item',
      })
      setAddedToListMessage(`Added "${itemName}" to your shopping list!`)
    } catch {
      setAddedToListMessage(`Failed to add "${itemName}" to shopping list`)
    }
  }

  // Trigger generative Pantry-to-Plate chef.
  async function handleGeneratePantryMeal() {
    setGenerating(true)
    setGeneratorError(null)
    setGeneratedMeal(null)
    setRecipeSaved(false)
    try {
      const response = await generatePantryMeal({
        dietary_preference: dietary,
        max_prep_time_minutes: maxMinutes,
        servings,
      })
      setGeneratedMeal(response)
    } catch (err: any) {
      setGeneratorError(err.message || 'Failed to generate meal proposal')
    } finally {
      setGenerating(false)
    }
  }

  // Save generated meal directly into the recipe vault.
  async function handleSaveGeneratedRecipe() {
    if (!generatedMeal) return
    setSavingRecipe(true)
    try {
      const payload: Partial<Recipe> = {
        title: generatedMeal.title,
        description: generatedMeal.description,
        prep_time_minutes: generatedMeal.prep_time_minutes,
        cook_time_minutes: generatedMeal.cook_time_minutes,
        servings: generatedMeal.servings,
        cuisine_type: dietary,
        region: 'Pan-India',
        ingredients: generatedMeal.ingredients.map((ing) => ({
          name: ing.item,
          quantity: ing.amount,
          unit: ing.unit,
        })),
        steps: generatedMeal.steps.map((st, idx) => ({
          step_number: idx + 1,
          instruction: st,
        })),
        tags: ['cook-ai', 'pantry-to-plate'],
      }
      await createRecipe(payload)
      setRecipeSaved(true)
      if (onRecipeCreated) {
        onRecipeCreated()
      }
    } catch (err: any) {
      setGeneratorError(err.message || 'Failed to save generated recipe')
    } finally {
      setSavingRecipe(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30">
              <Flame className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-slate-100">Cook AI</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Turn your active pantry inventory into actionable home-cooked meals.
          </p>
        </div>

        {/* Sub-tab navigation switch */}
        <div className="flex bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
          <button
            onClick={() => setActiveSubTab('what-to-cook')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeSubTab === 'what-to-cook'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            What Can I Cook?
          </button>
          <button
            onClick={() => setActiveSubTab('pantry-to-plate')}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition-all ${
              activeSubTab === 'pantry-to-plate'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Pantry-to-Plate Chef</span>
          </button>
        </div>
      </div>

      {/* --- Tab 1: What Can I Cook Right Now? --- */}
      {activeSubTab === 'what-to-cook' && (
        <div>
          {/* Readiness Filter Bar */}
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setFilterReadyOnly(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  !filterReadyOnly
                    ? 'bg-slate-700 text-white border border-slate-600'
                    : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
                }`}
              >
                All Ranked Recipes
              </button>
              <button
                onClick={() => setFilterReadyOnly(true)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1 transition-all ${
                  filterReadyOnly
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>100% Ready to Cook</span>
              </button>
            </div>

            <span className="text-xs text-slate-400">
              Ranked with FEFO expiry priority boost
            </span>
          </div>

          {/* Error Banner */}
          {matchError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm mb-6">
              {matchError}
            </div>
          )}

          {/* Loading Spinner */}
          {loadingMatches ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
              <RefreshCw className="w-6 h-6 animate-spin text-orange-400" />
              <p className="text-sm">Evaluating pantry inventory against recipes...</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="text-center py-16 bg-slate-800/20 rounded-2xl border border-slate-800 p-8">
              <Flame className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-slate-300">No matching recipes found</h3>
              <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
                {filterReadyOnly
                  ? 'No recipes in your vault currently have 100% ingredients in stock. Try toggling "All Ranked Recipes" or check substitutions.'
                  : 'Add recipes to your vault and scan grocery bills to start seeing recommendations.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {matches.map((match) => (
                <div
                  key={match.recipe_id}
                  className="bg-slate-800/60 rounded-2xl border border-slate-700/50 p-5 flex flex-col justify-between hover:border-orange-500/40 transition-all shadow-sm"
                >
                  <div>
                    {/* Header: Title and Readiness Badge */}
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <h3
                        onClick={() => onSelectRecipe(match.recipe_id)}
                        className="font-bold text-slate-100 text-base hover:text-orange-400 cursor-pointer transition-colors"
                      >
                        {match.recipe_title}
                      </h3>
                      {match.can_cook_now ? (
                        <span className="shrink-0 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          Ready to Cook
                        </span>
                      ) : (
                        <span className="shrink-0 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          Missing {match.missing_ingredients.length}
                        </span>
                      )}
                    </div>

                    {/* Expiry Boost Tag */}
                    {match.expiry_urgency_score > 0 && (
                      <div className="inline-flex items-center space-x-1 text-xs text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded-md mb-3 border border-orange-500/20">
                        <Clock className="w-3 h-3" />
                        <span>Uses soon-to-expire stock</span>
                      </div>
                    )}

                    {/* Coverage Progress Bar */}
                    <div className="space-y-1 mb-4">
                      <div className="flex justify-between text-xs text-slate-400">
                        <span>Pantry Coverage</span>
                        <span className="font-semibold text-slate-200">
                          {Math.round(match.coverage_percentage)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-700/60 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            match.can_cook_now ? 'bg-emerald-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${Math.min(100, match.coverage_percentage)}%` }}
                        />
                      </div>
                    </div>

                    {/* Missing Ingredients Pills */}
                    {match.missing_ingredients.length > 0 && (
                      <div className="space-y-2 mb-4">
                        <span className="text-xs text-slate-400 font-medium">Missing:</span>
                        <div className="flex flex-wrap gap-1.5">
                          {match.missing_ingredients.map((ing) => (
                            <button
                              key={ing}
                              onClick={() => handleInspectSubstitution(ing)}
                              className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 hover:border-orange-500 hover:text-orange-400 transition-all flex items-center space-x-1"
                              title="Click to check substitutions or add to cart"
                            >
                              <span>{ing}</span>
                              <span className="text-orange-400">⚡</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Action button */}
                  <div className="pt-4 border-t border-slate-700/50 flex justify-between items-center">
                    <button
                      onClick={() => onSelectRecipe(match.recipe_id)}
                      className="text-xs font-semibold text-orange-400 hover:text-orange-300 flex items-center space-x-1"
                    >
                      <span>View Recipe</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* --- Tab 2: Generative Pantry-to-Plate Chef --- */}
      {activeSubTab === 'pantry-to-plate' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Controls Column */}
          <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/50 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-orange-400" />
                <span>Pantry-to-Plate Chef</span>
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Generates a recipe strictly using what you have in stock, prioritizing expiring items.
              </p>
            </div>

            {/* Dietary Preference */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Dietary Preference
              </label>
              <select
                value={dietary}
                onChange={(e) => setDietary(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-orange-500"
              >
                <option value="vegetarian">Vegetarian (Pure Veg)</option>
                <option value="vegan">Vegan</option>
                <option value="jain">Jain (No Root Veg)</option>
                <option value="high-protein">High Protein</option>
                <option value="non-veg">Non-Vegetarian</option>
              </select>
            </div>

            {/* Target Time */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Maximum Cooking Time: {maxMinutes} mins
              </label>
              <input
                type="range"
                min="15"
                max="60"
                step="5"
                value={maxMinutes}
                onChange={(e) => setMaxMinutes(Number(e.target.value))}
                className="w-full accent-orange-500"
              />
            </div>

            {/* Portions */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Portions: {servings}
              </label>
              <div className="flex space-x-2">
                {[1, 2, 4, 6].map((num) => (
                  <button
                    key={num}
                    onClick={() => setServings(num)}
                    className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                      servings === num
                        ? 'bg-orange-500 text-white'
                        : 'bg-slate-900 text-slate-400 border border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleGeneratePantryMeal}
              disabled={generating}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-semibold text-sm shadow-md shadow-orange-500/20 hover:opacity-95 disabled:opacity-50 transition-all flex items-center justify-center space-x-2"
            >
              {generating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Designing Recipe...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Recipe</span>
                </>
              )}
            </button>

            {generatorError && (
              <p className="text-xs text-rose-400 bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
                {generatorError}
              </p>
            )}
          </div>

          {/* Output Recipe Column */}
          <div className="lg:col-span-2">
            {!generatedMeal && !generating && (
              <div className="h-full min-h-[300px] flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-2xl p-8 text-center text-slate-500">
                <ChefHat className="w-12 h-12 text-slate-600 mb-3" />
                <h3 className="text-base font-semibold text-slate-400">Ready to design your meal</h3>
                <p className="text-xs max-w-sm mt-1">
                  Adjust preferences and click "Generate Recipe" to produce a dish crafted strictly from active pantry stock.
                </p>
              </div>
            )}

            {generating && (
              <div className="h-full min-h-[300px] flex flex-col items-center justify-center bg-slate-800/30 rounded-2xl border border-slate-800 p-8 text-center space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-orange-500/20 text-orange-400 flex items-center justify-center animate-pulse">
                  <Sparkles className="w-6 h-6 animate-spin" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-200">The Chef is Thinking...</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-md">
                    Scanning pantry items, checking shelf-life urgency, and constructing balanced Indian spices.
                  </p>
                </div>
              </div>
            )}

            {generatedMeal && (
              <div className="bg-slate-800/60 rounded-2xl border border-slate-700/60 p-6 space-y-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-bold text-slate-100">{generatedMeal.title}</h2>
                    <p className="text-sm text-slate-400 mt-1">{generatedMeal.description}</p>
                    <div className="flex items-center space-x-4 mt-3 text-xs text-slate-300">
                      <span className="flex items-center space-x-1">
                        <Clock className="w-3.5 h-3.5 text-orange-400" />
                        <span>{generatedMeal.prep_time_minutes + generatedMeal.cook_time_minutes} mins</span>
                      </span>
                      <span>•</span>
                      <span>Serves {generatedMeal.servings}</span>
                    </div>
                  </div>

                  <button
                    onClick={handleSaveGeneratedRecipe}
                    disabled={savingRecipe || recipeSaved}
                    className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition-all ${
                      recipeSaved
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-orange-500 hover:bg-orange-600 text-white shadow-sm'
                    }`}
                  >
                    {recipeSaved ? (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Saved to Vault</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        <span>Save to Vault</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Ingredients */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Ingredients
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {generatedMeal.ingredients.map((ing, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-xs bg-slate-900/60 px-3 py-2 rounded-lg border border-slate-800"
                      >
                        <span className="text-slate-200 capitalize">{ing.item}</span>
                        <span className="text-slate-400 font-mono">
                          {ing.amount} {ing.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Steps */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Cooking Steps
                  </h4>
                  <ol className="space-y-2.5">
                    {generatedMeal.steps.map((step, idx) => (
                      <li key={idx} className="flex space-x-3 text-xs text-slate-300 leading-relaxed">
                        <span className="w-5 h-5 rounded-full bg-slate-700/60 text-orange-400 flex items-center justify-center shrink-0 font-bold">
                          {idx + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- Substitution & Shopping Modal --- */}
      {selectedMissingItem && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
                  Missing Ingredient
                </span>
                <h3 className="text-lg font-bold text-slate-100 capitalize">
                  {selectedMissingItem}
                </h3>
              </div>
              <button
                onClick={() => setSelectedMissingItem(null)}
                className="text-slate-400 hover:text-slate-200 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            {loadingSub ? (
              <div className="py-8 flex flex-col items-center justify-center space-y-2 text-slate-400 text-xs">
                <RefreshCw className="w-5 h-5 animate-spin text-orange-400" />
                <span>Checking your pantry for culinary substitutes...</span>
              </div>
            ) : subSuggestion ? (
              <div className="space-y-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
                <div className="flex items-center space-x-2 text-emerald-400 font-semibold text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>In-Stock Substitute Available!</span>
                </div>
                <div className="text-xs text-slate-300 space-y-1">
                  <p>
                    <strong className="text-slate-100">Use: </strong>
                    <span className="capitalize font-semibold text-emerald-300">
                      {subSuggestion.substitute_item}
                    </span>
                  </p>
                  <p>
                    <strong className="text-slate-100">Ratio: </strong>
                    {subSuggestion.ratio_or_amount}
                  </p>
                  <p className="text-slate-400 mt-1 italic">{subSuggestion.reason}</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-center space-x-2 text-amber-400 font-semibold text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <span>No In-Stock Substitute Found</span>
                </div>
                <p className="text-xs text-slate-400">
                  You don't currently have an appropriate substitute in your pantry. We recommend adding this to your shopping list or ordering via quick-commerce.
                </p>
              </div>
            )}

            {/* Quick-Commerce & Shopping List Actions */}
            <div className="pt-2 space-y-2">
              <button
                onClick={() => handleAddMissingToShoppingList(selectedMissingItem)}
                className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-colors border border-slate-700"
              >
                <ShoppingBag className="w-3.5 h-3.5 text-orange-400" />
                <span>Add to Shopping List</span>
              </button>

              <div className="grid grid-cols-3 gap-2">
                <a
                  href={`https://blinkit.com/s/?q=${encodeURIComponent(selectedMissingItem)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="py-2 rounded-lg bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 text-xs font-semibold text-center transition-all"
                >
                  Blinkit ⚡
                </a>
                <a
                  href={`https://zepto.com/search?q=${encodeURIComponent(selectedMissingItem)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="py-2 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs font-semibold text-center transition-all"
                >
                  Zepto 🚀
                </a>
                <a
                  href={`https://www.swiggy.com/instamart/search?query=${encodeURIComponent(selectedMissingItem)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="py-2 rounded-lg bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 border border-orange-500/30 text-xs font-semibold text-center transition-all"
                >
                  Instamart 🛒
                </a>
              </div>
            </div>

            {addedToListMessage && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400">
                <span>{addedToListMessage}</span>
                {onOpenShoppingList && (
                  <button
                    onClick={() => {
                      setSelectedMissingItem(null)
                      onOpenShoppingList()
                    }}
                    className="underline font-semibold hover:text-emerald-300 ml-2"
                  >
                    View List
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
