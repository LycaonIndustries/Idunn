import React, { useState, useRef } from 'react'
import {
  Upload,
  Receipt as ReceiptIcon,
  X,
  Check,
  Trash2,
  Loader2,
  Calendar,
  MapPin,
  Sparkles,
} from 'lucide-react'
import type { Receipt, ReceiptItemCandidate } from '../types'
import { confirmReceiptItems, ingestReceiptImage } from '../api'

interface ReceiptScannerModalProps {
  /** Flag controlling modal visibility. */
  isOpen: boolean
  /** Callback to close the modal. */
  onClose: () => void
  /** Callback invoked when candidate items are confirmed into inventory. */
  onConfirmed: () => void
}

const COMMON_STORES = [
  'Blinkit',
  'Zepto',
  'Instamart',
  'BigBasket',
  'Kirana Store',
  'Other',
]

const LOCATIONS = ['fridge', 'pantry', 'freezer', 'spice_box', 'cabinet', 'counter']
const UNITS = ['g', 'kg', 'ml', 'l', 'piece', 'packet', 'bunch', 'katori', 'chamcha', 'paav']

/**
 * ReceiptScannerModal provides receipt upload and candidate verification.
 *
 * @param props - Visibility and completion callback props.
 * @returns Rendered modal dialog element.
 */
