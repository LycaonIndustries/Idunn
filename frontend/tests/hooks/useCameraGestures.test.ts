import { describe, expect, it, mock } from 'bun:test'
import { renderHook } from '@testing-library/react'
import { useCameraGestures } from '../../src/hooks/useCameraGestures'

describe('useCameraGestures hook', () => {
  it('reports unsupported when mediaDevices is not in navigator', () => {
    const originalMediaDevices = navigator.mediaDevices
    try {
      Object.defineProperty(navigator, 'mediaDevices', {
        value: undefined,
        configurable: true,
      })

      const { result } = renderHook(() =>
        useCameraGestures({
          enabled: true,
          onNextStep: () => {},
          onPrevStep: () => {},
        })
      )

      expect(result.current.isSupported).toBe(false)
      expect(result.current.isActive).toBe(false)
    } finally {
      Object.defineProperty(navigator, 'mediaDevices', {
        value: originalMediaDevices,
        configurable: true,
      })
    }
  })

  it('requests front-facing camera stream and releases tracks on unmount', async () => {
    let stopped = false
    const mockTrack = {
      stop: mock(() => {
        stopped = true
      }),
    }
    const mockStream = {
      getTracks: () => [mockTrack],
    }

    const originalMediaDevices = navigator.mediaDevices
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: mock(async () => mockStream),
      },
      configurable: true,
    })

    try {
      const onNext = mock(() => {})
      const onPrev = mock(() => {})

      const { result, unmount } = renderHook(
        ({ enabled }) =>
          useCameraGestures({
            enabled,
            onNextStep: onNext,
            onPrevStep: onPrev,
          }),
        { initialProps: { enabled: true } }
      )

      expect(result.current.isSupported).toBe(true)

      // Allow async initCamera to process.
      await new Promise((r) => setTimeout(r, 20))

      unmount()
      expect(stopped).toBe(true)
    } finally {
      Object.defineProperty(navigator, 'mediaDevices', {
        value: originalMediaDevices,
        configurable: true,
      })
    }
  })

  it('handles permission denial gracefully with error state', async () => {
    const originalMediaDevices = navigator.mediaDevices
    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: mock(async () => {
          throw new Error('NotAllowedError: Permission denied')
        }),
      },
      configurable: true,
    })

    try {
      const { result } = renderHook(() =>
        useCameraGestures({
          enabled: true,
          onNextStep: () => {},
          onPrevStep: () => {},
        })
      )

      await new Promise((r) => setTimeout(r, 20))

      expect(result.current.isActive).toBe(false)
      expect(result.current.error).toContain('NotAllowedError')
    } finally {
      Object.defineProperty(navigator, 'mediaDevices', {
        value: originalMediaDevices,
        configurable: true,
      })
    }
  })
})
