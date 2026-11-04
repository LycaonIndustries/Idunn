import { useEffect, useState } from 'react'
import {
  createShoppingItemsBatch,
  fetchSubstitutions,
  fetchWhatCanICook,
  generatePantryRecipe,
} from '../api'
import type {
  PantryMatchResult,
  PantryToPlateRecipe,
  SubstitutionSuggestion,
} from '../types'

export function CookAIView() {
  const [tab, setTab] = useState<'vault' | 'chef'>('vault')
  const [matches, setMatches] = useState<PantryMatchResult[]>([])
  const [readyOnly, setReadyOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notification, setNotification] = useState<string | null>(null)
  const [activeSubIngredient, setActiveSubIngredient] = useState<string | null>(null)
  const [substitutions, setSubstitutions] = useState<SubstitutionSuggestion[]>([])
  const [loadingSubs, setLoadingSubs] = useState(false)
  const [servings, setServings] = useState(2)
  const [mealType, setMealType] = useState('dinner')
  const [dietary, setDietary] = useState('veg')
  const [generating, setGenerating] = useState(false)
  const [generatedRecipe, setGeneratedRecipe] = useState<PantryToPlateRecipe | null>(null)

  async function loadMatches(ready: boolean) {
    try {
      setLoading(true)
      setMatches(await fetchWhatCanICook(ready))
      setError(null)
    } catch (err: any) {
      setError(err.message || 'Failed to rank vault recipes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tab === 'vault') void loadMatches(readyOnly)
  }, [tab, readyOnly])

  async function handleFindSubstitutes(ing: string) {
    try {
      setActiveSubIngredient(ing)
      setLoadingSubs(true)
      setSubstitutions(await fetchSubstitutions(ing))
    } catch (err: any) {
      setError(err.message || 'Failed to load substitutions')
    } finally {
      setLoadingSubs(false)
    }
  }

  async function handleAddMissingToShopping(recipe: PantryMatchResult) {
    try {
      const items = recipe.missing_ingredients.map((name) => ({
        name,
        quantity: 1,
        unit: 'piece',
        source_recipe_id: recipe.recipe_id,
      }))
      await createShoppingItemsBatch(items)
      setNotification(`Added ${items.length} missing ingredients to Shopping List!`)
      setTimeout(() => setNotification(null), 4000)
    } catch (err: any) {
      setError(err.message || 'Failed to add items to shopping list')
    }
  }

  async function handleGenerateChefRecipe(e: React.FormEvent) {
    e.preventDefault()
    try {
      setGenerating(true)
      setError(null)
      setGeneratedRecipe(await generatePantryRecipe({ servings, meal_type: mealType, dietary_preference: dietary }))
    } catch (err: any) {
      setError(err.message || 'Failed to synthesize recipe from pantry')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Cook AI</h1>
          <p className="text-sm text-gray-500">Vault matching first; AI chef strictly on-demand.</p>
        </div>
        <div className="flex bg-gray-100 p-1 rounded-lg text-xs font-semibold">
          <button onClick={() => setTab('vault')} className={`px-3 py-1.5 rounded-md transition ${tab === 'vault' ? 'bg-white shadow text-gray-900' : 'text-gray-600'}`}>Vault Matching</button>
          <button onClick={() => setTab('chef')} className={`px-3 py-1.5 rounded-md transition ${tab === 'chef' ? 'bg-white shadow text-gray-900' : 'text-gray-600'}`}>Pantry to Plate Chef</button>
        </div>
      </div>

      {notification && <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded-md">{notification}</div>}
      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">{error}</div>}

      {tab === 'vault' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={readyOnly} onChange={(e) => setReadyOnly(e.target.checked)} className="rounded text-amber-600" />
              <span>100% Ready to Cook Only</span>
            </label>
            <span className="text-xs text-gray-400">{matches.length} recipes found</span>
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-400">Evaluating pantry against vault recipes...</div>
          ) : matches.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 border border-dashed rounded-lg">
              <p className="text-gray-500 font-medium">No recipes match current pantry stock.</p>
              <p className="text-xs text-gray-400 mt-1">Uncheck &quot;100% Ready&quot; or add ingredients to your pantry.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {matches.map((item) => (
                <div key={item.recipe_id} className="p-4 bg-white border rounded-lg space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-semibold text-gray-900">{item.recipe_title}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-700">{Math.round(item.coverage_percentage)}% in stock</span>
                        {item.can_cook_now && <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">Ready to Cook</span>}
                        {item.expiry_urgency_score > 0 && <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800">Uses Expiring Items!</span>}
                      </div>
                    </div>
                    {item.missing_ingredients.length > 0 && (
                      <button onClick={() => void handleAddMissingToShopping(item)} className="text-xs font-medium px-3 py-1.5 rounded-md border border-amber-600 text-amber-700 hover:bg-amber-50 transition">+ Add Missing to Shopping</button>
                    )}
                  </div>
                  {item.missing_ingredients.length > 0 && (
                    <div className="text-xs space-y-1">
                      <span className="text-gray-500 font-medium">Missing:</span>
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {item.missing_ingredients.map((ing) => (
                          <button key={ing} onClick={() => void handleFindSubstitutes(ing)} className="px-2 py-0.5 rounded bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition">{ing} (find sub)</button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'chef' && (
        <div className="space-y-6">
          <form onSubmit={(e) => void handleGenerateChefRecipe(e)} className="p-4 bg-gray-50 border rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wider">On-Demand Chef Recipe Synthesis</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Servings</label>
                <input type="number" min="1" max="12" value={servings} onChange={(e) => setServings(parseInt(e.target.value) || 2)} className="w-full px-3 py-1.5 border rounded-md text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Meal Type</label>
                <select value={mealType} onChange={(e) => setMealType(e.target.value)} className="w-full px-3 py-1.5 border rounded-md text-sm bg-white">
                  <option value="dinner">Dinner</option>
                  <option value="lunch">Lunch</option>
                  <option value="quick meal">Quick 15-min Meal</option>
                  <option value="snack">Snack / Appetizer</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Dietary</label>
                <select value={dietary} onChange={(e) => setDietary(e.target.value)} className="w-full px-3 py-1.5 border rounded-md text-sm bg-white">
                  <option value="veg">Vegetarian</option>
                  <option value="non_veg">Non-Vegetarian</option>
                </select>
              </div>
            </div>
            <button type="submit" disabled={generating} className="w-full py-2.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-md text-sm transition disabled:opacity-50">
              {generating ? 'Chef is Crafting Recipe...' : 'Synthesize Custom Recipe from Pantry'}
            </button>
          </form>

          {generatedRecipe && (
            <div className="p-6 bg-white border rounded-lg space-y-4 shadow-sm">
              <div className="border-b pb-3">
                <h3 className="text-xl font-bold text-gray-900">{generatedRecipe.title}</h3>
                <p className="text-sm text-gray-600 mt-1">{generatedRecipe.description}</p>
                <div className="flex gap-4 mt-2 text-xs text-gray-500">
                  <span>Prep: {generatedRecipe.prep_time_minutes} min</span>
                  <span>Cook: {generatedRecipe.cook_time_minutes} min</span>
                  <span>Servings: {generatedRecipe.servings}</span>
                </div>
              </div>
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-900">
                <strong>Assumed basic kitchen staples used:</strong> {generatedRecipe.assumed_staples.join(', ')}
              </div>
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase text-gray-500">Pantry Ingredients Used</h4>
                <ul className="list-disc list-inside text-sm text-gray-700 space-y-0.5">
                  {generatedRecipe.ingredients.map((ing, idx) => (
                    <li key={idx}>{ing.name} ({ing.quantity} {ing.unit})</li>
                  ))}
                </ul>
              </div>
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase text-gray-500">Step-by-Step Directions</h4>
                <ol className="list-decimal list-inside text-sm text-gray-700 space-y-1">
                  {generatedRecipe.steps.map((st) => <li key={st.step_number}>{st.instruction}</li>)}
                </ol>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Substitution Modal */}
      {activeSubIngredient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b pb-2">
              <h3 className="font-bold text-gray-900">Substitutes for: <span className="text-amber-600">{activeSubIngredient}</span></h3>
              <button onClick={() => setActiveSubIngredient(null)} className="text-gray-400 hover:text-gray-600 text-sm font-bold">✕</button>
            </div>
            {loadingSubs ? (
              <div className="text-center py-6 text-gray-400 text-sm">Finding culinary alternatives...</div>
            ) : substitutions.length === 0 ? (
              <div className="text-center py-6 text-gray-500 text-sm">No standard functional substitutes found in culinary graph.</div>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto divide-y">
                {substitutions.map((sub, i) => (
                  <div key={i} className="pt-2 first:pt-0 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm text-gray-900">{sub.substitute_name}</span>
                      {sub.in_pantry ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">In Your Pantry!</span>
                      ) : (
                        <span className="text-xs text-gray-400 uppercase">{sub.category}</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500"><span>Ratio: {sub.ratio}</span> — <span>{sub.notes}</span></div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
