export function scrollTo(y: number) {
  window.scrollTo({ top: y })
}

export function scrollToTop(options: { onComplete?: () => void } = {}) {
  window.scrollTo({ top: 0 })
  options.onComplete?.()
}

export function scrollToBottom(options: { onComplete?: () => void; duration?: number } = {}) {
  const docHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
  window.scrollTo({ top: docHeight - window.innerHeight })
  options.onComplete?.()
}

export function scrollToElement(el: HTMLElement) {
  el.scrollIntoView()
}

export function scrollToId(id: string) {
  if (typeof document === "undefined") return
  const hash = id.includes("#") ? id.slice(id.indexOf("#") + 1) : id
  document.getElementById(hash.replace(/^#/, ""))?.scrollIntoView()
}

export function handleAnchorClick(e: MouseEvent, href: string) {
  if (typeof window === "undefined") return
  const target = new URL(href, window.location.href)
  if (!target.hash || target.pathname !== window.location.pathname) return
  e.preventDefault()
  scrollToId(target.hash)
}
