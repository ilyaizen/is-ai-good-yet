/**
 * Custom easing function matching CSS: cubic-bezier(0, 0.7, 0.1, 1)
 */
export const easeSwift = (x: number): number => {
  if (x <= 0) return 0
  if (x >= 1) return 1
  let low = 0
  let high = 1
  let t = x
  for (let i = 0; i < 15; i++) {
    t = (low + high) / 2
    const estimatedX = 0.3 * t * t + 0.7 * t * t * t
    if (estimatedX < x) low = t
    else high = t
  }
  const t2 = t * t
  return 0.1 * t2 * t - 1.2 * t2 + 2.1 * t
}

// Module-level reference to the smooth scroll instance,
// set once by the layout during initialization.
let smoothScrollInstance: { scrollTo: (y: number) => void; scroll: number } | null = null

export function setSmoothScroll(instance: { scrollTo: (y: number) => void; scroll: number }) {
  smoothScrollInstance = instance
}

function getSs() {
  if (!smoothScrollInstance) {
    console.warn("[scroll] smooth scroll not initialized, using noop")
    return { scrollTo: () => {}, scroll: 0 }
  }
  return smoothScrollInstance
}

/**
 * Scroll to the top of the page with a smooth animation
 */
export const scrollToTop = (options: { duration?: number; onComplete?: () => void } = {}) => {
  const ss = getSs()
  ss.scrollTo(0)
  // We use direct scrollTo for instant feedback.
  // Duration-based animation is handled by the smooth scroll lerp.
  if (options.onComplete) requestAnimationFrame(options.onComplete)
}

/**
 * Scroll to the bottom of the page with a smooth animation
 */
export const scrollToBottom = (options: { duration?: number; onComplete?: () => void } = {}) => {
  if (typeof document === "undefined") return
  const docHeight = Math.max(
    document.body.scrollHeight,
    document.documentElement.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.offsetHeight,
    document.body.clientHeight,
    document.documentElement.clientHeight
  )
  const target = docHeight - window.innerHeight
  const ss = getSs()
  ss.scrollTo(target)
  if (options.onComplete) requestAnimationFrame(options.onComplete)
}

/**
 * Smooth scroll an element into view using the smooth scroll engine
 */
export function scrollToElement(el: HTMLElement) {
  if (typeof document === "undefined") return
  const top = el.getBoundingClientRect().top
  // top is relative to viewport. scroll offset = current scroll + top.
  const ss = getSs()
  ss.scrollTo(ss.scroll + top)
}