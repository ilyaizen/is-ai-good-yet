<script lang="ts">
  import type { PageData } from "./$types"
  import VerdictDisplay from "$lib/components/landing/verdict-display.svelte"
  import ArticlesTable from "$lib/components/landing/articles-table.svelte"
  import AppFooter from "$lib/components/app-footer.svelte"
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte"
  import { onMount, getContext } from "svelte"
  import DetailsSection from "$lib/components/landing/details-section.svelte"

  let { data }: { data: PageData } = $props()

  // Get context from layout to control header visibility
  const layoutScrollState = getContext<{
    scroll: number
    setScrolledPastVerdict: (value: boolean) => void
  }>("layoutScrollState")

  // Get veil control from layout
  const veilControl = getContext<{
    setVeilState: (params: {
      visible: boolean
      onReveal: () => void
      articleCount: number
      lastUpdateTimestamp: number | null
      resetTrigger: number
    }) => void
  }>("veilControl")

  // Local state
  let isLoading = $state(true)
  let revealed = $state(false)
  let contentVisible = $state(false)
  let veilResetTrigger = $state(0)
  const LOADER_FADE_DELAY_MS = 100
  const STORAGE_KEY = "isAiGoodYetRevealed"

  function resetToVeil() {
    revealed = false
    contentVisible = false
  }

  function handleReveal() {
    revealed = true
    // Persist reveal state across sessions
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
    // Clear persisted state so veil shows again
    if (typeof localStorage !== "undefined") {
      localStorage.removeItem(STORAGE_KEY)
    }
    veilResetTrigger++
  }

  onMount(() => {
    // Check if user has already revealed in a previous session
    if (typeof localStorage !== "undefined") {
      const hasRevealed = localStorage.getItem(STORAGE_KEY)
      if (hasRevealed === "true") {
        revealed = true
        contentVisible = true
      }
    }

    // Simulate initial loading delay (remove in production if data loads instantly)
    setTimeout(() => {
      isLoading = false
    }, LOADER_FADE_DELAY_MS)

    // Scroll-driven header visibility via smooth scroll context
    $effect(() => {
      if (revealed) {
        const scrolledPast = layoutScrollState.scroll > window.innerHeight * 0.5
        layoutScrollState.setScrolledPastVerdict(scrolledPast)
      } else {
        layoutScrollState.setScrolledPastVerdict(false)
      }
    })
  })

  // Sync veil visibility state with layout
  $effect(() => {
    if (!isLoading) {
      veilControl.setVeilState({
        visible: !revealed,
        onReveal: handleReveal,
        articleCount: data.permanentRecord.totalArticles,
        lastUpdateTimestamp: data.lastCatchUpTimestamp,
        resetTrigger: veilResetTrigger,
      })
    }
  })
</script>

<svelte:head>
  <title>Is AI "Good" Yet?</title>
  <meta
    name="description"
    content="a survey tracking developer sentiment on AI-assisted coding through hacker news posts."
  />
</svelte:head>

<!-- Comprehensive Loader - shows during initial data fetch -->
<ComprehensiveLoader visible={isLoading} />

{#if revealed}
  <main class="main-content">
    <!-- Hero Section: Full-Viewport Verdict Display -->
    <section id="home" class="verdict-hero">
      <div class="verdict-hero__container">
        <VerdictDisplay
          verdict={data.verdictScore.verdict}
          score={data.verdictScore.finalScore}
          weeklySnapshots={data.weeklySnapshots}
          verdictScore={data.verdictScore}
          onReplay={handleReplay}
        />
      </div>
    </section>

    <!-- Content Section: Articles Table & Footer -->
    <section id="articles" class="content-section" class:content-section--visible={contentVisible}>
      <div id="details" class="scroll-mt-24">
        <DetailsSection visible={contentVisible} />
      </div>

      <div id="articles-table" class="scroll-mt-24">
        <ArticlesTable articles={data.topArticles} />
      </div>
    </section>
  </main>
{/if}

<style>
  .main-content {
    display: flex;
    flex-direction: column;
  }

  /* Hero: Full viewport, centered verdict display */
  .verdict-hero {
    min-height: 100vh;
    min-height: 100dvh; /* Dynamic viewport height for mobile */
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 1rem; /* No vertical padding - let flexbox center perfectly */
    box-sizing: border-box;
  }

  .verdict-hero__container {
    width: 100%;
    max-width: 48rem; /* max-w-2xl */
  }

  /* Content Section: Fade + slide up animation */
  .content-section {
    padding-top: 2rem;
    max-width: 56rem; /* max-w-4xl - slightly wider for articles table */
    margin: 0 auto;
    width: 100%;
    padding-left: 1rem;
    padding-right: 1rem;

    /* Initial hidden state */
    opacity: 0;
    transform: translateY(24px);
    transition:
      opacity 500ms var(--ease-swift),
      transform 500ms var(--ease-swift);
  }

  .content-section--visible {
    opacity: 1;
    transform: translateY(0);
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .verdict-hero {
      min-height: calc(100vh - 4rem);
      padding: 1rem;
    }

    .content-section {
      padding-left: 0.75rem;
      padding-right: 0.75rem;
    }
  }
</style>