import { Flame, Timer, X } from 'lucide-react'
import { useMultiCook } from '../context/useMultiCook'
import type { Recipe } from '../types'

interface MultiCookWorkspaceProps {
  onSelectRecipe: (recipe: Recipe) => void
}

/**
 * Multi-cook session switcher banner for simultaneous dish preparation.
 * Displays tabs for active dishes, current steps, and running timers.
 */
export function MultiCookWorkspace({ onSelectRecipe }: MultiCookWorkspaceProps) {
  const { sessions, activeRecipeId, stopCooking, setActiveRecipeId } = useMultiCook()

  // Omit switcher bar if only zero or one recipe is being actively prepared.
  if (sessions.length <= 1) return null

  return (
    <div className="bg-slate-900/95 border-b border-orange-500/30 px-4 py-2 sticky top-16 z-40 backdrop-blur-md shadow-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3 overflow-x-auto">
        <div className="flex items-center gap-2">
          <Flame className="w-4 h-4 text-orange-400 shrink-0 animate-pulse" />
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider shrink-0">
            Multi-Cook:
          </span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto py-1">
          {sessions.map((session) => {
            const rId = session.recipe.id || session.recipe._id || ''
            const isActive = rId === activeRecipeId
            const runningTimers = session.timers.filter((t) => t.isRunning)

            return (
              <div
                key={rId}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-orange-500/20 border-orange-500/50 text-orange-300 ring-1 ring-orange-500/40'
                    : 'bg-slate-950/70 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
                onClick={() => {
                  setActiveRecipeId(rId)
                  onSelectRecipe(session.recipe)
                }}
              >
                <span>{session.recipe.title}</span>
                {session.activeStep && (
                  <span className="px-1.5 py-0.2 rounded-md bg-slate-800/80 text-[10px] text-slate-300">
                    Step {session.activeStep}
                  </span>
                )}
                {runningTimers.length > 0 && (
                  <span className="flex items-center gap-0.5 text-amber-400 text-[10px] font-mono">
                    <Timer className="w-3 h-3" />
                    {runningTimers[0].remainingSeconds}s
                  </span>
                )}
                <button
                  type="button"
                  title="Close dish from multi-cook"
                  onClick={(e) => {
                    e.stopPropagation()
                    stopCooking(rId)
                  }}
                  className="p-0.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
