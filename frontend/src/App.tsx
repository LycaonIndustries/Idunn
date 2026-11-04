import { useEffect, useState, useCallback } from 'react'
import type { InventoryItem, Recipe, SettingsStatus } from './types'
import { fetchInventory, fetchRecipes, deleteRecipe, fetchSettingsStatus } from './api'
import { Navbar } from './components/Navbar'
import { CaptureZone } from './components/CaptureZone'
import { RecipeVault } from './components/RecipeVault'
import { PantryView } from './components/PantryView'
import { SettingsView } from './components/SettingsView'

export function App() {
  const [activeTab, setActiveTab] = useState<'capture' | 'vault' | 'pantry' | 'settings'>('capture')
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [settingsStatus, setSettingsStatus] = useState<SettingsStatus | null>(null)
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

  const loadSettings = useCallback(async () => {
    try {
      const data = await fetchSettingsStatus()
      setSettingsStatus(data)
    } catch (err) {
      console.error('Failed to load settings status:', err)
    }
  }, [])

  useEffect(() => {
    loadRecipes()
    loadInventory()
    loadSettings()
  }, [loadRecipes, loadInventory, loadSettings])

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

  const isByokConfigured = Boolean(
    settingsStatus?.gemini_configured ||
    settingsStatus?.anthropic_configured ||
    settingsStatus?.openai_configured
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-orange-500/30 selection:text-orange-200">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        recipeCount={recipes.length}
        pantryCount={inventory.length}
        isByokConfigured={isByokConfigured}
      />

      <main className="flex-1">
        {activeTab === 'capture' && (
          <CaptureZone
            onRecipeSaved={handleRecipeSaved}
            onNavigateToSettings={() => setActiveTab('settings')}
            isByokConfigured={isByokConfigured}
          />
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

        {activeTab === 'settings' && (
          <SettingsView
            onSettingsUpdated={loadSettings}
          />
        )}
      </main>

      <footer className="py-6 border-t border-slate-900 bg-slate-950 text-center text-xs text-slate-500">
        <p>Iðunn Kitchen OS • Multimodal AI Recipe Vault & Pantry • Dark Mode Active</p>
      </footer>
    </div>
  )
}

export default App
