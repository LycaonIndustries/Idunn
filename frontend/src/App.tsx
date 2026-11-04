import { useEffect, useState, useCallback } from 'react'
import type { InventoryItem, Recipe } from './types'
import { fetchInventory, fetchRecipes, deleteRecipe } from './api'
import { Navbar } from './components/Navbar'
import { CaptureZone } from './components/CaptureZone'
import { RecipeVault } from './components/RecipeVault'
import { PantryView } from './components/PantryView'

export function App() {
  const [activeTab, setActiveTab] = useState<'capture' | 'vault' | 'pantry'>('capture')
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [recipesLoading, setRecipesLoading] = useState(false)
  const [inventoryLoading, setInventoryLoading] = useState(false)

  const loadRecipes = useCallback(async () => {
    setRecipesLoading(true)
    try {
      const data = await fetchRecipes()
      setRecipes(data)
    } catch (err) {
      console.error('Failed to load recipes:', err)
    } finally {
      setRecipesLoading(false)
    }
  }, [])

  const loadInventory = useCallback(async () => {
    setInventoryLoading(true)
    try {
      const data = await fetchInventory()
      setInventory(data)
    } catch (err) {
      console.error('Failed to load inventory:', err)
    } finally {
      setInventoryLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRecipes()
    loadInventory()
  }, [loadRecipes, loadInventory])

  const handleRecipeSaved = (newRecipe: Recipe) => {
    setRecipes((prev) => [newRecipe, ...prev])
  }

  const handleDeleteRecipe = async (id: string) => {
    try {
      await deleteRecipe(id)
      setRecipes((prev) => prev.filter((r) => (r.id || r._id) !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const handleItemAdded = (item: InventoryItem) => {
    setInventory((prev) => [item, ...prev])
  }

  const handleItemDeleted = (id: string) => {
    setInventory((prev) => prev.filter((i) => i.id !== id))
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        recipeCount={recipes.length}
        pantryCount={inventory.length}
      />

      <main className="flex-1">
        {activeTab === 'capture' && (
          <CaptureZone onRecipeSaved={handleRecipeSaved} />
        )}

        {activeTab === 'vault' && (
          <RecipeVault
            recipes={recipes}
            loading={recipesLoading}
            onRefresh={loadRecipes}
            onDeleteRecipe={handleDeleteRecipe}
            onNavigateToCapture={() => setActiveTab('capture')}
          />
        )}

        {activeTab === 'pantry' && (
          <PantryView
            items={inventory}
            loading={inventoryLoading}
            onRefresh={loadInventory}
            onItemAdded={handleItemAdded}
            onItemDeleted={handleItemDeleted}
          />
        )}
      </main>

      <footer className="py-6 border-t border-slate-200 bg-white text-center text-xs text-slate-400">
        <p>Iðunn Kitchen OS • Multimodal AI Recipe Vault & Pantry</p>
      </footer>
    </div>
  )
}

export default App
