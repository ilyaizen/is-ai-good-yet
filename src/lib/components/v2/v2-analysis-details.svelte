<script lang="ts">
  interface PipelineStats { totalUrls: number; scraped: number; relevant: number; analyzed: number; failed: number; }
  let { stats, articleCount, lastUpdate }: { stats: PipelineStats; articleCount: number; lastUpdate: string | null } = $props();
  const cells = $derived([
    ["TIME WINDOW", "ROLLING 6 MONTHS", lastUpdate ?? "static export"],
    ["SOURCE", "HACKER NEWS", "AI coding discourse"],
    ["ARTICLES ANALYZED", articleCount.toLocaleString("en-US"), `${stats.relevant.toLocaleString("en-US")} relevant records`],
    ["PIPELINE", "STATIC V1 CONTRACT", `${stats.scraped.toLocaleString("en-US")} pages scraped`],
    ["STATUS", stats.failed === 0 ? "READY" : "PARTIAL", `${stats.failed} failed records`]
  ]);
</script>

<section id="methodology" class="v2-panel" aria-labelledby="analysis-title">
  <header class="v2-panel__header"><h2 id="analysis-title">⚙ ANALYSIS DETAILS</h2><span>NO V2 SENTIMENT CONTRACT WIRED</span></header>
  <div class="v2-analysis">
    {#each cells as cell}
      <div><span>{cell[0]}</span><strong>{cell[1]}</strong><small>{cell[2]}</small></div>
    {/each}
  </div>
</section>
