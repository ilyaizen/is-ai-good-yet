<script lang="ts">
  import { onMount } from "svelte";
  import type { PageData } from "./$types";
  import V2Masthead from "$lib/components/v2/shell/v2-masthead.svelte";
  import V2Footer from "$lib/components/v2/shell/v2-footer.svelte";
  import V2PipelineStatus from "$lib/components/v2/shell/v2-pipeline-status.svelte";
  import V2VerdictHero from "$lib/components/v2/hero/v2-verdict-hero.svelte";
  import BotFeedSection from "$lib/components/v2/bot-feed/bot-feed-section.svelte";
  import HnEvidenceSection from "$lib/components/v2/evidence/hn-evidence-section.svelte";
  import V2HistoryChart from "$lib/components/v2/history/v2-history-chart.svelte";
  import V2MethodologySummary from "$lib/components/v2/methodology/v2-methodology-summary.svelte";
  import V2SettingsGui from "$lib/components/v2/settings/v2-settings-gui.svelte";
  import CrtOverlay from "$lib/components/v2/effects/crt-overlay.svelte";
  import {
    applyV2VisualSettings,
    defaultV2Settings,
    parseV2Settings,
    V2_SETTINGS_KEY,
    type V2Settings
  } from "$lib/state/v2-settings.svelte";
  import type { V2StoryCard } from "$lib/types/v2";
  import { V2_DIMENSIONS } from "$lib/types/v2";

  let { data }: { data: PageData } = $props();
  let root = $state<HTMLElement | null>(null);
  let settingsOpen = $state(false);
  let settings = $state<V2Settings>(defaultV2Settings());

  const windowMs = $derived(({ "24h": 86_400_000, "7d": 604_800_000, "30d": 2_592_000_000, "90d": 7_776_000_000, "12m": 31_556_952_000, all: Infinity })[settings.timeWindow]);
  const cutoff = $derived(Date.now() - windowMs);
  const confidence = (story: V2StoryCard): number => {
    const values = V2_DIMENSIONS.filter((dimension) => settings.dimensions[dimension] && story.combined.dimensions[dimension].score !== null).map((dimension) => story.combined.dimensions[dimension].confidence);
    return values.length ? Math.min(...values) : 0;
  };
  const divergence = (story: V2StoryCard): number => Math.max(0, ...V2_DIMENSIONS.map((dimension) => story.sourceDivergence[dimension] ?? 0));
  const polarization = (story: V2StoryCard): number => Math.max(0, ...V2_DIMENSIONS.map((dimension) => story.community?.dimensions[dimension].polarization ?? 0));
  const conflicts = (story: V2StoryCard): boolean => V2_DIMENSIONS.some((dimension) => {
    const article = story.article.dimensions[dimension].score;
    const community = story.community?.dimensions[dimension].score;
    return article !== null && community !== undefined && community !== null && article * community < 0;
  });

  const filteredStories = $derived.by(() => data.stories
    .filter((story) => story.hnTimestamp * 1000 >= cutoff)
    .filter((story) => story.combined.composite === null || (story.combined.composite >= settings.scoreMin && story.combined.composite <= settings.scoreMax))
    .filter((story) => confidence(story) >= settings.confidenceMin)
    .filter((story) => !settings.conflictsOnly || conflicts(story))
    .toSorted((a, b) => settings.sort === "influence" ? b.hnScore - a.hnScore : settings.sort === "divergence" ? divergence(b) - divergence(a) : settings.sort === "polarization" ? polarization(b) - polarization(a) : b.hnTimestamp - a.hnTimestamp));
  const filteredBotFeed = $derived(data.botFeed.filter((item) => new Date(item.postedAt).getTime() >= cutoff).toSorted((a, b) => new Date(b.postedAt).getTime() - new Date(a.postedAt).getTime()));
  const pipelineState = $derived(data.pipeline.currentRun ? "UPDATING" : data.pipeline.lastRun?.status === "failed" ? "DEGRADED" : data.pipeline.lastRun ? "ANALYSIS CURRENT" : "AWAITING V2 DATA");

  function updateSettings(next: V2Settings): void { settings = next; }

  onMount(() => {
    try { settings = parseV2Settings(JSON.parse(localStorage.getItem(V2_SETTINGS_KEY) ?? "null")); }
    catch { settings = defaultV2Settings(); }
    if (root) applyV2VisualSettings(root, settings);
  });

  $effect(() => { if (root) applyV2VisualSettings(root, settings); });
</script>

<svelte:head>
  <title>Is AI Good Yet? AI sentiment from Hacker News</title>
  <meta name="description" content="Article and Hacker News community analysis across AI capability, trajectory, and impact." />
  <meta name="keywords" content="AI sentiment, Hacker News, AI capability, AI trajectory, AI impact" />
  <link rel="canonical" href="https://www.is-ai-good-yet.com/v2" />
</svelte:head>

<a class="v2-skip-link" href="#main-content">Skip to content</a>
<div class="v2-route" bind:this={root}>
  <CrtOverlay />
  <V2Masthead {settingsOpen} onSettings={() => settingsOpen = !settingsOpen} />
  <main id="main-content" inert={settingsOpen ? true : undefined}>
    <V2VerdictHero verdict={data.verdict} {pipelineState} />
    <V2PipelineStatus status={data.pipeline} />
    <BotFeedSection items={filteredBotFeed} showImages={settings.previewImages} />
    <HnEvidenceSection stories={filteredStories} visibleDimensions={settings.dimensions} />
    <V2HistoryChart points={data.history} visibleDimensions={settings.dimensions} />
    <V2MethodologySummary />
  </main>
  <V2Footer />
  <V2SettingsGui open={settingsOpen} {settings} {root} onClose={() => settingsOpen = false} onChange={updateSettings} />
</div>
