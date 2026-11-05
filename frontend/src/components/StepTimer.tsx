import React, { useEffect, useState } from 'react'
import { Play, Pause, RotateCcw, Timer } from 'lucide-react'

interface StepTimerProps {
  durationSeconds: number
  label?: string
}

// Play pleasant two-tone audio alert using standard Web Audio API.
function playChime() {
  try {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    // Sound pleasant dual-frequency notification tone.
    osc.frequency.setValueAtTime(587.33, ctx.currentTime) // D5
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15) // A5

    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.6)
  } catch {
    // Gracefully handle browser autoplay or AudioContext restrictions.
  }
}

export const StepTimer: React.FC<StepTimerProps> = ({ durationSeconds, label }) => {
  const [timeLeft, setTimeLeft] = useState(durationSeconds)
  const [isRunning, setIsRunning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)

  // Countdown timer interval management.
  useEffect(() => {
    if (!isRunning || timeLeft <= 0) return

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setIsRunning(false)
          setIsCompleted(true)
          playChime()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isRunning, timeLeft])

  // Reset timer back to full duration.
  const handleReset = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsRunning(false)
    setIsCompleted(false)
    setTimeLeft(durationSeconds)
  }

  // Toggle running state.
  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (timeLeft === 0) {
      setTimeLeft(durationSeconds)
      setIsCompleted(false)
      setIsRunning(true)
    } else {
      setIsRunning((prev) => !prev)
    }
  }

  const mins = Math.floor(timeLeft / 60)
  const secs = timeLeft % 60
  const formattedTime = `${mins}:${secs.toString().padStart(2, '0')}`

  return (
    <div
      className={`inline-flex items-center space-x-2 px-2.5 py-1 rounded-xl text-xs font-semibold border transition-all ${
        isCompleted
          ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
          : isRunning
            ? 'bg-amber-950/60 border-amber-800 text-amber-300 ring-1 ring-amber-500/40'
            : 'bg-slate-900 border-slate-800 text-slate-300'
      }`}
    >
      <Timer className="w-3.5 h-3.5 flex-shrink-0" />
      <span>{label || 'Timer'}:</span>
      <span className="font-mono font-bold tracking-wider">{formattedTime}</span>

      {/* Control buttons */}
      <div className="flex items-center space-x-1 pl-1">
        <button
          type="button"
          onClick={handleToggle}
          aria-label={isRunning ? 'Pause timer' : 'Start timer'}
          className="p-1 rounded-lg hover:bg-slate-800 text-slate-200 transition-colors cursor-pointer"
        >
          {isRunning ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
        </button>

        <button
          type="button"
          onClick={handleReset}
          aria-label="Reset timer"
          className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
      </div>

      {isCompleted && <span className="text-[10px] text-emerald-400 font-bold ml-1">Done!</span>}
    </div>
  )
}
