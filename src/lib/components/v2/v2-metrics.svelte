<script lang="ts">
  interface VerdictData {
    totalAnalyzed: number;
    positiveCount: number;
    neutralCount: number;
    negativeCount: number;
    finalScore: number;
    momentum: number;
    momentumLabel: "improving" | "stable" | "declining";
  }

  let { verdict }: { verdict: VerdictData } = $props();
  const percent = (value: number) => (verdict.totalAnalyzed ? (value / verdict.totalAnalyzed) * 100 : 0);
  const metrics = $derived([
    { label: "Articles analyzed", value: verdict.totalAnalyzed.toLocaleString("en-US"), tone: "up", spark: "2,21 12,17 22,19 32,10 42,13 52,5 62,8" },
    { label: "Positive", value: `${percent(verdict.positiveCount).toFixed(1)}%`, tone: "up", spark: "2,22 12,19 22,20 32,14 42,11 52,8 62,5" },
    { label: "Neutral", value: `${percent(verdict.neutralCount).toFixed(1)}%`, tone: "flat", spark: "2,14 12,12 22,15 32,13 42,14 52,12 62,13" },
    { label: "Negative", value: `${percent(verdict.negativeCount).toFixed(1)}%`, tone: "down", spark: "2,5 12,9 22,8 32,14 42,12 52,18 62,21" },
    { label: "Verdict score", value: verdict.finalScore.toFixed(1), tone: verdict.momentumLabel === "declining" ? "down" : "up", spark: "2,20 12,16 22,18 32,12 42,14 52,7 62,9" }
  ]);
</script>

<section aria-labelledby="metrics-title">
  <div class="v2-section-label"><span id="metrics-title">KEY METRICS</span><span>LIVE STATIC EXPORT</span></div>
  <div class="v2-metrics">
    {#each metrics as metric, index}
      <article class="v2-metric" data-tone={metric.tone} style={`--delay:${index * 55}ms`}>
        <div class="v2-metric__top"><span>{index === 0 ? "▤" : index === 4 ? "〽" : metric.tone === "down" ? "↓" : metric.tone === "flat" ? "—" : "↑"}</span>
          <svg viewBox="0 0 64 26" aria-hidden="true"><polyline points={metric.spark}></polyline></svg>
        </div>
        <strong>{metric.value}</strong>
        <span>{metric.label}</span>
      </article>
    {/each}
  </div>
</section>
