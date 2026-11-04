/**
 * Shopping list management view for Iðunn Kitchen OS.
 * Manages missing recipe ingredients and manual grocery restock items.
 */

import React, { useState, useEffect } from 'react'
import {
  ShoppingBag,
  Plus,
  Trash2,
  CheckCircle2,
  Circle,
  ExternalLink,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import type { ShoppingListItem } from '../types'
import {
  fetchShoppingList,
  addShoppingListItem,
  updateShoppingListItem,
  deleteShoppingListItem,
  clearPurchasedShoppingItems,
} from '../api'

export const ShoppingListView: React.FC = () => {
  const [items, setItems] = useState<ShoppingListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Quick add form state
  const [newItemName, setNewItemName] = useState('')
  const [newItemQuantity, setNewItemQuantity] = useState<number>(1)
  const [newItemUnit, setNewItemUnit] = useState('count')
  const [addingItem, setAddingItem] = useState(false)

  // Fetch shopping list items from the backend API.
  const loadShoppingList = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await fetchShoppingList()
      setItems(data.items || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load shopping list')
    } finally {
      setLoading(false)
    }
  }

  // Load items once when component mounts.
  useEffect(() => {
    void loadShoppingList()
  }, [])

  // Toggle purchased checkbox for target item.
  const handleTogglePurchased = async (item: ShoppingListItem) => {
    const updatedStatus = !item.is_purchased
    try {
      // Optimistic update in UI.
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, is_purchased: updatedStatus } : i))
      )
      await updateShoppingListItem(item.id, updatedStatus)
    } catch (err: any) {
      // Rollback on network failure.
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, is_purchased: item.is_purchased } : i))
      )
      setError(err.message || 'Failed to update item status')
    }
  }

  // Remove individual item from the shopping list.
  const handleDeleteItem = async (itemId: string) => {
    try {
      setItems((prev) => prev.filter((i) => i.id !== itemId))
      await deleteShoppingListItem(itemId)
    } catch (err: any) {
      void loadShoppingList()
      setError(err.message || 'Failed to delete item')
    }
  }

  // Remove all completed items from database and local state.
  const handleClearPurchased = async () => {
    try {
      setItems((prev) => prev.filter((i) => !i.is_purchased))
      await clearPurchasedShoppingItems()
    } catch (err: any) {
      void loadShoppingList()
      setError(err.message || 'Failed to clear purchased items')
    }
  }

  // Add new grocery item directly to active shopping list.
  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newItemName.trim()) return

    try {
      setAddingItem(true)
      const created = await addShoppingListItem({
        name: newItemName.trim(),
        quantity: newItemQuantity,
        unit: newItemUnit,
      })
      setItems((prev) => [...prev, created])
      setNewItemName('')
      setNewItemQuantity(1)
    } catch (err: any) {
      setError(err.message || 'Failed to add item')
    } finally {
      setAddingItem(false)
    }
  }

  const activeItems = items.filter((i) => !i.is_purchased)
  const purchasedItems = items.filter((i) => i.is_purchased)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header and Quick Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <ShoppingBag className="w-6 h-6 text-orange-400" />
            <span>Shopping List</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Track ingredients needed for recipes and pantry restocks.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {purchasedItems.length > 0 && (
            <button
              onClick={handleClearPurchased}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              Clear Completed ({purchasedItems.length})
            </button>
          )}

          <button
            onClick={loadShoppingList}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-orange-400' : ''}`} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* Quick Add Form */}
      <form
        onSubmit={handleAddItem}
        className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4 flex flex-col sm:flex-row gap-3 items-center"
      >
        <div className="relative flex-1 w-full">
          <input
            type="text"
            placeholder="Add ingredient or item (e.g., Paneer, Coriander)..."
            value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-orange-500"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <input
            type="number"
            min="0.1"
            step="any"
            value={newItemQuantity}
            onChange={(e) => setNewItemQuantity(parseFloat(e.target.value) || 1)}
            className="w-20 bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 text-center focus:outline-none focus:border-orange-500"
          />

          <select
            value={newItemUnit}
            onChange={(e) => setNewItemUnit(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-orange-500"
          >
            <option value="count">count</option>
            <option value="g">g</option>
            <option value="kg">kg</option>
            <option value="ml">ml</option>
            <option value="l">l</option>
            <option value="tbsp">tbsp</option>
            <option value="tsp">tsp</option>
            <option value="cup">cup</option>
          </select>

          <button
            type="submit"
            disabled={addingItem || !newItemName.trim()}
            className="shrink-0 px-4 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold flex items-center space-x-1.5 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add</span>
          </button>
        </div>
      </form>

      {/* Quick Commerce 1-Click Ordering Banner */}
      {activeItems.length > 0 && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-orange-500/10 via-amber-500/10 to-yellow-500/10 border border-orange-500/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h4 className="text-sm font-bold text-slate-200 flex items-center space-x-1.5">
              <Sparkles className="w-4 h-4 text-orange-400" />
              <span>Instant Quick-Commerce Restock</span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Launch quick searches on your favorite delivery apps for unpurchased items.
            </p>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <a
              href={`https://blinkit.com/s/?q=${encodeURIComponent(
                activeItems.map((i) => i.name).slice(0, 3).join(' ')
              )}`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-300 border border-yellow-500/40 text-xs font-semibold flex items-center space-x-1 transition-all"
            >
              <span>Blinkit</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            <a
              href={`https://zepto.com/search?q=${encodeURIComponent(
                activeItems.map((i) => i.name).slice(0, 3).join(' ')
              )}`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-xs font-semibold flex items-center space-x-1 transition-all"
            >
              <span>Zepto</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            <a
              href={`https://www.swiggy.com/instamart/search?query=${encodeURIComponent(
                activeItems.map((i) => i.name).slice(0, 3).join(' ')
              )}`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-orange-500/20 hover:bg-orange-500/30 text-orange-300 border border-orange-500/40 text-xs font-semibold flex items-center space-x-1 transition-all"
            >
              <span>Instamart</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      )}

      {/* Items Section */}
      {loading && items.length === 0 ? (
        <div className="text-center py-12 text-slate-400 flex flex-col items-center space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin text-orange-400" />
          <p className="text-sm">Loading shopping list...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-slate-800/20 border border-slate-800 rounded-2xl p-8">
          <ShoppingBag className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">Your shopping list is empty</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Missing recipe ingredients and items you add manually will appear here for easy restock.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Active Items */}
          {activeItems.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
                To Buy ({activeItems.length})
              </h3>
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl divide-y divide-slate-800/80">
                {activeItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <button
                        onClick={() => handleTogglePurchased(item)}
                        className="text-slate-500 hover:text-emerald-400 transition-colors shrink-0"
                        title="Mark as purchased"
                      >
                        <Circle className="w-5 h-5" />
                      </button>

                      <div className="min-w-0">
                        <span className="text-sm font-semibold text-slate-100 capitalize">
                          {item.name}
                        </span>
                        {item.recipe_id && (
                          <p className="text-xs text-slate-500 truncate">
                            From Recipe
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0 ml-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {item.quantity} {item.unit}
                      </span>

                      {/* Quick Commerce Deep Link for this item */}
                      <a
                        href={`https://blinkit.com/s/?q=${encodeURIComponent(item.name)}`}
                        target="_blank"
                        rel="noreferrer"
                        title="Search on Blinkit"
                        className="text-xs px-2 py-1 rounded-lg bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 hidden sm:inline-block"
                      >
                        ⚡ Blinkit
                      </a>

                      <button
                        onClick={() => handleDeleteItem(item.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                        title="Delete item"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Purchased Items */}
          {purchasedItems.length > 0 && (
            <div className="space-y-2 opacity-75">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-1">
                Completed ({purchasedItems.length})
              </h3>
              <div className="bg-slate-900/40 border border-slate-800/60 rounded-2xl divide-y divide-slate-800/60">
                {purchasedItems.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 flex items-center justify-between hover:bg-slate-800/20 transition-colors"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <button
                        onClick={() => handleTogglePurchased(item)}
                        className="text-emerald-400 shrink-0"
                        title="Mark uncompleted"
                      >
                        <CheckCircle2 className="w-5 h-5" />
                      </button>

                      <span className="text-sm line-through text-slate-500 capitalize truncate">
                        {item.name}
                      </span>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0 ml-3">
                      <span className="text-xs text-slate-500 line-through">
                        {item.quantity} {item.unit}
                      </span>

                      <button
                        onClick={() => handleDeleteItem(item.id)}
                        className="text-slate-600 hover:text-rose-400 p-1 transition-colors"
                        title="Delete item"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
