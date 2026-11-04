import React, { useState, useEffect } from 'react'
import {
  KeyRound,
  ShieldCheck,
  Sparkles,
  Cpu,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Save,
  Loader2,
  RefreshCw,
  FileCode,
  Check,
} from 'lucide-react'
import type { SettingsStatus } from '../types'
import { fetchSettingsStatus, updateSettings } from '../api'

interface SettingsViewProps {
  onSettingsUpdated?: () => void
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onSettingsUpdated }) => {
  const [status, setStatus] = useState<SettingsStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Form fields
  const [geminiKey, setGeminiKey] = useState('')
  const [geminiModel, setGeminiModel] = useState('gemini-2.5-flash')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [openaiKey, setOpenAIKey] = useState('')
  const [voyageKey, setVoyageKey] = useState('')

  // Show/hide toggles
  const [showGemini, setShowGemini] = useState(false)
  const [showAnthropic, setShowAnthropic] = useState(false)
  const [showOpenAI, setShowOpenAI] = useState(false)
  const [showVoyage, setShowVoyage] = useState(false)

  const loadStatus = async () => {
    setLoading(true)
    try {
      const data = await fetchSettingsStatus()
      setStatus(data)
      if (data.gemini_model) setGeminiModel(data.gemini_model)
    } catch (err: unknown) {
      console.error('Failed to load settings:', err)
      setMessage({ type: 'error', text: 'Could not connect to settings backend.' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    const payload: {
      gemini_api_key?: string
      gemini_model?: string
      anthropic_api_key?: string
      openai_api_key?: string
      voyage_api_key?: string
    } = {}

    if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim()
    if (geminiModel.trim()) payload.gemini_model = geminiModel.trim()
    if (anthropicKey.trim()) payload.anthropic_api_key = anthropicKey.trim()
    if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim()
    if (voyageKey.trim()) payload.voyage_api_key = voyageKey.trim()

    try {
      const updated = await updateSettings(payload)
      setStatus(updated)
      setMessage({
        type: 'success',
        text: 'BYOK configuration successfully saved! Keys are applied in runtime & saved to .env',
      })
      // Clear inputs
      setGeminiKey('')
      setAnthropicKey('')
      setOpenAIKey('')
      setVoyageKey('')
      if (onSettingsUpdated) onSettingsUpdated()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save settings'
      setMessage({ type: 'error', text: msg })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              Settings & BYOK Setup
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
              Zero-Cost Ready
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Bring Your Own Key (BYOK) to extract recipes from reels, voice notes, photos, and web URLs without host limits.
          </p>
        </div>

        <button
          onClick={loadStatus}
          disabled={loading}
          title="Refresh status"
          className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Provider Status Overview */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {/* Active Provider */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Active Extractor
              </span>
              <Cpu className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-lg font-bold text-slate-100 capitalize">
              {status.active_llm_provider !== 'none' ? status.active_llm_provider : 'None configured'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {status.active_llm_provider === 'gemini'
                ? `Using ${status.gemini_model} (multimodal + fast)`
                : status.active_llm_provider === 'anthropic'
                ? 'Using Claude Haiku 4.5'
                : 'Configure a provider below to enable AI'}
            </p>
          </div>

          {/* Gemini Status */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Google Gemini
              </span>
              {status.gemini_configured ? (
                <Check className="w-4 h-4 text-emerald-400" />
              ) : (
                <span className="w-2 h-2 rounded-full bg-amber-500" />
              )}
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`text-sm font-semibold px-2 py-0.5 rounded-md ${
                  status.gemini_configured
                    ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                    : 'bg-amber-950/60 text-amber-400 border border-amber-800/50'
                }`}
              >
                {status.gemini_configured ? 'Configured' : 'Needs Key'}
              </span>
              {status.gemini_api_key_masked && (
                <span className="text-xs font-mono text-slate-500">
                  {status.gemini_api_key_masked}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-2">Free tier supported via Google AI Studio</p>
          </div>

          {/* Storage / .env Status */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Environment File
              </span>
              <FileCode className="w-4 h-4 text-blue-400" />
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`text-sm font-semibold px-2 py-0.5 rounded-md ${
                  status.env_file_exists
                    ? 'bg-blue-950/60 text-blue-400 border border-blue-800/50'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
              >
                {status.env_file_exists ? '.env Active' : '.env Missing'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Updates saved here persist across restarts.
            </p>
          </div>
        </div>
      )}

      {/* Alert Messages */}
      {message && (
        <div
          className={`flex items-center space-x-2 text-sm p-4 rounded-xl border mb-6 ${
            message.type === 'success'
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/80'
              : 'bg-red-950/40 text-red-300 border-red-800/80'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-400" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Main Settings Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Gemini Provider Card (Highlighted) */}
        <div className="bg-slate-900/90 border-2 border-orange-500/30 rounded-2xl p-6 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-gradient-to-l from-orange-500 to-amber-500 text-white text-xs font-bold rounded-bl-xl shadow-sm">
            Recommended • 100% Free Tier
          </div>

          <div className="flex items-start space-x-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-orange-500/20 text-orange-400 border border-orange-500/30 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Google Gemini BYOK</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Powers video reel keyframe sampling, voice note transcription, photo OCR, and text parsing with zero API bills.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Gemini API Key
              </label>
              <div className="relative">
                <input
                  type={showGemini ? 'text' : 'password'}
                  placeholder={
                    status?.gemini_configured
                      ? `Current: ${status.gemini_api_key_masked} (enter new key to update)`
                      : 'AIzaSy...'
                  }
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowGemini(!showGemini)}
                  className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
                >
                  {showGemini ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Model Name
              </label>
              <select
                value={geminiModel}
                onChange={(e) => setGeminiModel(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm font-mono"
              >
                <option value="gemini-2.5-flash">gemini-2.5-flash (Fastest)</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                <option value="gemini-1.5-pro">gemini-1.5-pro (High reasoning)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800/80">
            <span className="text-slate-500">Need a free key? Get one in 10 seconds:</span>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="text-orange-400 hover:text-orange-300 font-semibold inline-flex items-center space-x-1"
            >
              <span>Get Gemini API Key on Google AI Studio</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Anthropic Claude Card */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-6 shadow-sm">
          <div className="flex items-start space-x-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center flex-shrink-0">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Anthropic Claude</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Uses Claude Haiku 4.5 for high-accuracy structured JSON extraction.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Anthropic API Key
            </label>
            <div className="relative">
              <input
                type={showAnthropic ? 'text' : 'password'}
                placeholder={
                  status?.anthropic_configured
                    ? `Current: ${status.anthropic_api_key_masked} (enter new key to update)`
                    : 'sk-ant-api...'
                }
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => setShowAnthropic(!showAnthropic)}
                className="absolute right-3 top-3 text-slate-500 hover:text-slate-300"
              >
                {showAnthropic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Voyage AI & OpenAI Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* OpenAI */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-100 mb-1">OpenAI API Key</h2>
            <p className="text-xs text-slate-400 mb-3">Optional fallback provider.</p>
            <div className="relative">
              <input
                type={showOpenAI ? 'text' : 'password'}
                placeholder={
                  status?.openai_configured
                    ? `Current: ${status.openai_api_key_masked}`
                    : 'sk-...'
                }
                value={openaiKey}
                onChange={(e) => setOpenAIKey(e.target.value)}
                className="w-full px-3 py-2 pr-10 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => setShowOpenAI(!showOpenAI)}
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
              >
                {showOpenAI ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Voyage AI */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-100 mb-1">Voyage AI (Embeddings)</h2>
            <p className="text-xs text-slate-400 mb-3">
              Powers Indian ingredient vector embeddings in Atlas search.
            </p>
            <div className="relative">
              <input
                type={showVoyage ? 'text' : 'password'}
                placeholder={
                  status?.voyage_configured
                    ? `Current: ${status.voyage_api_key_masked}`
                    : 'pa-...'
                }
                value={voyageKey}
                onChange={(e) => setVoyageKey(e.target.value)}
                className="w-full px-3 py-2 pr-10 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 text-sm font-mono"
              />
              <button
                type="button"
                onClick={() => setShowVoyage(!showVoyage)}
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
              >
                {showVoyage ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Security / Architecture Note */}
        <div className="flex items-start space-x-3 bg-slate-900/40 border border-slate-800 rounded-xl p-4 text-xs text-slate-400">
          <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-slate-300">Privacy & Security:</strong> Your keys are stored locally on your machine in <code className="text-orange-400 font-mono">.env</code> and loaded directly into Iðunn&apos;s runtime memory. They are never sent to any third-party telemetry or cloud servers.
          </p>
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-3 rounded-xl bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-semibold text-sm flex items-center space-x-2 shadow-lg shadow-orange-500/20 transition-all cursor-pointer"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Applying Changes...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save & Apply Settings</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
