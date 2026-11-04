import React, { useState } from 'react'
import {
  Package,
  Plus,
  Trash2,
  Calendar,
  MapPin,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import type { InventoryCreate, InventoryItem } from '../types'
import { createInventoryItem, deleteInventoryItem } from '../api'

interface PantryViewProps {
  items: InventoryItem[]
  loading: boolean
  onRefresh: () => void
  onItemAdded: (item: InventoryItem) => void
  onItemDeleted: (id: string) => void
}

const LOCATIONS = ['fridge', 'pantry', 'freezer', 'cabinet', 'spice_box', 'counter']
const UNITS = ['g', 'kg', 'paav', 'ml', 'l', 'tsp', 'tbsp', 'chamcha', 'katori', 'piece', 'bunch', 'packet']

export const PantryView: React.FC<PantryViewProps> = ({
  items,
  loading,
  onRefresh,
  onItemAdded,
  onItemDeleted,
}) => {
  const [showAddModal, setShowAddModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form State
  const [name, setName] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [unit, setUnit] = useState('piece')
  const [location, setLocation] = useState('fridge')
  const [expiryDate, setExpiryDate] = useState('')

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    setSubmitting(true)
    setError(null)
    try {
      const payload: InventoryCreate = {
        name: name.trim(),
        quantity: parseFloat(quantity) || 1,
        unit,
        location,
        expiry_date: expiryDate ? new Date(expiryDate).toISOString() : null,
      }
      const newItem = await createInventoryItem(payload)
      onItemAdded(newItem)
      setName('')
      setQuantity('1')
      setExpiryDate('')
      setShowAddModal(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to add item')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string, itemName: string) => {
    if (window.confirm(`Remove "${itemName}" from pantry?`)) {
      try {
        await deleteInventoryItem(id)
        onItemDeleted(id)
      } catch (err: unknown) {
        alert(err instanceof Error ? err.message : 'Failed to delete')
      }
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Kitchen Pantry</h1>
          <p className="mt-1 text-sm text-slate-500">
            {items.length} items tracked across your fridge, freezer, and pantry
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={onRefresh}
            title="Refresh pantry"
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2.5 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-medium text-sm flex items-center space-x-2 shadow-sm transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Item</span>
          </button>
        </div>
      </div>

      {/* Add Item Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Add Pantry Item</h3>

            {error && (
              <div className="mb-4 text-xs text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
                {error}
              </div>
            )}

            <form onSubmit={handleAddItem} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Item Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Paneer, Onions, Toor Dal"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Quantity</label>
                  <input
                    type="number"
                    step="any"
                    required
                    min="0.1"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Unit</label>
                  <select
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
                  >
                    {UNITS.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Location</label>
                  <select
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
                  >
                    {LOCATIONS.map((loc) => (
                      <option key={loc} value={loc}>{loc.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Expiry Date (optional)</label>
                  <input
                    type="date"
                    value={expiryDate}
                    onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-semibold text-white bg-orange-500 hover:bg-orange-600 rounded-lg shadow-sm transition-all flex items-center space-x-1"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Item</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Items Grid */}
      {items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow"
            >
              <div>
                <div className="flex items-start justify-between">
                  <h4 className="font-bold text-slate-900 text-base">{item.name}</h4>
                  <button
                    onClick={() => handleDelete(item.id, item.name)}
                    className="text-slate-400 hover:text-red-500 p-1 rounded hover:bg-slate-50 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="mt-2 flex items-center space-x-2">
                  <span className="text-xl font-extrabold text-orange-600 font-mono">
                    {item.quantity}
                  </span>
                  <span className="text-xs font-semibold text-slate-500 uppercase">
                    {item.unit}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  <span className="capitalize">{item.location.replace('_', ' ')}</span>
                </div>

                {item.expiry_date && (
                  <div className="flex items-center space-x-1 text-slate-600">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>{new Date(item.expiry_date).toLocaleDateString()}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-300 p-8">
          <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center mx-auto mb-3">
            <Package className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">Your pantry is empty</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            Add items manually or use receipt OCR to automatically log groceries from Blinkit, Zepto, or store bills.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="mt-4 px-4 py-2 rounded-xl bg-orange-500 hover:bg-orange-600 text-white font-medium text-xs shadow-sm transition-all"
          >
            Add Your First Item
          </button>
        </div>
      )}
    </div>
  )
}
