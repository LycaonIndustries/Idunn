import { useEffect, useRef, useState } from 'react'

export interface CameraGesturesOptions {
  enabled: boolean
  onNextStep: () => void
  onPrevStep: () => void
}

export interface CameraGesturesState {
  isActive: boolean
  isSupported: boolean
  error: string | null
  lastGesture: 'next' | 'prev' | 'cover' | null
}

const DOWNSAMPLE_WIDTH = 32
const DOWNSAMPLE_HEIGHT = 24
const GESTURE_COOLDOWN_MS = 1200
const OCCLUSION_MAX_DURATION_MS = 1500

/**
 * Hands-free recipe step navigation hook using front-facing camera.
 * Analyzes local canvas luminosity and optical motion without streaming video.
 */
export function useCameraGestures({
  enabled,
  onNextStep,
  onPrevStep,
}: CameraGesturesOptions): CameraGesturesState {
  const isSupported =
    typeof navigator !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia)

  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastGesture, setLastGesture] = useState<'next' | 'prev' | 'cover' | null>(null)

  // Keep latest callbacks in refs to avoid restarting video stream on parent re-renders.
  const nextCallbackRef = useRef(onNextStep)
  const prevCallbackRef = useRef(onPrevStep)

  useEffect(() => {
    nextCallbackRef.current = onNextStep
    prevCallbackRef.current = onPrevStep
  }, [onNextStep, onPrevStep])

  // Track gesture processing state across animation frames.
  const streamRef = useRef<MediaStream | null>(null)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const lastTriggerTimeRef = useRef<number>(0)
  const coverStartTimeRef = useRef<number | null>(null)
  const baselineLumaRef = useRef<number>(128)
  const prevLumaGridRef = useRef<Uint8Array | null>(null)
  const motionHistoryRef = useRef<number[]>([])

  useEffect(() => {
    // Abort camera activation if feature is disabled or unsupported.
    if (!enabled || !isSupported) {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
      return
    }

    let isCancelled = false
    let animationFrameId: number | null = null

    // Create offscreen canvas for zero-streaming frame analysis.
    const canvas = document.createElement('canvas')
    canvas.width = DOWNSAMPLE_WIDTH
    canvas.height = DOWNSAMPLE_HEIGHT
    const ctx = canvas.getContext('2d', { willReadFrequently: true })

    const video = document.createElement('video')
    video.autoplay = true
    video.muted = true
    video.playsInline = true
    videoRef.current = video

    // Request local front-facing camera stream.
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'user',
            width: { ideal: 160 },
            height: { ideal: 120 },
          },
          audio: false,
        })

        if (isCancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        streamRef.current = stream
        video.srcObject = stream
        await video.play()

        setIsActive(true)
        setError(null)

        // Process downsampled frames on interval to detect gestures.
        analyzeFrames()
      } catch (err) {
        if (!isCancelled) {
          setIsActive(false)
          setError(err instanceof Error ? err.message : 'Camera permission denied')
        }
      }
    }

    // Measure palm occlusion and directional hand wave without external dependencies.
    function analyzeFrames() {
      if (isCancelled || !ctx || !video) return

      if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        ctx.drawImage(video, 0, 0, DOWNSAMPLE_WIDTH, DOWNSAMPLE_HEIGHT)
        const frame = ctx.getImageData(0, 0, DOWNSAMPLE_WIDTH, DOWNSAMPLE_HEIGHT)
        const data = frame.data
        const totalPixels = DOWNSAMPLE_WIDTH * DOWNSAMPLE_HEIGHT

        let totalLuma = 0
        const currentGrid = new Uint8Array(totalPixels)

        // Extract grayscale luminance for optical difference analysis.
        for (let i = 0; i < totalPixels; i++) {
          const offset = i * 4
          const luma = Math.round(
            data[offset] * 0.299 + data[offset + 1] * 0.587 + data[offset + 2] * 0.114
          )
          currentGrid[i] = luma
          totalLuma += luma
        }

        const avgLuma = totalLuma / totalPixels
        const now = performance.now()
        const timeSinceLastGesture = now - lastTriggerTimeRef.current

        // Adaptively track room ambient lighting baseline.
        if (coverStartTimeRef.current === null) {
          baselineLumaRef.current = baselineLumaRef.current * 0.95 + avgLuma * 0.05
        }

        const isOccluded = avgLuma < Math.max(20, baselineLumaRef.current * 0.4)

        // Check for palm occlusion gesture (cover camera and release to advance).
        if (isOccluded) {
          if (coverStartTimeRef.current === null) {
            coverStartTimeRef.current = now
          }
        } else if (coverStartTimeRef.current !== null) {
          const duration = now - coverStartTimeRef.current
          coverStartTimeRef.current = null

          // Trigger next step if lens was covered momentarily.
          if (
            duration >= 150 &&
            duration <= OCCLUSION_MAX_DURATION_MS &&
            timeSinceLastGesture > GESTURE_COOLDOWN_MS
          ) {
            lastTriggerTimeRef.current = now
            setLastGesture('cover')
            nextCallbackRef.current()
          }
        }

        // Check directional motion if camera is not occluded.
        if (!isOccluded && prevLumaGridRef.current && timeSinceLastGesture > GESTURE_COOLDOWN_MS) {
          const prevGrid = prevLumaGridRef.current
          let motionWeight = 0
          let motionCentroidX = 0

          for (let y = 0; y < DOWNSAMPLE_HEIGHT; y++) {
            for (let x = 0; x < DOWNSAMPLE_WIDTH; x++) {
              const idx = y * DOWNSAMPLE_WIDTH + x
              const diff = Math.abs(currentGrid[idx] - prevGrid[idx])
              if (diff > 25) {
                motionWeight += diff
                motionCentroidX += x * diff
              }
            }
          }

          // Register horizontal swipe when motion passes energy threshold.
          if (motionWeight > totalPixels * 6) {
            const centroidX = motionCentroidX / motionWeight
            const history = motionHistoryRef.current
            history.push(centroidX)
            if (history.length > 5) history.shift()

            if (history.length >= 3) {
              const delta = history[history.length - 1] - history[0]
              // Wave left-to-right advances recipe; right-to-left returns to previous step.
              if (delta > 7.0) {
                lastTriggerTimeRef.current = now
                motionHistoryRef.current = []
                setLastGesture('next')
                nextCallbackRef.current()
              } else if (delta < -7.0) {
                lastTriggerTimeRef.current = now
                motionHistoryRef.current = []
                setLastGesture('prev')
                prevCallbackRef.current()
              }
            }
          } else {
            motionHistoryRef.current = []
          }
        }

        prevLumaGridRef.current = currentGrid
      }

      animationFrameId = requestAnimationFrame(analyzeFrames)
    }

    void initCamera()

    // Stop all media tracks and cancel frame processing on teardown.
    return () => {
      isCancelled = true
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId)
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
      setIsActive(false)
    }
  }, [enabled, isSupported])

  return {
    isActive,
    isSupported,
    error,
    lastGesture,
  }
}
