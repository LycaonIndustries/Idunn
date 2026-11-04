/**
 * Application header navigation bar for Iðunn Kitchen OS.
 * Displays brand identity, tab controls, dynamic badge counts, and BYOK indicator.
 */

import React from 'react'
import { Sparkles, BookOpen, Package, ChefHat, Settings } from 'lucide-react'

/**
 * Properties for the Navbar component.
 */
interface NavbarProps {
  /** Active navigation tab key. */
  activeTab: 'capture' | 'vault' | 'pantry' | 'settings'
  /** Tab switch event handler. */
  setActiveTab: (tab: 'capture' | 'vault' | 'pantry' | 'settings') => void
  /** Total number of stored recipes for badge display. */
  recipeCount: number
  /** Total number of active pantry items for badge display. */
  pantryCount: number
  /** Whether user has configured their BYOK API keys. */
  isByokConfigured?: boolean
}

/**
 * Sticky top navigation header with blurred translucent backdrop.
 *
 * @param props - Component properties.
 * @returns Header JSX element.
 */
export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  recipeCount,
  pantryCount,
  isByokConfigured = false,
}) => {
  return (
    // Use sticky positioning and backdrop blur so navigation controls remain accessible while scrolling.
    <header className="sticky top-0 z-30 bg-slate-900/85 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        {/* Brand logo clicking routes to capture home */}
        <div
          className="flex items-center space-x-3 cursor-pointer"
          onClick={() => setActiveTab('capture')}
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
            <ChefHat className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-xl tracking-tight text-slate-100">Iðunn</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              India-aware Kitchen OS & Multimodal Vault
            </p>
          </div>
        </div>

        {/* Tab switch buttons */}
        <nav className="flex space-x-1 sm:space-x-2">
          {/* AI Ingestion Tab */}
          <button
            onClick={() => setActiveTab('capture')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'capture'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Capture</span>
          </button>

          {/* Recipe Vault Tab with live count pill */}
          <button
            onClick={() => setActiveTab('vault')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'vault'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Recipes</span>
            {recipeCount > 0 && (
              <span
                className={`text-xs px-1.5 py-0.2 rounded-full ${
                  activeTab === 'vault'
                    ? 'bg-orange-600 text-white'
                    : 'bg-slate-800 text-slate-300'
                }`}
              >
                {recipeCount}
              </span>
            )}
          </button>

          {/* Pantry Inventory Tab */}
          <button
            onClick={() => setActiveTab('pantry')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === 'pantry'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Package className="w-4 h-4" />
            <span>Pantry</span>
            {pantryCount > 0 && (
              <span
                className={`text-xs px-1.5 py-0.2 rounded-full ${
                  activeTab === 'pantry'
                    ? 'bg-orange-600 text-white'
                    : 'bg-slate-800 text-slate-300'
                }`}
              >
                {pantryCount}
              </span>
            )}
          </button>

          {/* BYOK Settings Tab with warning beacon when unconfigured */}
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-xl text-sm font-medium transition-all relative ${
              activeTab === 'settings'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
            title="BYOK & App Settings"
          >
            <Settings className="w-4 h-4" />
            <span className="hidden sm:inline">Settings</span>
            {!isByokConfigured && (
              // Display pulsing amber dot when no API key is configured to prompt onboarding.
              <span
                className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"
                title="BYOK setup recommended"
              />
            )}
          </button>
        </nav>
      </div>
    </header>
  )
}

export default Navbar
