import { onMount, getContext } from "svelte"

const STORAGE_KEY = "isAiGoodYetRevealed"
const LOADER_FADE_DELAY_MS = 100

type VeilControl = {
  setVeilState: (params: {
    visible: boolean
    onReveal: () => void
    articleCount: number
    lastUpdateTimestamp: number | null
    resetTrigger: number
  }) => void
}

type LayoutScrollState = {
  scroll: number
  setScrolledPastVerdict: (value: boolean) => void
}

/**
 * Shared veil state machine for landing pages.
 * Manages the reveal/replay lifecycle, localStorage persistence,
 * and sync with the layout-level veil control + scroll-driven header visibility.
 */
export function useVeil(params: { articleCount: number; lastUpdateTimestamp: number | null }) {
  const layoutScrollState = getContext<LayoutScrollState>("layoutScrollState")
  const veilControl = getContext<VeilControl>("veilControl")

  let isLoading = $state(true)
  let revealed = $state(false)
  let contentVisible = $state(false)
  let veilResetTrigger = $state(0)

  function resetToVeil() {
    revealed = false
    contentVisible = false
  }

  function handleReveal() {
    revealed = true
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(STORAGE_KEY, "true")
    }
    setTimeout(() => {
      contentVisible = true
    }, 300)
  }

  function handleReplay() {
    revealed = false
    contentVisible = false
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(STORAGE_KEY)
    }
    veilResetTrigger++
  }

  function handleReplayScrollToTop() {
    handleReplay()
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0 })
    }
  }

  // Scroll-driven header visibility
  $effect(() => {
    if (!revealed) {
      layoutScrollState.setScrolledPastVerdict(false)
      return
    }
    const scrolledPast = layoutScrollState.scroll > window.innerHeight * 0.5
    layoutScrollState.setScrolledPastVerdict(scrolledPast)
  })

  // Sync veil visibility state with layout
  $effect(() => {
    if (!isLoading) {
      veilControl.setVeilState({
        visible: !revealed,
        onReveal: handleReveal,
        articleCount: params.articleCount,
        lastUpdateTimestamp: params.lastUpdateTimestamp,
        resetTrigger: veilResetTrigger,
      })
    }
  })

  onMount(() => {
    if (typeof localStorage !== "undefined") {
      const hasRevealed = localStorage.getItem(STORAGE_KEY)
      if (hasRevealed === "true") {
        revealed = true
        contentVisible = true
      }
    }

    setTimeout(() => {
      isLoading = false
    }, LOADER_FADE_DELAY_MS)
  })

  return {
    get isLoading() {
      return isLoading
    },
    get revealed() {
      return revealed
    },
    get contentVisible() {
      return contentVisible
    },
    handleReveal,
    handleReplay,
    handleReplayScrollToTop,
    resetToVeil,
  }
}
