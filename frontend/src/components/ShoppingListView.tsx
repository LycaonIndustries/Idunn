import { useEffect, useState } from 'react'
import {
  clearPurchasedShoppingItems,
  createShoppingItem,
  deleteShoppingItem,
  exportShoppingListWhatsApp,
  fetchShoppingList,
  updateShoppingItem,
} from '../api'
import type { ShoppingListItem } from '../types'

const QC_PLATFORMS = [
  { key: 'blinkit', label: 'Blinkit', bg: 'bg-yellow-100 hover:bg-yellow-200 text-yellow-800' },
  { key: 'zepto', label: 'Zepto', bg: 'bg-purple-100 hover:bg-purple-200 text-purple-800' },
  { key: 'instamart', label: 'Instamart', bg: 'bg-orange-100 hover:bg-orange-200 text-orange-800' },
] as const

export function ShoppingListView() {
  const [items, setItems] = useState<ShoppingListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [unit, setUnit] = useState('piece')

  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        const data = await fetchShoppingList()
        if (!cancelled) {
          setItems(data)
          setError(null)
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || 'Failed to load shopping list')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void init()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleAddItem(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    try {
      const created = await createShoppingItem({
        name: name.trim(),
        quantity: parseFloat(quantity) || 1,
        unit: unit.trim() || 'piece',
      })
      setItems((prev) => [created, ...prev])
      setName('')
      setQuantity('1')
      setUnit('piece')
    } catch (err: any) {
      setError(err.message || 'Failed to add item')
    }
  }

  async function handleToggleChecked(item: ShoppingListItem) {
    try {
      const updated = await updateShoppingItem(item._id, { checked: !item.checked })
      setItems((prev) => prev.map((x) => (x._id === item._id ? updated : x)))
    } catch (err: any) {
      setError(err.message || 'Failed to update item')
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteShoppingItem(id)
      setItems((prev) => prev.filter((x) => x._id !== id))
    } catch (err: any) {
      setError(err.message || 'Failed to delete item')
    }
  }

  async function handleClearPurchased() {
    try {
      await clearPurchasedShoppingItems()
      setItems((prev) => prev.filter((x) => !x.checked))
    } catch (err: any) {
      setError(err.message || 'Failed to clear purchased items')
    }
  }

  async function handleShareWhatsApp() {
    try {
      const exportData = await exportShoppingListWhatsApp()
      if (typeof navigator !== 'undefined' && navigator.share) {
        try {
          await navigator.share({
            title: 'Iðunn Grocery List',
            text: exportData.text,
          })
          return
        } catch {
          // Fall through to browser URL launch.
        }
      }
      window.open(exportData.whatsapp_url, '_blank')
    } catch (err: any) {
      setError(err.message || 'Failed to export to WhatsApp')
    }
  }

  const uncheckedItems = items.filter((x) => !x.checked)
  const checkedItems = items.filter((x) => x.checked)

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Shopping List</h1>
          <p className="text-sm text-gray-500">
            Track ingredients to buy and 1-click order via Quick-Commerce.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {items.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => void handleShareWhatsApp()}
                className="px-3 py-1.5 text-xs font-semibold rounded-md bg-emerald-600 hover:bg-emerald-500 text-white transition flex items-center gap-1.5 cursor-pointer"
                title="Share formatted list via WhatsApp"
              >
                <span>WhatsApp</span>
              </button>
              <button
                type="button"
                onClick={() => window.print()}
                className="px-3 py-1.5 text-xs font-semibold rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1.5 cursor-pointer"
                title="Print refrigerator summary"
              >
                <span>Print</span>
              </button>
            </>
          )}
          {checkedItems.length > 0 && (
            <button
              onClick={() => void handleClearPurchased()}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 transition"
            >
              Clear Purchased ({checkedItems.length})
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      {/* Inline Add Item Form */}
      <form onSubmit={(e) => void handleAddItem(e)} className="flex gap-2 items-center">
        <input
          type="text"
          placeholder="Ingredient name (e.g. Greek yogurt)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          required
        />
        <input
          type="number"
          step="any"
          min="0.1"
          placeholder="Qty"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-20 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        />
        <input
          type="text"
          placeholder="Unit"
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          className="w-24 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-md text-sm transition"
        >
          Add Item
        </button>
      </form>

      {/* Loading & Empty States */}
      {loading && items.length === 0 ? (
        <div className="text-center py-12 text-gray-400">Loading shopping list...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 border border-dashed rounded-lg">
          <p className="text-gray-500 font-medium">Your shopping list is empty.</p>
          <p className="text-xs text-gray-400 mt-1">
            Add items manually or click &quot;Add Missing to Shopping List&quot; on any recipe.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white border rounded-lg divide-y">
            {uncheckedItems.map((item) => (
              <div key={item._id} className="p-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={item.checked}
                    onChange={() => void handleToggleChecked(item)}
                    className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500 cursor-pointer"
                  />
                  <div>
                    <span className="text-sm font-medium text-gray-900">{item.name}</span>
                    <span className="text-xs text-gray-500 ml-2">
                      ({item.quantity} {item.unit})
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {QC_PLATFORMS.map(({ key, label, bg }) =>
                    item.quick_links?.[key] ? (
                      <a
                        key={key}
                        href={item.quick_links[key]}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`px-2 py-1 text-xs font-semibold rounded ${bg} transition`}
                      >
                        {label}
                      </a>
                    ) : null
                  )}
                  <button
                    onClick={() => void handleDelete(item._id)}
                    className="text-gray-400 hover:text-red-500 text-xs px-2 py-1 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {checkedItems.length > 0 && (
            <div className="pt-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Purchased ({checkedItems.length})
              </h3>
              <div className="bg-gray-50 border rounded-lg divide-y opacity-75">
                {checkedItems.map((item) => (
                  <div key={item._id} className="p-3 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={item.checked}
                        onChange={() => void handleToggleChecked(item)}
                        className="h-4 w-4 rounded border-gray-300 text-amber-600 cursor-pointer"
                      />
                      <span className="text-sm line-through text-gray-400">
                        {item.name} ({item.quantity} {item.unit})
                      </span>
                    </div>
                    <button
                      onClick={() => void handleDelete(item._id)}
                      className="text-gray-400 hover:text-red-500 text-xs px-2 py-1 transition"
                    >
                      Delete
                    </button>
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
