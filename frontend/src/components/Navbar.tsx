import React from 'react'
import { Sparkles, BookOpen, Package, ChefHat } from 'lucide-react'

interface NavbarProps {
  activeTab: 'capture' | 'vault' | 'pantry'
  setActiveTab: (tab: 'capture' | 'vault' | 'pantry') => void
  recipeCount: number
  pantryCount: number
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  recipeCount,
  pantryCount,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
            <ChefHat className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-xl tracking-tight text-slate-900">Iðunn</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-orange-100 text-orange-700">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">India-aware Kitchen OS & Multimodal Vault</p>
          </div>
        </div>

        <nav className="flex space-x-1 sm:space-x-2">
          <button
            onClick={() => setActiveTab('capture')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'capture'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>AI Capture</span>
          </button>

          <button
            onClick={() => setActiveTab('vault')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'vault'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Recipes</span>
            {recipeCount > 0 && (
              <span className={`text-xs px-1.5 py-0.2 rounded-full ${
                activeTab === 'vault' ? 'bg-orange-600 text-white' : 'bg-slate-200 text-slate-700'
              }`}>
                {recipeCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('pantry')}
            className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'pantry'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Package className="w-4 h-4" />
            <span>Pantry</span>
            {pantryCount > 0 && (
              <span className={`text-xs px-1.5 py-0.2 rounded-full ${
                activeTab === 'pantry' ? 'bg-orange-600 text-white' : 'bg-slate-200 text-slate-700'
              }`}>
                {pantryCount}
              </span>
            )}
          </button>
        </nav>
      </div>
    </header>
  )
}
