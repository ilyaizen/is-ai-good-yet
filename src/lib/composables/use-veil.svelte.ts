import { onMount } from "svelte"
import { v12Effects } from "$lib/state/v12-effects.svelte"

const STORAGE_KEY = "isAiGoodYetRevealed"

export interface VeilController {
  readonly isLoading: boolean
  readonly revealed: boolean
  readonly showIntro: boolean
  readonly replayKey: number
  handleReveal: () => void
  handleComplete: () => void
  handleReplay: () => void
}

export function useVeil(): VeilController {
  let isLoading = $state(true)
  let revealed = $state(false)
  let showIntro = $state(false)
  let replayKey = $state(0)

  function handleReveal(): void {
    revealed = true
    document.documentElement.classList.remove("v12-veil-pending")
    try {
      localStorage.setItem(STORAGE_KEY, "true")
    } catch {
      // Storage can be blocked; keep the reveal for this mount.
    }
  }

  function handleComplete(): void {
    showIntro = false
    requestAnimationFrame(() => {
      document.getElementById("home")?.focus({ preventScroll: true })
    })
  }

  function handleReplay(): void {
    if (!v12Effects.fx || showIntro) return
    revealed = false
    replayKey += 1
    showIntro = true
    window.scrollTo({ top: 0, behavior: "instant" })
  }

  onMount(() => {
    let returning = false
    try {
      v12Effects.init()
      returning = localStorage.getItem(STORAGE_KEY) === "true"
    } catch {
      // Usable with session-only state when storage is restricted.
    }
    showIntro = v12Effects.fx && !returning
    if (!showIntro) {
      handleReveal()
    }
    isLoading = false
  })

  return {
    get isLoading() {
      return isLoading
    },
    get revealed() {
      return revealed
    },
    get showIntro() {
      return showIntro
    },
    get replayKey() {
      return replayKey
    },
    handleReveal,
    handleComplete,
    handleReplay,
  }
}
