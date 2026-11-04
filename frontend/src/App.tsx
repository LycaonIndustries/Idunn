/**
 * Root Application component for Iðunn Kitchen OS.
 * Manages top-level navigation tabs, global recipe cache, and active settings state.
 */

import { useEffect, useState, useCallback } from 'react'
import type { InventoryItem, Recipe, SettingsStatus } from './types'
import { fetchInventory, fetchRecipes, deleteRecipe, fetchSettingsStatus } from './api'
import { Navbar } from './components/Navbar'
import { CaptureZone } from './components/CaptureZone'
import { RecipeVault } from './components/RecipeVault'
import { RecipeDetailPage } from './components/RecipeDetailPage'
import { PantryView } from './components/PantryView'
import { SettingsView } from './components/SettingsView'
import { CookAIView } from './components/CookAIView'
import { ShoppingListView } from './components/ShoppingListView'

/**
 * Main application container with tab navigation and state coordination.
 *
 * @returns Rendered Single Page Application layout.
 */
export function App() {
  // Track active navigation tab. Defaults to 'capture' for fast recipe imports.
  const [activeTab, setActiveTab] = useState<'capture' | 'vault' | 'pantry' | 'cook-ai' | 'shopping' | 'settings'>('capture')

  // Hold currently viewed recipe for dedicated full-page inspection.
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null)

  // Cache recipes and inventory items in memory to eliminate redundant network roundtrips.
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [settingsStatus, setSettingsStatus] = useState<SettingsStatus | null>(null)
  const [recipesLoading, setRecipesLoading] = useState(false)
  const [inventoryLoading, setInventoryLoading] = useState(false)

  // Fetch all recipes from the backend and populate local state.
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

  // Fetch active pantry inventory for FEFO expiration monitoring.
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

  // Load server provider configuration to show BYOK warnings when keys are missing.
  const loadSettings = useCallback(async () => {
    try {
      const data = await fetchSettingsStatus()
      setSettingsStatus(data)
    } catch (err) {
      console.error('Failed to load settings status:', err)
    }
  }, [])

  // Synchronize initial data once on mount.
  useEffect(() => {
    void loadRecipes()
    void loadInventory()
    void loadSettings()
  }, [loadRecipes, loadInventory, loadSettings])

  // Reset selected recipe detail view when switching main navigation tabs.
  // This prevents the user from remaining trapped in a detail view on unrelated tabs.
  const handleTabChange = (tab: 'capture' | 'vault' | 'pantry' | 'cook-ai' | 'shopping' | 'settings') => {
    setSelectedRecipe(null)
    setActiveTab(tab)
  }

  // Prepend newly imported recipe and transition immediately to its detail view.
  // This gives instant visual confirmation that the ingestion stream succeeded.
  const handleRecipeSaved = (newRecipe: Recipe) => {
    setRecipes((prev) => [newRecipe, ...prev])
    setSelectedRecipe(newRecipe)
    setActiveTab('vault')
  }

  // Delete recipe from server and update local cache optimistically.
  const handleDeleteRecipe = async (id: string) => {
    try {
      await deleteRecipe(id)
      setRecipes((prev) => prev.filter((r) => (r.id || r._id) !== id))
      if (selectedRecipe && (selectedRecipe.id || selectedRecipe._id) === id) {
        setSelectedRecipe(null)
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  // Update inventory cache when a new item is added from the pantry modal.
  const handleItemAdded = (item: InventoryItem) => {
    setInventory((prev) => [item, ...prev])
  }

  // Remove deleted item from local inventory state.
  const handleItemDeleted = (id: string) => {
    setInventory((prev) => prev.filter((i) => i.id !== id))
  }

  // Determine whether any AI provider key is configured to guide user onboarding banners.
  const isByokConfigured = Boolean(
    settingsStatus?.gemini_configured ||
      settingsStatus?.anthropic_configured ||
      settingsStatus?.openai_configured
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-orange-500/30 selection:text-orange-200">
      {/* Global application navbar with live item counters */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={handleTabChange}
        recipeCount={recipes.length}
        pantryCount={inventory.length}
        isByokConfigured={isByokConfigured}
      />

      {/* Main content body switching between functional tabs */}
      <main className="flex-1">
        {activeTab === 'capture' && (
          <CaptureZone
            onRecipeSaved={handleRecipeSaved}
            onNavigateToSettings={() => handleTabChange('settings')}
            isByokConfigured={isByokConfigured}
          />
        )}

        {activeTab === 'vault' &&
          (selectedRecipe ? (
            <RecipeDetailPage
              recipe={selectedRecipe}
              onBack={() => setSelectedRecipe(null)}
              onDelete={handleDeleteRecipe}
            />
          ) : (
            <RecipeVault
              recipes={recipes}
              loading={recipesLoading}
              onRefresh={loadRecipes}
              onDeleteRecipe={handleDeleteRecipe}
              onNavigateToCapture={() => handleTabChange('capture')}
              onSelectRecipe={(recipe) => setSelectedRecipe(recipe)}
            />
          ))}

        {activeTab === 'pantry' && (
          <PantryView
            items={inventory}
            loading={inventoryLoading}
            onRefresh={loadInventory}
            onItemAdded={handleItemAdded}
            onItemDeleted={handleItemDeleted}
          />
        )}

        {activeTab === 'cook-ai' && <CookAIView />}

        {activeTab === 'shopping' && <ShoppingListView />}

        {activeTab === 'settings' && <SettingsView onSettingsUpdated={loadSettings} />}
      </main>

      {/* Persistent footer */}
      <footer className="py-6 border-t border-slate-900 bg-slate-950 text-center text-xs text-slate-500">
        <p>Iðunn Kitchen OS • Multimodal AI Recipe Vault & Pantry • Dark Mode Active</p>
      </footer>
    </div>
  )
}

export default App
