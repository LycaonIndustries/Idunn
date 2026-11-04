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
} from 'lucide-react'
import type { Recipe } from '../types'
import { ingestUrl, ingestText, ingestImage, ingestAudio, ingestVideo, createRecipe } from '../api'

interface CaptureZoneProps {
  onRecipeSaved: (recipe: Recipe) => void
}

export const CaptureZone: React.FC<CaptureZoneProps> = ({ onRecipeSaved }) => {
  const [stream, setStream] = useState<'image' | 'audio' | 'video' | 'url' | 'text'>('image')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Stream inputs
  const [urlInput, setUrlInput] = useState('')
  const [textInput, setTextInput] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Extracted preview
  const [preview, setPreview] = useState<Recipe | null>(null)
  const [saving, setSaving] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0])
      setError(null)
    }
  }

  const handleExtract = async () => {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)

    try {
      let extracted: Recipe | null = null

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

  const handleSaveToVault = async () => {
    if (!preview) return
    setSaving(true)
    setError(null)
    try {
      const saved = await createRecipe(preview)
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
      {/* Title */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
          Universal Recipe Ingestion
        </h1>
        <p className="mt-2 text-base text-slate-600 max-w-2xl mx-auto">
          Capture recipes from any source — cookbook photos, Instagram/TikTok reels, voice notes, WhatsApp messages, or blog URLs.
        </p>
      </div>

      {/* Stream Tabs */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-2 mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <button
            onClick={() => { setStream('image'); setSelectedFile(null); setError(null); }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              stream === 'image'
                ? 'bg-orange-50 text-orange-600 border border-orange-200 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            <span>Photo / Book</span>
          </button>

          <button
            onClick={() => { setStream('audio'); setSelectedFile(null); setError(null); }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              stream === 'audio'
                ? 'bg-orange-50 text-orange-600 border border-orange-200 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Mic className="w-4 h-4" />
            <span>Voice Note</span>
          </button>

          <button
            onClick={() => { setStream('video'); setSelectedFile(null); setError(null); }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              stream === 'video'
                ? 'bg-orange-50 text-orange-600 border border-orange-200 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Video className="w-4 h-4" />
            <span>Reel (1 fps)</span>
          </button>

          <button
            onClick={() => { setStream('url'); setError(null); }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              stream === 'url'
                ? 'bg-orange-50 text-orange-600 border border-orange-200 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Globe className="w-4 h-4" />
            <span>Recipe URL</span>
          </button>

          <button
            onClick={() => { setStream('text'); setError(null); }}
            className={`flex items-center justify-center space-x-2 py-3 px-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              stream === 'text'
                ? 'bg-orange-50 text-orange-600 border border-orange-200 shadow-sm'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Pasted Text</span>
          </button>
        </div>
      </div>

      {/* Input Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-8">
        {stream === 'image' && (
          <div>
            <div className="text-sm font-medium text-slate-700 mb-2">Upload Cookbook Photo or Recipe Screenshot</div>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-orange-400 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50 hover:bg-orange-50/20"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center mx-auto mb-3">
                <Upload className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {selectedFile ? selectedFile.name : 'Click to select or drop cookbook photo / screenshot'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Supports JPEG, PNG, WebP up to 10 MB</p>
            </div>
          </div>
        )}

        {stream === 'audio' && (
          <div>
            <div className="text-sm font-medium text-slate-700 mb-2">Upload Voice Note or Spoken Recipe Audio</div>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-orange-400 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50 hover:bg-orange-50/20"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center mx-auto mb-3">
                <Mic className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {selectedFile ? selectedFile.name : 'Click to select audio recording'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Supports MP3, M4A, WAV, OGG, WebM up to 50 MB</p>
            </div>
          </div>
        )}

        {stream === 'video' && (
          <div>
            <div className="text-sm font-medium text-slate-700 mb-2">Upload Silent Cooking Reel or Short Video</div>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 hover:border-orange-400 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50 hover:bg-orange-50/20"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center mx-auto mb-3">
                <Video className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {selectedFile ? selectedFile.name : 'Click to select cooking video clip'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Samples 1 frame/sec (up to 15 keyframes) + multimodal OCR. Supports MP4, MOV, WebM up to 100 MB.
              </p>
            </div>
          </div>
        )}

        {stream === 'url' && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Recipe URL</label>
            <input
              type="url"
              placeholder="https://hebbarskitchen.com/palak-paneer-recipe/ or YouTube link"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
            />
          </div>
        )}

        {stream === 'text' && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Pasted Recipe or WhatsApp Forward</label>
            <textarea
              rows={6}
              placeholder="Paste recipe ingredients, method, or WhatsApp message from your family..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm"
            />
          </div>
        )}

        {/* Action Button & Messages */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex-1">
            {error && (
              <div className="flex items-center space-x-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {successMsg && (
              <div className="flex items-center space-x-2 text-sm text-emerald-700 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}
          </div>

          <button
            onClick={handleExtract}
            disabled={loading}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-medium text-sm flex items-center justify-center space-x-2 shadow-sm shadow-orange-500/20 transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing AI Multimodal Ingest...</span>
              </>
            ) : (
              <>
                <span>Extract Recipe</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Extracted Preview */}
      {preview && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-4 mb-6 gap-4">
            <div>
              <span className="text-xs font-semibold px-2 py-1 rounded-md bg-orange-100 text-orange-700 uppercase tracking-wider">
                Extracted Preview
              </span>
              <h2 className="text-2xl font-bold text-slate-900 mt-2">{preview.title}</h2>
              {preview.description && (
                <p className="text-sm text-slate-500 mt-1">{preview.description}</p>
              )}
            </div>

            <button
              onClick={handleSaveToVault}
              disabled={saving}
              className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm flex items-center justify-center space-x-2 shadow-sm transition-all"
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

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-50 p-3 rounded-xl flex items-center space-x-3">
              <Clock className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-xs text-slate-500">Prep Time</p>
                <p className="text-sm font-semibold text-slate-800">{preview.prep_time_minutes || 0} mins</p>
              </div>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl flex items-center space-x-3">
              <Clock className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-xs text-slate-500">Cook Time</p>
                <p className="text-sm font-semibold text-slate-800">{preview.cook_time_minutes || 0} mins</p>
              </div>
            </div>
            <div className="bg-slate-50 p-3 rounded-xl flex items-center space-x-3">
              <Users className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-xs text-slate-500">Servings</p>
                <p className="text-sm font-semibold text-slate-800">{preview.servings || 2}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Ingredients */}
            <div>
              <h3 className="font-semibold text-slate-900 text-base mb-3 flex items-center justify-between">
                <span>Ingredients</span>
                <span className="text-xs text-slate-500">{preview.ingredients.length} items</span>
              </h3>
              <ul className="divide-y divide-slate-100 bg-slate-50/50 rounded-xl p-3 border border-slate-100">
                {preview.ingredients.map((ing, i) => (
                  <li key={i} className="py-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-800">{ing.name}</span>
                    <span className="text-slate-500 font-mono text-xs bg-slate-100 px-2 py-0.5 rounded">
                      {ing.quantity ? `${ing.quantity} ` : ''}{ing.unit || ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Steps */}
            <div>
              <h3 className="font-semibold text-slate-900 text-base mb-3 flex items-center justify-between">
                <span>Steps</span>
                <span className="text-xs text-slate-500">{preview.steps.length} steps</span>
              </h3>
              <ol className="space-y-3">
                {preview.steps.map((st, i) => (
                  <li key={i} className="flex space-x-3 text-sm">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-100 text-orange-700 font-semibold text-xs flex items-center justify-center">
                      {st.step_number || i + 1}
                    </span>
                    <span className="text-slate-700 leading-relaxed">{st.instruction}</span>
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
