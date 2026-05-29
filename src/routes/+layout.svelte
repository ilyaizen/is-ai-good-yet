<script lang="ts">
  import "../app.css"
  import { injectSpeedInsights } from "@vercel/speed-insights/sveltekit"
  import { injectAnalytics } from "@vercel/analytics/sveltekit"
  import favicon from "$lib/assets/favicon.svg"
  import { Canvas } from "@threlte/core"
  import SceneBackground from "$lib/components/scene-background.svelte"
  import AppHeader from "$lib/components/app-header.svelte"
  import AppFooter from "$lib/components/app-footer.svelte"
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte"
  import VerdictVeil from "$lib/components/landing/verdict-veil.svelte"
  import { TooltipProvider } from "$lib/components/ui/tooltip"
  import { ModeWatcher, mode } from "mode-watcher"
  import { onMount, setContext } from "svelte"
  import { page } from "$app/state"
  import { useSmoothScroll } from "$lib/composables/use-smooth-scroll.svelte"
  import Scrollbar from "$lib/components/ui/scrollbar.svelte"
  import { setSmoothScroll } from "$lib/scroll"

  let { children } = $props()

  // Homepage uses animated header mode
  const isHomepage = $derived(page.url.pathname === "/")

  const currentTheme = $derived(mode.current ?? "dark")

  // Shared state for homepage scroll position (reactive for header visibility)
  let scrolledPastVerdict = $state(false)

  // Loader visibility state
  let showLoader = $state(true)

  // Verdict veil state — controlled by the homepage page via context
  let veilVisible = $state(false)
  let veilOnReveal: (() => void) | null = $state(null)
  let veilArticleCount = $state(0)
  let veilLastUpdateTimestamp = $state<number | null>(null)
  let veilResetTrigger = $state(0)

  function setVeilState(params: {
    visible: boolean
    onReveal: () => void
    articleCount: number
    lastUpdateTimestamp: number | null
    resetTrigger: number
  }) {
    veilVisible = params.visible
    veilOnReveal = params.onReveal
    veilArticleCount = params.articleCount
    veilLastUpdateTimestamp = params.lastUpdateTimestamp
    veilResetTrigger = params.resetTrigger
  }

  // Smooth scroll setup
  const ss = useSmoothScroll()

  // Expose scroll state and setter for homepage to use
  setContext("layoutScrollState", {
    get scroll() { return ss.scroll; },
    setScrolledPastVerdict: (value: boolean) => {
      scrolledPastVerdict = value
    },
  })

  // Expose veil control for homepage
  setContext("veilControl", { setVeilState })

  // Also expose the smooth scroll instance directly
  setContext("smoothScroll", ss)

  onMount(() => {
    // Hide loader after 0.5 seconds
    setTimeout(() => {
      showLoader = false
    }, 500)

    // Init smooth scroll
    const cleanup = ss.init()
    setSmoothScroll(ss)

    // Prevent native scroll — we handle it
    document.documentElement.style.overflow = "hidden"
    document.body.style.overflow = "hidden"

    // Inject Vercel analytics and speed insights
    injectSpeedInsights()
    injectAnalytics()

    return () => {
      cleanup?.()
    }
  })
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>Is AI "Good" Yet?</title>
  <meta name="description" content="A survey website that analyzes Hacker News sentiment toward AI coding." />
  <meta name="keywords" content="AI coding assistants, developer sentiment, Hacker News analysis, is ai good yet" />
  <meta name="author" content="Ilya Aizenberg" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="https://www.is-ai-good-yet.com" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://www.is-ai-good-yet.com" />
  <meta property="og:title" content="Is AI &ldquo;Good&rdquo; Yet?" />
  <meta property="og:description" content="A survey tracking developer sentiment on AI-assisted coding through HN posts." />
  <meta property="og:image" content="https://www.is-ai-good-yet.com/og-image.png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:locale" content="en_US" />
  <meta property="og:site_name" content="Is AI &ldquo;Good&rdquo; Yet?" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content="https://www.is-ai-good-yet.com" />
  <meta name="twitter:title" content="Is AI &ldquo;Good&rdquo; Yet?" />
  <meta name="twitter:description" content="A survey tracking developer sentiment on AI-assisted coding through HN posts." />
  <meta name="twitter:image" content="https://www.is-ai-good-yet.com/og-image.png" />
  <meta name="twitter:creator" content="@ilyaizen" />
</svelte:head>

<ModeWatcher defaultMode="dark" />

<TooltipProvider>
  <ComprehensiveLoader visible={showLoader} />

  <!-- 3D Scene Background -->
  <div class="bg-scene" aria-hidden="true">
    <Canvas>
      <SceneBackground
        opacity={0.75}
        maxFps={60}
        maxDpr={1.5}
        theme={currentTheme}
      />
    </Canvas>
  </div>

  {#if isHomepage}
    <AppHeader mode="animated" visible={scrolledPastVerdict} />
  {:else}
    <AppHeader mode="default" />
  {/if}

  <!-- Verdict Veil — rendered outside smooth-scroll so fixed positioning works -->
  {#if veilVisible && isHomepage}
    <VerdictVeil
      onReveal={veilOnReveal ?? (() => {})}
      articleCount={veilArticleCount}
      lastUpdateTimestamp={veilLastUpdateTimestamp}
      resetTrigger={veilResetTrigger}
    />
  {/if}

  <!-- Smooth scroll wrapper — all page content translate3d'd inside -->
  <div id="smooth-scroll">
    {@render children()}

    {#if !isHomepage}
      <AppFooter />
    {/if}
  </div>

  <!-- Custom scrollbar -->
  <Scrollbar progress={ss.progress} />
</TooltipProvider>

<style>
  .bg-scene {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -3;
    pointer-events: none;
  }

  #smooth-scroll {
    will-change: transform;
  }
</style>