<script lang="ts">
  import { goto } from "$app/navigation"
  import { page } from "$app/state"
  import { setContext } from "svelte"
  import PageTransitionCurtain from "$lib/components/lab/page-transition-curtain.svelte"
  import type { LabTransitionCard } from "$lib/lab/transition-data"

  interface Props {
    children: import("svelte").Snippet
    data: {
      cards: LabTransitionCard[]
    }
  }

  let { children, data }: Props = $props()

  const toneAccent: Record<LabTransitionCard["tone"], string> = {
    positive: "#55d6a3",
    negative: "#ff6b6b",
    neutral: "#7dd3fc",
  }

  const transition = {
    navigate: async (card: LabTransitionCard) => {
      if (busy) return
      busy = true
      active = true
      poster = card.poster
      accent = toneAccent[card.tone]
      title = card.title
      phase = "out"

      try {
        await animate(0, 1, 340)
        await goto(card.href, { keepFocus: true, noScroll: true })
        phase = "in"
        await animate(1, 0, 340)
      } finally {
        active = false
        busy = false
        progress = 0
      }
    },
    get busy() {
      return busy
    },
  }

  let active = $state(false)
  let busy = $state(false)
  let progress = $state(0)
  let poster = $state("")
  let accent = $state("#7dd3fc")
  let title = $state("")
  let phase = $state<"out" | "in">("out")

  let raf = 0

  function easeOutCubic(value: number) {
    return 1 - Math.pow(1 - value, 3)
  }

  function animate(from: number, to: number, duration: number) {
    cancelAnimationFrame(raf)
    const start = performance.now()

    return new Promise<void>((resolve) => {
      const frame = (now: number) => {
        const raw = Math.min(1, Math.max(0, (now - start) / duration))
        const eased = easeOutCubic(raw)
        progress = from + (to - from) * eased

        if (raw < 1) {
          raf = requestAnimationFrame(frame)
          return
        }

        progress = to
        resolve()
      }

      raf = requestAnimationFrame(frame)
    })
  }

  setContext("labTransition", transition)

  $effect(() => {
    const first = data.cards[0]
    if (!poster && first) {
      poster = first.poster
      title = first.title
      accent = first.accent
    }
  })

  const isLabRoute = $derived(page.url.pathname.startsWith("/lab/threejs-page-transition"))

  $effect(() => {
    if (isLabRoute) {
      document.body.classList.add("lab-transition")
      return () => {
        document.body.classList.remove("lab-transition")
      }
    }

    document.body.classList.remove("lab-transition")
    return () => {
      document.body.classList.remove("lab-transition")
    }
  })
</script>

<svelte:head>
  <title>Three.js page transition lab</title>
  <meta
    name="description"
    content="A SvelteKit port of a Three.js page transition experiment, built as a route-local lab."
  />
</svelte:head>

<div class="lab-shell">
  <div class="lab-shell__topbar">
    <a href="/" class="lab-shell__link">← home</a>
    <a href="/lab/threejs-page-transition" class="lab-shell__link">overview</a>
    <span class="lab-shell__status">{busy ? "transitioning" : "idle"}</span>
  </div>

  <div class="lab-shell__content">
    {@render children()}
  </div>
</div>

<PageTransitionCurtain
  active={active}
  progress={progress}
  poster={poster}
  accent={accent}
  title={title}
  phase={phase}
/>

<style>
  .lab-shell {
    min-height: 100vh;
    padding: 1rem 1rem 3rem;
  }

  .lab-shell__topbar {
    width: min(1160px, 100%);
    margin: 0 auto 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.9rem;
    justify-content: space-between;
    align-items: center;
    border: 1px solid oklch(from var(--border) l c h / 0.75);
    border-radius: 999px;
    padding: 0.8rem 1rem;
    background: oklch(from var(--card) l c h / 0.76);
    backdrop-filter: blur(12px);
  }

  .lab-shell__link,
  .lab-shell__status {
    font-family: var(--font-mono);
    font-size: 0.76rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .lab-shell__status {
    color: var(--color-text-secondary);
  }

  .lab-shell__content {
    width: min(1160px, 100%);
    margin: 0 auto;
  }

  @media (max-width: 640px) {
    .lab-shell {
      padding-inline: 0.75rem;
    }

    .lab-shell__topbar {
      border-radius: 1.1rem;
    }
  }
</style>
