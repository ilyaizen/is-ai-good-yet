<script lang="ts">
  import "../app.css"
  import { injectSpeedInsights } from "@vercel/speed-insights/sveltekit"
  import { injectAnalytics } from "@vercel/analytics/sveltekit"
  import favicon from "$lib/assets/favicon.svg"
  import { Canvas } from "@threlte/core"
  import SceneBackground from "$lib/components/scene-background.svelte"
  import AppHeader from "$lib/components/app-header.svelte"
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte"
  import VerdictVeil from "$lib/components/landing/verdict-veil.svelte"
  import { TooltipProvider } from "$lib/components/ui/tooltip"
  import { ModeWatcher, mode } from "mode-watcher"
  import { onMount, setContext } from "svelte"
  import { page } from "$app/state"
  import Scrollbar from "$lib/components/ui/scrollbar.svelte"
  import { initLenis, getLenis, destroyLenis } from "$lib/scroll"
  import Scanlines from "$lib/components/scanlines.svelte"

  let { children } = $props()

  const isV2 = $derived(page.url.pathname.startsWith("/v2"))
  const currentTheme = $derived(mode.current ?? "dark")

  let scrolledPastVerdict = $state(false)
  let showLoader = $state(true)

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

  let scrollY = $state(0)
  let scrollProgress = $state(0)

  setContext("layoutScrollState", {
    get scroll() { return scrollY; },
    setScrolledPastVerdict: (value: boolean) => {
      scrolledPastVerdict = value
    },
  })

  setContext("veilControl", { setVeilState })
  setContext("lenis", { getLenis })

  // Toggle v2 class on body for CSS scoping (glass overrides only on v2)
  $effect(() => {
    if (isV2) {
      document.body.classList.add("v2")
    } else {
      document.body.classList.remove("v2")
    }
    return () => document.body.classList.remove("v2")
  })

  onMount(() => {
    setTimeout(() => { showLoader = false; }, 500)

    if (isV2) {
      // v2: Lenis smooth scroll
      const lenis = initLenis();
      lenis.on("scroll", ({ scroll, progress }: { scroll: number; progress: number }) => {
        scrollY = scroll;
        scrollProgress = progress;
      })
      injectSpeedInsights()
      injectAnalytics()
      return () => { destroyLenis(); }
    } else {
      // v1: native scroll — bridge scroll position to $state for reactive consumers
      const onScroll = () => {
        scrollY = window.scrollY;
        const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        scrollProgress = scrollY / maxScroll;
      };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll(); // init
      injectSpeedInsights()
      injectAnalytics()
      return () => { window.removeEventListener("scroll", onScroll); }
    }
  })
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>Is AI &ldquo;Good&rdquo; Yet?</title>
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

  <!-- 3D Scene Background — only on v2 -->
  {#if isV2}
    <div class="bg-scene" aria-hidden="true">
      <Canvas>
        <SceneBackground
          opacity={0.75}
          maxFps={40}
          maxDpr={1.25}
          theme={currentTheme}
        />
      </Canvas>
    </div>
  {/if}

  <!-- Header: animated on homepage (hidden until scroll), default on other routes -->
  <AppHeader mode="animated" visible={scrolledPastVerdict} />

  <!-- Verdict Veil -->
  {#if veilVisible}
    <VerdictVeil
      onReveal={veilOnReveal ?? (() => {})}
      articleCount={veilArticleCount}
      lastUpdateTimestamp={veilLastUpdateTimestamp}
      resetTrigger={veilResetTrigger}
    />
  {/if}

  <!-- Page content -->
  {@render children()}

  <!-- Custom scrollbar — only on v2 -->
  {#if isV2}
    <Scrollbar progress={scrollProgress} />
  {/if}
</TooltipProvider>

<!-- Scanlines -->
<Scanlines />

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
</style>
