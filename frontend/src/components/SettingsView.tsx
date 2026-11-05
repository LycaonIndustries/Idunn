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
  Check,
  Database,
  Copy,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import type { SettingsStatus } from '../types'
import {
  deleteUserAccount,
  exportUserData,
  fetchSettingsStatus,
  updateSettings,
} from '../api'

/**
 * Properties for the SettingsView component.
 */
interface SettingsViewProps {
  /** Optional callback triggered after successful configuration updates. */
  onSettingsUpdated?: () => void
}

/**
 * SettingsView manages database connection credentials and AI API keys.
 *
 * @param props - Component configuration and change notifications.
 * @returns Rendered React element containing settings forms and connection diagnostics.
 */
export const SettingsView: React.FC<SettingsViewProps> = ({ onSettingsUpdated }) => {
  // Store the active system configuration returned by the backend.
  const [status, setStatus] = useState<SettingsStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Manage Supabase project URL and secret service credentials.
  const [supabaseUrl, setSupabaseUrl] = useState('')
  const [supabaseKey, setSupabaseKey] = useState('')
  const [showSupabaseKey, setShowSupabaseKey] = useState(false)
  const [showSqlGuide, setShowSqlGuide] = useState(false)
  const [copiedSql, setCopiedSql] = useState(false)

  // Manage Bring-Your-Own-Key credentials for supported AI model providers.
  const [geminiKey, setGeminiKey] = useState('')
  const [geminiModel, setGeminiModel] = useState('gemini-2.5-flash')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [openaiKey, setOpenAIKey] = useState('')
  const [voyageKey, setVoyageKey] = useState('')

  // Control masked password visibility to protect secrets during screen sharing.
  const [showGemini, setShowGemini] = useState(false)
  const [showAnthropic, setShowAnthropic] = useState(false)
  const [showOpenAI, setShowOpenAI] = useState(false)
  const [showVoyage, setShowVoyage] = useState(false)

  /**
   * Loads current settings configuration and masked credentials from the backend.
   */
  const loadStatus = async () => {
    setLoading(true)
    try {
      const data = await fetchSettingsStatus()
      setStatus(data)
      if (data.gemini_model) setGeminiModel(data.gemini_model)
      if (data.supabase_url) setSupabaseUrl(data.supabase_url)
    } catch (err: unknown) {
      console.error('Failed to load settings:', err)
      setMessage({ type: 'error', text: 'Could not connect to settings backend.' })
    } finally {
      setLoading(false)
    }
  }

  // Load existing configuration once on component mount to populate status badges.
  useEffect(() => {
    void loadStatus()
  }, [])

  /**
   * Validates and submits updated credentials to the server.
   *
   * @param e - Form submission event.
   */
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)

    // Build sparse payload so untouched credentials are not overwritten with empty strings.
    const payload: {
      supabase_url?: string
      supabase_key?: string
      gemini_api_key?: string
      gemini_model?: string
      anthropic_api_key?: string
      openai_api_key?: string
      voyage_api_key?: string
    } = {}

    if (supabaseUrl.trim()) payload.supabase_url = supabaseUrl.trim()
    if (supabaseKey.trim()) payload.supabase_key = supabaseKey.trim()
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
        text: 'Configuration successfully saved! Settings are active in memory & saved to .env',
      })
      // Clear sensitive plain-text input fields from memory after saving.
      setSupabaseKey('')
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

  /**
   * Generates and downloads a machine-readable JSON archive of all personal kitchen data.
   */
  const handleExportData = async () => {
    try {
      const data = await exportUserData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `idunn_data_export_${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to export user data'
      setMessage({ type: 'error', text: msg })
    }
  }

  /**
   * Prompts user and triggers cascade account deletion under GDPR / DPDP.
   */
  const handleDeleteAccount = async () => {
    if (
      !window.confirm(
        'Are you sure you want to permanently delete your account and all associated pantry items, recipes, receipts, and meal plans? This action cannot be undone.'
      )
    ) {
      return
    }
    try {
      await deleteUserAccount()
      window.alert('Account and all associated personal data have been completely erased.')
      window.location.reload()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to erase account'
      setMessage({ type: 'error', text: msg })
    }
  }

  /**
   * Copies the Supabase SQL schema to the user clipboard for quick database initialization.
   */
  const handleCopySql = async () => {
    // Provide embedded DDL script so users can bootstrap tables without finding repo files.
    const sql = `-- Supabase Schema for Iðunn
create table if not exists items (
    id text primary key,
    name text not null,
    quantity double precision not null default 1.0,
    unit text not null default 'piece',
    location text not null default 'fridge',
    expiry_date timestamptz,
    notes text,
    barcode text,
    consumed boolean not null default false,
    added_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists ingredients (
    id text primary key,
    name text not null unique,
    category text not null,
    synonyms jsonb not null default '[]'::jsonb,
    storage_life_days jsonb not null default '{}'::jsonb,
    unit_conversions jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists recipes (
    id text primary key,
    title text not null,
    description text,
    cuisine_type text,
    region text,
    difficulty text,
    prep_time_minutes integer,
    cook_time_minutes integer,
    servings integer,
    source_url text,
    source_name text,
    image_url text,
    video_url text,
    tags text[] not null default '{}',
    ingredients jsonb not null default '[]'::jsonb,
    steps jsonb not null default '[]'::jsonb,
    nutrition jsonb,
    embedding jsonb,
    embedding_model text,
    normalized_ingredients text[] not null default '{}',
    ingredient_matches jsonb not null default '[]'::jsonb,
    ingest_source text,
    ingest_confidence double precision,
    needs_review boolean not null default false,
    extraction_reviewed boolean not null default true,
    revision integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table items enable row level security;
alter table ingredients enable row level security;
alter table recipes enable row level security;

create policy "Allow all on items" on items for all using (true) with check (true);
create policy "Allow all on ingredients" on ingredients for all using (true) with check (true);
create policy "Allow all on recipes" on recipes for all using (true) with check (true);`

    // Write schema string directly to system clipboard for one-click setup.
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable')
      }
      await navigator.clipboard.writeText(sql)
      setCopiedSql(true)
      setTimeout(() => setCopiedSql(false), 2000)
    } catch {
      setMessage({
        type: 'error',
        text: 'Failed to copy SQL to clipboard. Please copy manually from the schema guide.',
      })
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Header gives system overview and cloud persistence mode indicator. */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              Settings & Database
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Supabase Ready
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Configure your Supabase database and BYOK AI models. No local MongoDB or Docker required.
          </p>
        </div>

        <button
          onClick={() => void loadStatus()}
          disabled={loading}
          title="Refresh status"
          className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors self-start sm:self-auto cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Status tiles show connection states for cloud database and active AI model. */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          {/* Inform user whether database persistence is using cloud Supabase or fallback RAM. */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Database Store
              </span>
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`text-sm font-semibold px-2 py-0.5 rounded-md ${
                  status.supabase_configured
                    ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50'
                    : 'bg-blue-950/60 text-blue-400 border border-blue-800/50'
                }`}
              >
                {status.supabase_configured ? 'Supabase Connected' : 'In-Memory (Dev Mode)'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {status.supabase_configured
                ? 'Recipes & pantry persist to your Supabase cloud tables.'
                : 'Zero-setup mode. Add Supabase keys below for permanent cloud sync.'}
            </p>
          </div>

          {/* Gemini AI status tile shows whether key is configured and provides masked view. */}
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
            <p className="text-xs text-slate-500 mt-2">Free tier via Google AI Studio</p>
          </div>

          {/* Display active extraction engine selected from configured providers. */}
          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Active Extractor
              </span>
              <Cpu className="w-4 h-4 text-orange-400" />
            </div>
            <div className="text-sm font-bold text-slate-100 capitalize">
              {status.active_llm_provider !== 'none'
                ? status.active_llm_provider
                : 'None configured'}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {status.active_llm_provider === 'gemini'
                ? `Using ${status.gemini_model}`
                : status.active_llm_provider === 'anthropic'
                  ? 'Using Claude Haiku'
                  : 'Add Gemini key to extract recipes'}
            </p>
          </div>
        </div>
      )}

      {/* Render alert messages when credentials save succeeds or fails. */}
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

      {/* Form collects credentials for Supabase Postgres and AI models. */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Supabase card configuration for cloud database tables. */}
        <div className="bg-slate-900/90 border-2 border-emerald-500/30 rounded-2xl p-6 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-gradient-to-l from-emerald-500 to-teal-500 text-white text-xs font-bold rounded-bl-xl shadow-sm">
            Cloud NoSQL Database
          </div>

          <div className="flex items-start space-x-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Supabase Cloud Database</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Stores your recipes, pantry items, and ingredients in Postgres JSONB with automatic
                backup and zero local daemons.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Supabase Project URL
              </label>
              <input
                type="url"
                placeholder="https://xyzcompany.supabase.co"
                value={supabaseUrl}
                onChange={(e) => setSupabaseUrl(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Supabase Anon / Service Key
              </label>
              <div className="relative">
                <input
                  type={showSupabaseKey ? 'text' : 'password'}
                  placeholder={
                    status?.supabase_configured
                      ? `Current: ${status.supabase_key_masked} (enter new key to update)`
                      : 'eyJhbGciOi...'
                  }
                  value={supabaseKey}
                  onChange={(e) => setSupabaseKey(e.target.value)}
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowSupabaseKey(!showSupabaseKey)}
                  className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 cursor-pointer"
                >
                  {showSupabaseKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          {/* Collapsible guide shows schema creation steps to remove documentation friction. */}
          <div className="pt-2 border-t border-slate-800/80">
            <button
              type="button"
              onClick={() => setShowSqlGuide(!showSqlGuide)}
              className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-emerald-400 transition-colors py-1 cursor-pointer"
            >
              <span className="font-semibold flex items-center space-x-1.5">
                <span>How to set up Supabase in 2 minutes</span>
              </span>
              {showSqlGuide ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showSqlGuide && (
              <div className="mt-3 p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300 space-y-3">
                <ol className="list-decimal list-inside space-y-1.5 leading-relaxed text-slate-400">
                  <li>
                    Go to{' '}
                    <a
                      href="https://supabase.com/dashboard"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400 hover:underline inline-flex items-center space-x-1"
                    >
                      <span>supabase.com</span>
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </a>{' '}
                    and create a free project.
                  </li>
                  <li>
                    In your Supabase dashboard, open the <strong>SQL Editor</strong> in the left sidebar.
                  </li>
                  <li>
                    Click below to copy the tables SQL script and paste it into the SQL Editor, then
                    click <strong>Run</strong>:
                  </li>
                </ol>

                <div className="flex items-center space-x-3 pt-1">
                  <button
                    type="button"
                    onClick={handleCopySql}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 transition-colors cursor-pointer"
                  >
                    {copiedSql ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedSql ? 'Copied to Clipboard!' : 'Copy SQL Schema Script'}</span>
                  </button>
                  <span className="text-slate-500 font-mono text-[11px]">
                    or see file <code className="text-emerald-400">db/schema.sql</code>
                  </span>
                </div>

                <p className="text-slate-400 pt-1">
                  4. Finally, go to <strong>Project Settings &gt; API</strong>, copy your{' '}
                  <strong>Project URL</strong> and <strong>anon key</strong>, and paste them above!
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Gemini Provider card provides free-tier multimodal AI extraction. */}
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
                Powers video reel keyframe sampling, voice note transcription, photo OCR, and text
                parsing with zero API bills.
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
                  className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 cursor-pointer"
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
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent text-sm font-mono cursor-pointer"
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

        {/* Anthropic Claude card offers alternative high-accuracy text extraction. */}
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
                className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 cursor-pointer"
              >
                {showAnthropic ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* OpenAI and Voyage AI providers allow custom embedding and fallback options. */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300 cursor-pointer"
              >
                {showOpenAI ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-100 mb-1">Voyage AI (Embeddings)</h2>
            <p className="text-xs text-slate-400 mb-3">
              Powers Indian ingredient vector embeddings in search.
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
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300 cursor-pointer"
              >
                {showVoyage ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Security badge assures user keys are never transmitted to third-party telemetry. */}
        <div className="flex items-start space-x-3 bg-slate-900/40 border border-slate-800 rounded-xl p-4 text-xs text-slate-400">
          <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong className="text-slate-300">Privacy & Security:</strong> Your keys are stored
            locally on your machine in <code className="text-orange-400 font-mono">.env</code> and
            loaded directly into Iðunn&apos;s runtime memory.
          </p>
        </div>

        {/* Submit button locks in changes and initiates background persistence. */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-sm flex items-center space-x-2 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Applying Changes...</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save All Settings</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* GDPR / DPDP Privacy, Data Portability & Account Erasure */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-200">
            Data Privacy & Compliance (GDPR / DPDP)
          </h2>
          <p className="text-xs text-slate-400">
            Export all personal kitchen records or execute irreversible cascade account erasure.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => void handleExportData()}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition cursor-pointer"
          >
            Download Data Archive (JSON)
          </button>

          <button
            type="button"
            onClick={() => void handleDeleteAccount()}
            className="px-4 py-2 rounded-xl bg-red-950/60 hover:bg-red-900/60 text-red-300 text-xs font-semibold border border-red-800/60 transition cursor-pointer"
          >
            Delete My Account & Data
          </button>
        </div>
      </div>
    </div>
  )
}