export const ReceiptScannerModal: React.FC<ReceiptScannerModalProps> = ({
  isOpen,
  onClose,
  onConfirmed,
}) => {
  // File input reference triggers native browser file selection.
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Track upload and parsing state.
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [storeHint, setStoreHint] = useState<string>('Blinkit')
  const [analyzing, setAnalyzing] = useState<boolean>(false)
  const [confirming, setConfirming] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Parsed receipt candidates ready for user verification.
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [candidates, setCandidates] = useState<ReceiptItemCandidate[]>([])

  // Return early when modal is closed to preserve DOM lightweight state.
  if (!isOpen) return null

  /**
   * Handle user file selection from file input.
   *
   * @param e - Input change event.
   */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Select first image file to initialize preview.
    const file = e.target.files?.[0]
    if (!file) return

    setSelectedFile(file)
    setError(null)

    // Generate local data URL to display immediate visual thumbnail.
    const reader = new FileReader()
    reader.onload = () => {
      setImagePreview(reader.result as string)
    }
    reader.readAsDataURL(file)
  }

  /**
   * Submit selected image file to backend receipt extraction service.
   */
  const handleAnalyzeReceipt = async () => {
    // Prevent network request when user has not chosen an image.
    if (!selectedFile) {
      setError('Please select or drop a receipt image first.')
      return
    }

    setAnalyzing(true)
    setError(null)

    try {
      // Send image binary to multimodal receipt parser.
      const parsedReceipt = await ingestReceiptImage(selectedFile, storeHint)
      setReceipt(parsedReceipt)
      setCandidates(parsedReceipt.items || [])
    } catch (err: unknown) {
      // Display user-friendly error if LLM parsing or API call fails.
      setError(err instanceof Error ? err.message : 'Receipt extraction failed.')
    } finally {
      setAnalyzing(false)
    }
  }

  /**
   * Update candidate item field dynamically.
   *
   * @param index - Index in candidates list.
   * @param field - Field name to update.
   * @param value - New field value.
   */
  const handleCandidateChange = (
    index: number,
    field: keyof ReceiptItemCandidate,
    value: string | number,
  ) => {
    // Update candidate in local state to allow manual corrections before saving.
    setCandidates((prev) => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  /**
   * Remove unwanted or non-grocery item candidate.
   *
   * @param index - Index of item to delete.
   */
  const handleRemoveCandidate = (index: number) => {
    // Filter out item candidate to exclude accidental items.
    setCandidates((prev) => prev.filter((_, i) => i !== index))
  }

  /**
   * Commit verified items into pantry stock.
   */
  const handleConfirmItems = async () => {
    // Prevent saving when no candidate items remain.
    if (!receipt || candidates.length === 0) {
      setError('No items to confirm.')
      return
    }

    setConfirming(true)
    setError(null)

    try {
      // Send verified candidate list to create persistent inventory items.
      await confirmReceiptItems({
        receipt_id: receipt._id,
        store_name: storeHint || receipt.store_name,
        items: candidates,
      })

      // Notify parent view to reload pantry and close dialog.
      onConfirmed()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to confirm items to pantry.')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in">
      <div className="bg-slate-900 rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-800">
        {/* Header section with title and close button. */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <ReceiptIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Scan Receipt or Bill</h2>
              <p className="text-xs text-slate-400">
                Extract items from Blinkit, Zepto, Instamart, or Kirana store bills
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Display alert banner when errors occur. */}
        {error && (
          <div className="mb-4 text-xs text-red-400 bg-red-950/40 p-3 rounded-xl border border-red-800/80">
            {error}
          </div>
        )}

        {/* Scrollable dialog body. */}
        <div className="overflow-y-auto flex-1 pr-1 space-y-5">
          {!receipt ? (
            /* Upload step: Choose store platform and upload bill screenshot. */
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-2">
                  Store or Quick Commerce App
                </label>
                <div className="flex flex-wrap gap-2">
                  {COMMON_STORES.map((store) => (
                    <button
                      key={store}
                      type="button"
                      onClick={() => setStoreHint(store)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-colors cursor-pointer ${
                        storeHint === store
                          ? 'bg-emerald-500 text-white shadow-sm'
                          : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      {store}
                    </button>
                  ))}
                </div>
              </div>

              {/* Drag and drop upload zone. */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 hover:border-emerald-500 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-slate-950/50"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {imagePreview ? (
                  <div className="flex flex-col items-center space-y-2">
                    <img
                      src={imagePreview}
                      alt="Receipt preview"
                      className="max-h-48 rounded-xl object-contain border border-slate-800"
                    />
                    <p className="text-xs text-slate-400">{selectedFile?.name}</p>
                    <span className="text-xs text-emerald-400 font-medium">Click to replace image</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-2 py-4">
                    <div className="p-3 rounded-full bg-slate-800 text-slate-400">
                      <Upload className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-medium text-slate-200">
                      Click to upload receipt or screenshot
                    </p>
                    <p className="text-xs text-slate-500">Supports JPEG, PNG, WEBP order screenshots</p>
                  </div>
                )}
              </div>

              {/* Action button to trigger multimodal OCR extraction. */}
              <button
                type="button"
                onClick={handleAnalyzeReceipt}
                disabled={!selectedFile || analyzing}
                className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-lg shadow-emerald-600/20"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Extracting Grocery Items...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Extract Items with OCR</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            /* Review step: Display extracted grocery candidate list with shelf-life projections. */
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>
                  Found <strong className="text-slate-200">{candidates.length}</strong> items from{' '}
                  <strong className="text-emerald-400">{receipt.store_name}</strong>
                </span>
                <button
                  onClick={() => {
                    setReceipt(null)
                    setSelectedFile(null)
                    setImagePreview(null)
                  }}
                  className="text-xs text-slate-400 hover:text-slate-200 underline cursor-pointer"
                >
                  Upload different receipt
                </button>
              </div>

              {/* Render item cards for confirmation. */}
              <div className="space-y-2.5">
                {candidates.map((cand, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="flex-1 space-y-2">
                      <input
                        type="text"
                        value={cand.name}
                        onChange={(e) => handleCandidateChange(idx, 'name', e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-sm font-semibold text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />

                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        {/* Numerical quantity input. */}
                        <div className="flex items-center space-x-1">
                          <span className="text-slate-500">Qty:</span>
                          <input
                            type="number"
                            step="any"
                            value={cand.quantity}
                            onChange={(e) =>
                              handleCandidateChange(idx, 'quantity', parseFloat(e.target.value) || 1)
                            }
                            className="w-16 bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 text-xs text-slate-200"
                          />
                        </div>

                        {/* Standardized kitchen unit selector. */}
                        <select
                          value={cand.unit}
                          onChange={(e) => handleCandidateChange(idx, 'unit', e.target.value)}
                          className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 text-xs text-slate-300"
                        >
                          {UNITS.map((u) => (
                            <option key={u} value={u}>
                              {u}
                            </option>
                          ))}
                        </select>

                        {/* Kitchen storage location selector. */}
                        <div className="flex items-center space-x-1">
                          <MapPin className="w-3 h-3 text-slate-500" />
                          <select
                            value={cand.suggested_location}
                            onChange={(e) =>
                              handleCandidateChange(idx, 'suggested_location', e.target.value)
                            }
                            className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-0.5 text-xs text-slate-300"
                          >
                            {LOCATIONS.map((loc) => (
                              <option key={loc} value={loc}>
                                {loc}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* FEFO projected shelf life indicator. */}
                        <div className="flex items-center space-x-1 text-amber-400 bg-amber-950/30 px-2 py-0.5 rounded-md border border-amber-800/40">
                          <Calendar className="w-3 h-3" />
                          <span>~{cand.estimated_shelf_life_days}d shelf life</span>
                        </div>
                      </div>
                    </div>

                    {/* Delete button removes false detection from receipt. */}
                    <button
                      type="button"
                      onClick={() => handleRemoveCandidate(idx)}
                      title="Remove item"
                      className="self-end sm:self-center p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-900 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Confirm button batch-inserts all items into active pantry. */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleConfirmItems}
                  disabled={confirming || candidates.length === 0}
                  className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-lg shadow-emerald-600/20"
                >
                  {confirming ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Adding to Pantry...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Confirm {candidates.length} Items to Pantry</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
