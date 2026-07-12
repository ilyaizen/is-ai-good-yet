<script lang="ts">
  import "../app.css";
  import { injectSpeedInsights } from "@vercel/speed-insights/sveltekit";
  import { injectAnalytics } from "@vercel/analytics/sveltekit";
  import favicon from "$lib/assets/favicon.svg";
  import AppHeader from "$lib/components/app-header.svelte";
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte";
  import VerdictVeil from "$lib/components/landing/verdict-veil.svelte";
  import V2VerdictVeil from "$lib/components/v2/v2-verdict-veil.svelte";
  import { TooltipProvider } from "$lib/components/ui/tooltip";
  import { ModeWatcher } from "mode-watcher";
  import { onMount, setContext } from "svelte";
  import { page } from "$app/state";
  import Scanlines from "$lib/components/scanlines.svelte";

  let { children } = $props();

  const isV2 = $derived(page.url.pathname.startsWith("/v2"));
  let scrolledPastVerdict = $state(false);
  let showLoader = $state(true);
  let scrollY = $state(0);

  let veilVisible = $state(false);
  let veilOnReveal: (() => void) | null = $state(null);
  let veilArticleCount = $state(0);
  let veilLastUpdateTimestamp = $state<number | null>(null);
  let veilResetTrigger = $state(0);

  function setVeilState(params: {
    visible: boolean;
    onReveal: () => void;
    articleCount: number;
    lastUpdateTimestamp: number | null;
    resetTrigger: number;
  }) {
    veilVisible = params.visible;
    veilOnReveal = params.onReveal;
    veilArticleCount = params.articleCount;
    veilLastUpdateTimestamp = params.lastUpdateTimestamp;
    veilResetTrigger = params.resetTrigger;
  }

  setContext("layoutScrollState", {
    get scroll() {
      return scrollY;
    },
    setScrolledPastVerdict: (value: boolean) => {
      scrolledPastVerdict = value;
    }
  });
  setContext("veilControl", { setVeilState });

  $effect(() => {
    document.body.classList.toggle("v2", isV2);
    return () => document.body.classList.remove("v2");
  });

  onMount(() => {
    const loaderTimer = window.setTimeout(() => {
      showLoader = false;
    }, 500);
    const onScroll = () => {
      scrollY = window.scrollY;
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    injectSpeedInsights();
    injectAnalytics();

    return () => {
      window.clearTimeout(loaderTimer);
      window.removeEventListener("scroll", onScroll);
    };
  });
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
  <AppHeader mode="animated" visible={scrolledPastVerdict} />

  {#if veilVisible}
    {#if isV2}
      <V2VerdictVeil
        onReveal={veilOnReveal ?? (() => {})}
        articleCount={veilArticleCount}
        lastUpdateTimestamp={veilLastUpdateTimestamp}
        resetTrigger={veilResetTrigger}
      />
    {:else}
      <VerdictVeil
        onReveal={veilOnReveal ?? (() => {})}
        articleCount={veilArticleCount}
        lastUpdateTimestamp={veilLastUpdateTimestamp}
        resetTrigger={veilResetTrigger}
      />
    {/if}
  {/if}

  {@render children()}
</TooltipProvider>

{#if !isV2}
  <Scanlines />
{/if}
