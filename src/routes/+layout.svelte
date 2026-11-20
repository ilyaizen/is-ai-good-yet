<script lang="ts">
  import "../app.css";
  import favicon from "$lib/assets/favicon.svg";
  import AppHeader from "$lib/components/app-header.svelte";
  import BootLoader from "$lib/components/landing/boot-loader.svelte";
  import BootVeil from "$lib/components/landing/boot-veil.svelte";
  import { TooltipProvider } from "$lib/components/ui/tooltip";
  import { ModeWatcher } from "mode-watcher";
  import { onMount, setContext } from "svelte";
  import { page } from "$app/state";
  import Scanlines from "$lib/components/scanlines.svelte";
  import { v12Effects } from "$lib/state/v12-effects.svelte";

  let { children } = $props();

  const isV2 = $derived(page.url.pathname.startsWith("/v2"));
  let scrolledPastVerdict = $state(false);
  let showLoader = $state(true);
  let scrollY = $state(0);

  let veilVisible = $state(false);
  let veilOnReveal: (() => void) | null = $state(null);
  let veilArticleCount = $state(0);
  let veilVerdict = $state<string | null>(null);

  function setVeilState(params: {
    visible: boolean;
    onReveal: () => void;
    articleCount: number;
    resetTrigger: number;
    verdict: string | null;
  }) {
    veilVisible = params.visible;
    veilOnReveal = params.onReveal;
    veilArticleCount = params.articleCount;
    veilVerdict = params.verdict;
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
    document.body.classList.toggle("v12", !isV2);
    return () => {
      document.body.classList.remove("v2");
      document.body.classList.remove("v12");
    };
  });

  onMount(() => {
    v12Effects.init();
    const loaderTimer = window.setTimeout(() => {
      showLoader = false;
    }, 500);
    const onScroll = () => {
      scrollY = window.scrollY;
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

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
  <BootLoader visible={showLoader && !isV2} />
  <AppHeader mode="animated" visible={scrolledPastVerdict} />

  {#if veilVisible}
    <BootVeil
      onReveal={veilOnReveal ?? (() => {})}
      articleCount={veilArticleCount}
      verdict={veilVerdict}
    />
  {/if}

  {@render children()}
</TooltipProvider>

{#if !isV2}
  <Scanlines />
{/if}
