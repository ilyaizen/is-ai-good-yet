<script lang="ts">
  import "../app.css"
  import { injectSpeedInsights } from "@vercel/speed-insights/sveltekit"
  import { injectAnalytics } from "@vercel/analytics/sveltekit"
  import favicon from "$lib/assets/favicon.svg"
  import BackgroundEffects from "$lib/components/background-effects.svelte"
  import AppHeader from "$lib/components/app-header.svelte"
  import AppFooter from "$lib/components/app-footer.svelte"
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte"
  import { TooltipProvider } from "$lib/components/ui/tooltip"
  import { ModeWatcher } from "mode-watcher"
  import { onMount, setContext } from "svelte"
  import { page } from "$app/state"

  let { children } = $props()

  // Homepage uses animated header mode
  const isHomepage = $derived(page.url.pathname === "/")

  // Shared state for homepage scroll position (reactive for header visibility)
  let scrolledPastVerdict = $state(false)

  // Loader visibility state
  let showLoader = $state(true)

  // Expose scroll state setter for homepage to use
  setContext("layoutScrollState", {
    setScrolledPastVerdict: (value: boolean) => {
      scrolledPastVerdict = value
    },
  })

  onMount(() => {
    // Hide loader after 0.5 seconds to simulate loading
    setTimeout(() => {
      showLoader = false
    }, 500)

    // Inject Vercel analytics and speed insights
    injectSpeedInsights()
    injectAnalytics()
  })

  // SEO constants
  const SITE_TITLE = "Is AI “Good” Yet?"
  const SITE_DESCRIPTION = "A survey website that analyzes Hacker News sentiment toward AI coding."
  const SITE_URL = "https://www.is-ai-good-yet.com"
  const SITE_IMAGE = `${SITE_URL}/og-image.png`
  const AUTHOR = "Ilya Aizenberg"
  const KEYWORDS = [
    "AI coding assistants",
    "developer sentiment",
    "Hacker News analysis",
    "GitHub Copilot",
    "Cursor AI",
    "LLM coding",
    "software engineering trends",
    "AI productivity",
    "AI skepticism",
    "AI-assisted coding",
    "coding automation",
    "AI agents",
    "local LLMs",
    "software development",
    "data journalism",
    "sentiment analysis",
    "is ai good yet",
    "is-ai-good-yet",
    "dev tools",
    "coding trends 2024",
    "coding trends 2025",
    "coding trends 2026",
  ]
</script>

<svelte:head>
  <!-- Favicon -->
  <link rel="icon" href={favicon} />

  <!-- Basic Meta Tags -->
  <title>{SITE_TITLE}</title>
  <meta name="description" content={SITE_DESCRIPTION} />
  <meta name="keywords" content={KEYWORDS.join(", ")} />
  <meta name="author" content={AUTHOR} />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href={SITE_URL} />

  <!-- Open Graph / Facebook -->
  <meta property="og:type" content="website" />
  <meta property="og:url" content={SITE_URL} />
  <meta property="og:title" content={SITE_TITLE} />
  <meta property="og:description" content={SITE_DESCRIPTION} />
  <meta property="og:image" content={SITE_IMAGE} />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:locale" content="en_US" />
  <meta property="og:site_name" content="Is AI “Good” Yet?" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content={SITE_URL} />
  <meta name="twitter:title" content={SITE_TITLE} />
  <meta name="twitter:description" content={SITE_DESCRIPTION} />
  <meta name="twitter:image" content={SITE_IMAGE} />
  <meta name="twitter:creator" content="@ilyaizen" />
</svelte:head>

<ModeWatcher defaultMode="dark" />

<TooltipProvider>
  <ComprehensiveLoader visible={showLoader} />

  <BackgroundEffects />

  {#if isHomepage}
    <!-- Homepage: animated header that slides in after scroll -->
    <AppHeader mode="animated" visible={scrolledPastVerdict} />
  {:else}
    <!-- Other pages: standard sticky header -->
    <AppHeader mode="default" />
  {/if}

  {@render children()}

  {#if !isHomepage}
    <AppFooter />
  {/if}
</TooltipProvider>
