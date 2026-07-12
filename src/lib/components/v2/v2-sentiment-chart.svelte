<script lang="ts">
  interface Snapshot {
    weekStart: string;
    verdictScore: number;
  }

  let { snapshots }: { snapshots: Snapshot[] } = $props();
  let range = $state<"12W" | "26W" | "ALL">("26W");
  const visible = $derived(range === "ALL" ? snapshots : snapshots.slice(range === "12W" ? -12 : -26));
  const points = $derived.by(() => {
    if (!visible.length) return "";
    return visible.map((point, index) => `${(index / Math.max(1, visible.length - 1)) * 900},${280 - (point.verdictScore / 100) * 240}`).join(" ");
  });
  const area = $derived(points ? `0,280 ${points} 900,280` : "");
  const start = $derived(visible[0]?.weekStart ?? "—");
  const end = $derived(visible[visible.length - 1]?.weekStart ?? "—");
</script>

<section class="v2-panel v2-chart" aria-labelledby="sentiment-title">
  <header class="v2-panel__header">
    <h2 id="sentiment-title">⌁ VERDICT SCORE OVER TIME</h2>
    <div role="group" aria-label="Chart range">
      {#each ["12W", "26W", "ALL"] as option}
        <button type="button" aria-pressed={range === option} onclick={() => (range = option as typeof range)}>{option}</button>
      {/each}
    </div>
  </header>
  <div class="v2-chart__body">
    <svg viewBox="0 0 900 320" role="img" aria-label={`Verdict score from ${start} to ${end}`} preserveAspectRatio="none">
      <defs><linearGradient id="v2-chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--v2-accent)" stop-opacity=".32"></stop><stop offset="1" stop-color="var(--v2-accent)" stop-opacity="0"></stop></linearGradient></defs>
      {#each [40, 100, 160, 220, 280] as y}<line x1="0" x2="900" {y} y2={y}></line>{/each}
      {#if area}<polygon points={area}></polygon><polyline points={points}></polyline>{/if}
    </svg>
  </div>
  <footer><span>{start}</span><span>50 = NEUTRAL THRESHOLD</span><span>{end}</span></footer>
</section>
