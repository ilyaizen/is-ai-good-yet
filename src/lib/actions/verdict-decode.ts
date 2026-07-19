const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%@&"

interface DecodeOptions {
  duration?: number
  delay?: number
  onDone?: () => void
}

export function verdictDecode(node: HTMLElement, finalText: string, options: DecodeOptions = {}): () => void {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  if (reduced) {
    node.textContent = finalText
    options.onDone?.()
    return () => undefined
  }

  const chars = Array.from(finalText)
  const duration = options.duration ?? 900
  let frame = 0
  let timer = 0
  let cancelled = false
  timer = window.setTimeout(() => {
    let started = 0
    const tick = (now: number) => {
      if (cancelled) return
      if (!started) started = now
      const progress = Math.min(1, (now - started) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      const locked = Math.floor(eased * chars.length)
      node.textContent = chars
        .map((character, index) => {
          if (character === " " || index < locked) return character
          return GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
        })
        .join("")
      if (progress < 1) frame = requestAnimationFrame(tick)
      else {
        node.textContent = finalText
        options.onDone?.()
      }
    }
    frame = requestAnimationFrame(tick)
  }, options.delay ?? 0)

  return () => {
    cancelled = true
    window.clearTimeout(timer)
    cancelAnimationFrame(frame)
    node.textContent = finalText
  }
}
