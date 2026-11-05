import { useEffect, useState } from 'react'

/**
 * Request and retain screen illumination using Screen Wake Lock API.
 * Keeps mobile displays illuminated while cooking without display timeouts.
 */
export function useScreenWakeLock(enabled: boolean) {
  const [isLocked, setIsLocked] = useState(false)

  // Manage native Screen Wake Lock lifecycle based on active toggle.
  useEffect(() => {
    if (!enabled || typeof navigator === 'undefined' || !('wakeLock' in navigator)) {
      setIsLocked(false)
      return
    }

    let sentinel: WakeLockSentinel | null = null
    let isCancelled = false

    // Request wake lock from navigator to prevent screen sleep.
    async function acquireLock() {
      try {
        sentinel = await navigator.wakeLock.request('screen')
        if (isCancelled) {
          void sentinel.release()
          return
        }
        setIsLocked(true)
        sentinel.addEventListener('release', () => {
          setIsLocked(false)
        })
      } catch {
        // Fall back gracefully when device battery saver blocks wake lock.
        setIsLocked(false)
      }
    }

    void acquireLock()

    // Release wake lock when user exits recipe view or disables cooking mode.
    return () => {
      isCancelled = true
      if (sentinel) {
        void sentinel.release()
      }
    }
  }, [enabled])

  return {
    isLocked,
    isSupported: typeof navigator !== 'undefined' && 'wakeLock' in navigator,
  }
}
