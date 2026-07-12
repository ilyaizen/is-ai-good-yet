<script lang="ts">
  import type { PageData } from "./$types";
  import ComprehensiveLoader from "$lib/components/landing/comprehensive-loader.svelte";
  import V2VerdictHero from "$lib/components/v2/v2-verdict-hero.svelte";
  import V2Metrics from "$lib/components/v2/v2-metrics.svelte";
  import V2SentimentChart from "$lib/components/v2/v2-sentiment-chart.svelte";
  import V2Discussions from "$lib/components/v2/v2-discussions.svelte";
  import V2AnalysisDetails from "$lib/components/v2/v2-analysis-details.svelte";
  import V2FooterBar from "$lib/components/v2/v2-footer-bar.svelte";
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
  <title>Is AI &ldquo;Good&rdquo; Yet? — Sentiment Terminal</title>
  <meta name="description" content="A dense Hacker News AI coding sentiment dashboard built from the current static analysis record." />
</svelte:head>

<ComprehensiveLoader visible={veil.isLoading} />

{#if veil.revealed}
  <main id="main-content" class="v2-shell" class:v2-shell--visible={veil.contentVisible}>
    <header class="v2-masthead">
      <a class="v2-brand" href="/v2">is-ai-good-yet.com <span>█</span></a>
      <p>HACKER NEWS AI SENTIMENT TERMINAL</p>
      <nav aria-label="V2 sections"><a href="#home">HOME</a><a href="#sentiment">HISTORY</a><a href="#methodology">METHODOLOGY</a></nav>
    </header>

    <div id="home"><V2VerdictHero verdict={data.verdictScore} /></div>
    <V2Metrics verdict={data.verdictScore} />
    <div id="sentiment"><V2SentimentChart snapshots={data.weeklySnapshots} /></div>
    <V2Discussions articles={data.topArticles} />
    <V2AnalysisDetails stats={data.pipelineStats} articleCount={data.permanentRecord.totalArticles} lastUpdate={data.lastCatchUpTimeAgo} />
    <V2FooterBar onReplay={veil.handleReplayScrollToTop} />
    <p class="v2-colophon">IS AI “GOOD” YET? / CURRENT STATIC RECORD / BUILT FOR SCRUTINY</p>
  </main>
{/if}
