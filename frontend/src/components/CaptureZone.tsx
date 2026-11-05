/**
 * Multimodal recipe ingestion component for Iðunn Kitchen OS.
 * Supports five capture channels: Photos/Cookbooks, Voice Notes, Silent Video Reels, URLs, and Pasted Text.
 */

import React, { useState, useRef } from 'react'
import {
  Image as ImageIcon,
  Mic,
  Video,
  Globe,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Plus,
  Clock,
  Users,
  Settings as SettingsIcon,
} from 'lucide-react'
import type { Recipe } from '../types'
import { ingestUrl, ingestText, ingestImage, ingestAudio, ingestVideo, createRecipe } from '../api'

/**
 * Properties for CaptureZone component.
 */
interface CaptureZoneProps {
  /** Callback invoked when a recipe is confirmed and saved to the vault. */
  onRecipeSaved: (recipe: Recipe) => void
  /** Navigation callback to open the settings view. */
  onNavigateToSettings?: () => void
  /** Whether the user has at least one AI provider key configured. */
  isByokConfigured?: boolean
}

/**
 * Universal recipe capture zone with tabbed stream selectors and live preview.
 *
 * @param props - Component properties.
 * @returns CaptureZone JSX element.
 */
export const CaptureZone: React.FC<CaptureZoneProps> = ({
  onRecipeSaved,
  onNavigateToSettings,
  isByokConfigured = true,
}) => {
  // Track active input channel. Defaults to 'image' for cookbook/screenshot scanning.
  const [stream, setStream] = useState<'image' | 'audio' | 'video' | 'url' | 'text'>('image')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Maintain separate states for each stream type to preserve user draft inputs across tab switches.
  const [urlInput, setUrlInput] = useState('')
  const [textInput, setTextInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Hold extracted recipe model for pre-commit review before vault persistence.
  const [preview, setPreview] = useState<Recipe | null>(null)
  const [saving, setSaving] = useState(false)

  // Hidden native file input reference to trigger OS file selection dialogs cleanly.
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Capture file selections and clear past error states.
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
      setError(null)
    }
  }

  // Dispatch current stream input to corresponding backend extraction endpoint.
  const handleExtract = async () => {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)

    try {
      let extracted: Recipe | null = null

      // Route by active stream mode. Validate required inputs before calling network client.
      if (stream === 'url') {
        if (!urlInput.trim()) throw new Error('Please enter a recipe URL')
        extracted = await ingestUrl(urlInput.trim())
      } else if (stream === 'text') {
        if (!textInput.trim()) throw new Error('Please paste recipe text or notes')
        extracted = await ingestText(textInput.trim())
      } else if (stream === 'image') {
        if (!selectedFile) throw new Error('Please select an image file')
        extracted = await ingestImage(selectedFile)
      } else if (stream === 'audio') {
        if (!selectedFile) throw new Error('Please select an audio file (.mp3, .m4a, .wav)')
        extracted = await ingestAudio(selectedFile)
      } else if (stream === 'video') {
        if (!selectedFile) throw new Error('Please select a video reel (.mp4, .mov)')
        extracted = await ingestVideo(selectedFile)
      }

      // Populate preview card so user can verify ingredients and steps before saving.
      if (extracted) {
        setPreview(extracted)
        setSuccessMsg('Recipe successfully extracted! Review below and save to your vault.')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Extraction failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // Commit reviewed recipe to vault and notify parent container.
  const handleSaveToVault = async () => {
    if (!preview) return
    setSaving(true)
    setError(null)
    try {
      // Ingest endpoints already persist records to the database.
      // Call createRecipe only if ID is missing from manual construction.
      const saved = preview.id || preview._id ? preview : await createRecipe(preview)
      setSuccessMsg(`"${saved.title}" saved to your vault!`)
      setPreview(null)
      setSelectedFile(null)
      setUrlInput('')
      setTextInput('')
      onRecipeSaved(saved)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save recipe'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Header section explaining multimodal capabilities */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight sm:text-4xl">
          Universal Recipe Ingestion
        </h1>
        <p className="mt-2 text-base text-slate-400 max-w-2xl mx-auto">
          Capture recipes from any source — cookbook photos, Instagram/TikTok reels, voice notes,
          WhatsApp messages, or blog URLs.
        </p>
      </div>

      {/* Prominent warning banner when user has not entered BYOK keys */}
      {!isByokConfigured && onNavigateToSettings && (
        <div className="mb-6 p-4 rounded-2xl bg-amber-950/40 border border-amber-800/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-center space-x-3">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
            <p className="text-xs sm:text-sm text-amber-200">
              <strong>BYOK Key Needed:</strong> Add a free Google Gemini key in Settings to extract
              recipes from reels, photos, and voice notes.
            </p>
          </div>
          <button
            onClick={onNavigateToSettings}
            className="px-3.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs flex items-center space-x-1.5 flex-shrink-0 transition-colors"
          >
            <SettingsIcon className="w-3.5 h-3.5" />
            <span>Configure BYOK</span>
          </button>
        </div>
      )}

      {/* Five-channel stream selector tabs */}
      <div className="bg-slate-900/90 rounded-2xl shadow-sm border border-slate-800 p-2 mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {/* Photo / Cookbook Stream */}
          <button
            onClick={() => {
              setStream('image')
              setSelectedFile(null)
              setError(null)
            }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              stream === 'image'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            <span>Photo / Book</span>
          </button>

          {/* Voice Note Audio Stream */}
          <button
            onClick={() => {
              setStream('audio')
              setSelectedFile(null)
              setError(null)
            }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              stream === 'audio'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <Mic className="w-4 h-4" />
            <span>Voice Note</span>
          </button>

          {/* Silent Video Reel Stream */}
          <button
            onClick={() => {
              setStream('video')
              setSelectedFile(null)
              setError(null)
            }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              stream === 'video'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <Video className="w-4 h-4" />
            <span>Reel (1 fps)</span>
          </button>

          {/* Web / YouTube URL Stream */}
          <button
            onClick={() => {
              setStream('url')
              setError(null)
            }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              stream === 'url'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Recipe URL</span>
          </button>

          {/* Raw Text Stream */}
          <button
            onClick={() => {
              setStream('text')
              setError(null)
            }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              stream === 'text'
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40 shadow-sm'
                : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Pasted Text</span>
          </button>
        </div>
      </div>

      {/* Dynamic input card adapting to chosen stream */}
      <div className="bg-slate-900/90 rounded-2xl shadow-sm border border-slate-800 p-6 mb-8">
        {stream === 'image' && (
          <div>
            <div className="text-sm font-medium text-slate-300 mb-2">
              Upload Cookbook Photo or Recipe Screenshot
            </div>
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              aria-label="Upload cookbook photo or recipe screenshot"
              className="border-2 border-dashed border-slate-800 hover:border-orange-500/60 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-950/60 hover:bg-orange-950/10"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-200">
                {selectedFile
                  ? selectedFile.name
                  : 'Click to select or drop cookbook photo / screenshot'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Supports JPEG, PNG, WebP up to 10 MB</p>
            </div>
          </div>
        )}

        {stream === 'audio' && (
          <div>
            <div className="text-sm font-medium text-slate-300 mb-2">
              Upload Voice Note or Spoken Recipe Audio
            </div>
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              aria-label="Upload voice note or spoken recipe audio"
              className="border-2 border-dashed border-slate-800 hover:border-orange-500/60 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-950/60 hover:bg-orange-950/10"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center mx-auto mb-3">
                <Mic className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-200">
                {selectedFile ? selectedFile.name : 'Click to select audio recording'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supports MP3, M4A, WAV, OGG, WebM up to 50 MB
              </p>
            </div>
          </div>
        )}

        {stream === 'video' && (
          <div>
            <div className="text-sm font-medium text-slate-300 mb-2">
              Upload Silent Cooking Reel or Short Video
            </div>
            <div
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  fileInputRef.current?.click()
                }
              }}
              aria-label="Upload cooking video reel"
              className="border-2 border-dashed border-slate-800 hover:border-orange-500/60 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-950/60 hover:bg-orange-950/10"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center mx-auto mb-3">
                <Video className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-200">
                {selectedFile ? selectedFile.name : 'Click to select cooking video clip'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Samples 1 frame/sec (up to 15 keyframes) + multimodal OCR. Supports MP4, MOV, WebM up
                to 100 MB.
              </p>
            </div>
          </div>
        )}

        {stream === 'url' && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">Recipe URL</label>
            <input
              type="url"
              placeholder="https://hebbarskitchen.com/palak-paneer-recipe/ or YouTube link"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
            />
          </div>
        )}

        {stream === 'text' && (
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Pasted Recipe or WhatsApp Forward
            </label>
            <textarea
              rows={6}
              placeholder="Paste recipe ingredients, method, or WhatsApp message from your family..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
            />
          </div>
        )}

        {/* Action Button & Status Banners */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex-1">
            {error && (
              <div className="flex items-center space-x-2 text-sm text-red-400 bg-red-950/40 p-3 rounded-xl border border-red-800/80">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {successMsg && (
              <div className="flex items-center space-x-2 text-sm text-emerald-300 bg-emerald-950/40 p-3 rounded-xl border border-emerald-800/80">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}
          </div>

          <button
            onClick={handleExtract}
            disabled={loading}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-semibold text-sm flex items-center justify-center space-x-2 shadow-lg shadow-orange-500/20 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing Multimodal Ingest...</span>
              </>
            ) : (
              <>
                <span>Extract Recipe</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Extracted Recipe Preview */}
      {preview && (
        <div className="bg-slate-900/90 rounded-2xl shadow-sm border border-slate-800 p-6 sm:p-8 animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-4 mb-6 gap-4">
            <div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-orange-500/20 text-orange-400 border border-orange-500/30 uppercase tracking-wider">
                Extracted Preview
              </span>
              <h2 className="text-2xl font-bold text-slate-100 mt-2">{preview.title}</h2>
              {preview.description && (
                <p className="text-sm text-slate-400 mt-1">{preview.description}</p>
              )}
            </div>

            <button
              onClick={handleSaveToVault}
              disabled={saving}
              className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm flex items-center justify-center space-x-2 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  <span>Save to Recipe Vault</span>
                </>
              )}
            </button>
          </div>

          {/* Quick stats: prep time, cook time, portions */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl flex items-center space-x-3">
              <Clock className="w-5 h-5 text-orange-400" />
              <div>
                <p className="text-xs text-slate-500">Prep Time</p>
                <p className="text-sm font-semibold text-slate-200">
                  {preview.prep_time_minutes || 0} mins
                </p>
              </div>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl flex items-center space-x-3">
              <Clock className="w-5 h-5 text-orange-400" />
              <div>
                <p className="text-xs text-slate-500">Cook Time</p>
                <p className="text-sm font-semibold text-slate-200">
                  {preview.cook_time_minutes || 0} mins
                </p>
              </div>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl flex items-center space-x-3">
              <Users className="w-5 h-5 text-orange-400" />
              <div>
                <p className="text-xs text-slate-500">Servings</p>
                <p className="text-sm font-semibold text-slate-200">{preview.servings || 2}</p>
              </div>
            </div>
          </div>

          {/* Two-column layout: Ingredients and Instructions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Ingredients column */}
            <div>
              <h3 className="font-semibold text-slate-200 text-base mb-3 flex items-center justify-between">
                <span>Ingredients</span>
                <span className="text-xs text-slate-500">{preview.ingredients.length} items</span>
              </h3>
              <ul className="divide-y divide-slate-800/60 bg-slate-950/60 rounded-xl p-3 border border-slate-800">
                {preview.ingredients.map((ing, i) => (
                  <li key={i} className="py-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-200">{ing.name}</span>
                    <span className="text-slate-400 font-mono text-xs bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                      {ing.quantity ? `${ing.quantity} ` : ''}
                      {ing.unit || ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Steps column */}
            <div>
              <h3 className="font-semibold text-slate-200 text-base mb-3 flex items-center justify-between">
                <span>Steps</span>
                <span className="text-xs text-slate-500">{preview.steps.length} steps</span>
              </h3>
              <ol className="space-y-3">
                {preview.steps.map((st, i) => (
                  <li key={i} className="flex space-x-3 text-sm">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-semibold text-xs flex items-center justify-center">
                      {st.step_number || i + 1}
                    </span>
                    <span className="text-slate-300 leading-relaxed">{st.instruction}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CaptureZone
