/**
 * Dotted Glow Background — Aceternity-style animated dot grid.
 * Pure canvas, framework-free. Each dot shimmers independently via a
 * triangle-wave alpha cycle with optional glow bloom on bright peaks.
 *
 * Returns a dispose() handle that tears down observers + rAF.
 */

import { V2_FRAME_MS as GRAIN_FRAME_MS, prefersReducedMotion } from "./runtime"

export interface DottedGlowOpts {
  /** Grid spacing in CSS px (default 14). */
  gap?: number
  /** Dot base radius in CSS px (default 1.8). */
  radius?: number
  /** Dot fill rgba without alpha, e.g. "255,255,255" (default "255,255,255"). */
  color?: string
  /** Glow shadow color rgba (default "255,255,255,0.6"). */
  glowColor?: string
  /** Base opacity multiplier 0-1 (default 0.5). */
  opacity?: number
  /** Min angular speed rad/s (default 0.4). */
  speedMin?: number
  /** Max angular speed rad/s (default 1.3). */
  speedMax?: number
  /** Global speed scale multiplier (default 1). */
  speedScale?: number
  /** Radial vignette edge opacity 0-1 (default 0). */
  backgroundOpacity?: number
}

interface Dot {
  x: number
  y: number
  phase: number
  speed: number
}

const TWO_PI = Math.PI * 2

export function createDottedGlow(container: HTMLElement, opts: DottedGlowOpts = {}): () => void {
  const {
    gap = 14,
    radius = 1.8,
    color = "255,255,255",
    glowColor = "255,255,255,0.6",
    opacity = 0.5,
    speedMin = 0.4,
    speedMax = 1.3,
    speedScale = 1,
    backgroundOpacity = 0,
  } = opts

  // Canvas element -----------------------------------------------------------
  const canvas = document.createElement("canvas")
  canvas.className = "dotted-glow__canvas"
  canvas.setAttribute("aria-hidden", "true")
  canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;"
  container.appendChild(canvas)

  const ctx = canvas.getContext("2d")!

  // Hi-DPI -------------------------------------------------------------------
  let dpr = Math.min(window.devicePixelRatio || 1, 2)
  let logicalW = 0
  let logicalH = 0

  // Dot grid -----------------------------------------------------------------
  let dots: Dot[] = []

  function buildGrid() {
    logicalW = container.clientWidth
    logicalH = container.clientHeight

    const pw = logicalW * dpr
    const ph = logicalH * dpr
    canvas.width = pw
    canvas.height = ph
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    dots = []
    const cols = Math.ceil(logicalW / gap) + 1
    const rows = Math.ceil(logicalH / gap) + 1

    for (let r = 0; r < rows; r++) {
      const stagger = r % 2 === 1 ? gap * 0.5 : 0
      for (let c = 0; c < cols; c++) {
        dots.push({
          x: c * gap + stagger,
          y: r * gap,
          phase: Math.random() * TWO_PI,
          speed: (speedMin + Math.random() * (speedMax - speedMin)) * speedScale,
        })
      }
    }
  }

  // Render -------------------------------------------------------------------
  function draw(timeMs: number) {
    const t = timeMs / 1000
    ctx.clearRect(0, 0, logicalW, logicalH)

    // Optional radial vignette
    if (backgroundOpacity > 0) {
      const cx = logicalW / 2
      const cy = logicalH / 2
      const maxR = Math.hypot(cx, cy)
      const grad = ctx.createRadialGradient(cx, cy, maxR * 0.1, cx, cy, maxR * 0.7)
      grad.addColorStop(0, "transparent")
      grad.addColorStop(1, `rgba(0,0,0,${backgroundOpacity})`)
      ctx.fillStyle = grad
      ctx.fillRect(0, 0, logicalW, logicalH)
    }

    ctx.shadowBlur = 0
    ctx.shadowColor = "transparent"

    for (let i = 0; i < dots.length; i++) {
      const d = dots[i]
      // Triangle wave: mod = (t*speed + phase) % 2
      const mod = (((t * d.speed + d.phase) % 2) + 2) % 2 // ensure positive
      const lin = mod < 1 ? mod : 2 - mod
      const alpha = (0.25 + 0.55 * lin) * opacity

      // Glow when bright
      if (alpha > 0.6 * opacity) {
        const glow = (alpha / opacity - 0.6) / 0.4
        ctx.shadowBlur = 6 * glow
        ctx.shadowColor = `rgba(${glowColor})`
      } else {
        ctx.shadowBlur = 0
      }

      ctx.fillStyle = `rgba(${color},${alpha.toFixed(3)})`
      ctx.beginPath()
      ctx.arc(d.x, d.y, radius, 0, TWO_PI)
      ctx.fill()
    }
  }

  // Static mid-brightness frame for reduced-motion ---------------------------
  function drawStatic() {
    ctx.clearRect(0, 0, logicalW, logicalH)
    if (backgroundOpacity > 0) {
      const cx = logicalW / 2
      const cy = logicalH / 2
      const maxR = Math.hypot(cx, cy)
      const grad = ctx.createRadialGradient(cx, cy, maxR * 0.1, cx, cy, maxR * 0.7)
      grad.addColorStop(0, "transparent")
      grad.addColorStop(1, `rgba(0,0,0,${backgroundOpacity})`)
      ctx.fillStyle = grad
      ctx.fillRect(0, 0, logicalW, logicalH)
    }
    const midAlpha = (0.525 * opacity).toFixed(3)
    ctx.fillStyle = `rgba(${color},${midAlpha})`
    for (const d of dots) {
      ctx.beginPath()
      ctx.arc(d.x, d.y, radius, 0, TWO_PI)
      ctx.fill()
    }
  }

  // Animation loop with IntersectionObserver gating -------------------------
  // Throttled to GRAIN_FPS (10fps) so the dot field shares the page's
  // single analog-signal heartbeat with the TV-static grain + globe.
  let raf = 0
  let running = false
  let lastTime = 0

  function loop(ts: number) {
    if (!running) return
    if (ts - lastTime >= GRAIN_FRAME_MS) {
      lastTime = ts
      draw(ts)
    }
    raf = requestAnimationFrame(loop)
  }

  function start() {
    if (running || document.hidden) return
    running = true
    raf = requestAnimationFrame(loop)
  }

  function stop() {
    running = false
    cancelAnimationFrame(raf)
  }

  // Visibility gating via IntersectionObserver ------------------------------
  const visObs = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) start()
        else stop()
      }
    },
    { threshold: 0.1 }
  )
  visObs.observe(container)

  const onDocumentVisibility = () => {
    if (document.hidden) stop()
    else if (!prefersReducedMotion()) start()
  }
  document.addEventListener("visibilitychange", onDocumentVisibility)

  // ResizeObserver -----------------------------------------------------------
  const resizeObs = new ResizeObserver(() => {
    buildGrid()
    if (prefersReducedMotion()) drawStatic()
    else if (!running) start() // restart if visible
  })
  resizeObs.observe(container)

  // Initial build + render ---------------------------------------------------
  buildGrid()

  if (prefersReducedMotion()) {
    drawStatic()
    // No rAF loop — single static frame only.
  } else {
    start()
  }

  // Dispose handle -----------------------------------------------------------
  return () => {
    stop()
    visObs.disconnect()
    resizeObs.disconnect()
    document.removeEventListener("visibilitychange", onDocumentVisibility)
    canvas.remove()
  }
}
