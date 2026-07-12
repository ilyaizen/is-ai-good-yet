<script lang="ts">
  import type { PageData } from "./$types";
  import VerdictDisplay from "$lib/components/landing/verdict-display.svelte";
  import ArticlesTable from "$lib/components/landing/articles-table.svelte";
  import AppFooter from "$lib/components/app-footer.svelte";
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte";
  import DetailsSection from "$lib/components/landing/details-section.svelte";
  import { useVeil } from "$lib/composables/use-veil.svelte";

  let { data }: { data: PageData } = $props();

  const veil = useVeil({
    get articleCount() {
      return data.permanentRecord.totalArticles;
    },
    get lastUpdateTimestamp() {
      return data.lastCatchUpTimestamp;
    }
  });
</script>

<svelte:head>
  <title>Is AI &ldquo;Good&rdquo; Yet?</title>
  <meta
    name="description"
    content="a survey tracking developer sentiment on AI-assisted coding through hacker news posts."
  />
</svelte:head>

<!-- Comprehensive Loader - shows during initial data fetch -->
<ComprehensiveLoader visible={veil.isLoading} />

{#if veil.revealed}
  <main class="main-content">
    <!-- Hero Section: Full-Viewport Verdict Display -->
    <section id="home" class="verdict-hero">
      <div class="verdict-hero__container">
        <VerdictDisplay
          verdict={data.verdictScore.verdict}
          score={data.verdictScore.finalScore}
          weeklySnapshots={data.weeklySnapshots}
          verdictScore={data.verdictScore}
          onReplay={veil.handleReplayScrollToTop}
        />
      </div>
    </section>

    <!-- Content Section: Articles, Details & Footer -->
    <section id="articles" class="content-section" class:content-section--visible={veil.contentVisible}>
      <div id="articles-table" class="scroll-mt-24">
        <ArticlesTable articles={data.topArticles} />
      </div>

      <div id="details" class="scroll-mt-24">
        <DetailsSection visible={veil.contentVisible} />
      </div>

      <AppFooter />
    </section>
  </main>
{/if}

<style>
  .main-content {
    display: flex;
    flex-direction: column;
  }

  .verdict-hero {
    min-height: 100vh;
    min-height: 100dvh;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 1rem;
    box-sizing: border-box;
  }

  .verdict-hero__container {
    width: 100%;
    max-width: 48rem;
  }

  .content-section {
    padding-top: 2rem;
    max-width: 56rem;
    margin: 0 auto;
    width: 100%;
    padding-left: 1rem;
    padding-right: 1rem;
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
