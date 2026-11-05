import { describe, expect, it, mock } from 'bun:test'
import { renderHook } from '@testing-library/react'
import { useScreenWakeLock } from '../../src/hooks/useScreenWakeLock'

describe('useScreenWakeLock hook', () => {
  it('reports unsupported when wakeLock is not in navigator', () => {
    const { result } = renderHook(() => useScreenWakeLock(true))
    expect(result.current.isLocked).toBe(false)
  })

  it('acquires and releases wake lock when navigator.wakeLock is supported', async () => {
    let released = false
    const mockSentinel = {
      release: mock(async () => {
        released = true
      }),
      addEventListener: mock(() => {}),
    }

    const originalWakeLock = (navigator as unknown as { wakeLock?: unknown }).wakeLock
    ;(navigator as unknown as { wakeLock: unknown }).wakeLock = {
      request: mock(async () => mockSentinel),
    }

    try {
      const { result, unmount } = renderHook(({ enabled }) => useScreenWakeLock(enabled), {
        initialProps: { enabled: true },
      })

      // Allow microtask to process acquireLock promise.
      await new Promise((r) => setTimeout(r, 10))

      expect(result.current.isSupported).toBe(true)
      expect(result.current.isLocked).toBe(true)

      unmount()
      expect(released).toBe(true)
    } finally {
      if (originalWakeLock !== undefined) {
        ;(navigator as unknown as { wakeLock: unknown }).wakeLock = originalWakeLock
      } else {
        delete (navigator as unknown as { wakeLock?: unknown }).wakeLock
      }
    }
  })
})
