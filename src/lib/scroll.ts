/**
 * Custom easing function matching CSS: cubic-bezier(0, 0.7, 0.1, 1)
 */
export const easeSwift = (x: number): number => {
  if (x <= 0) return 0
  if (x >= 1) return 1

  // Solve for t where x(t) = 0.7t^3 + 0.3t^2 ≈ x using binary search
  // Based on P0=(0,0), P1=(0,0.7), P2=(0.1,1), P3=(1,1)
  let low = 0
  let high = 1
  let t = x

  // 15 iterations gives enough precision for animation
  for (let i = 0; i < 15; i++) {
    t = (low + high) / 2
    const estimatedX = 0.3 * t * t + 0.7 * t * t * t
    if (estimatedX < x) low = t
    else high = t
  }

  // Solve y(t) = 0.1t^3 - 1.2t^2 + 2.1t
  const t2 = t * t
  return 0.1 * t2 * t - 1.2 * t2 + 2.1 * t
}

interface ScrollOptions {
  duration?: number
  onComplete?: () => void
}

/**
 * Scroll to the top of the page with a smooth animation
 */
export const scrollToTop = (options: ScrollOptions = {}) => {
  const { duration = 600, onComplete } = options

  // Guard against server-side execution
  if (typeof window === 'undefined') return

  const start = performance.now()
  const startY = window.scrollY

  const animate = (currentTime: number) => {
    const elapsed = currentTime - start
    const progress = Math.min(elapsed / duration, 1)
    const easedProgress = easeSwift(progress)

    window.scrollTo(0, startY * (1 - easedProgress))

    if (progress < 1) {
      requestAnimationFrame(animate)
    } else {
      if (onComplete) onComplete()
    }
  }

  requestAnimationFrame(animate)
}

/**
 * Scroll to the bottom of the page with a smooth animation
 * Handles dynamic content resizing during scroll
 */
export const scrollToBottom = (options: ScrollOptions = {}) => {
  const { duration = 800, onComplete } = options

  // Guard against server-side execution
  if (typeof window === 'undefined') return

  const start = window.scrollY
  let startTime = 0

  function animate(currentTime: number) {
    if (!startTime) startTime = currentTime
    const timeElapsed = currentTime - startTime

    // Calculate target dynamically to handle layout changes
    // Use Math.max of body and docElement to get true scrollHeight across browsers
    const docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.offsetHeight,
      document.body.clientHeight,
      document.documentElement.clientHeight
    )
    const target = docHeight - window.innerHeight
    const change = target - start

    if (timeElapsed < duration) {
      const progress = timeElapsed / duration
      const ease = easeSwift(progress)
      window.scrollTo(0, start + change * ease)
      requestAnimationFrame(animate)
    } else {
      window.scrollTo(0, start + change)
      if (onComplete) onComplete()
    }
  }
  requestAnimationFrame(animate)
}
