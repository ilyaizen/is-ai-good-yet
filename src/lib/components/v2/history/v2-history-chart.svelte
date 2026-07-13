<script lang="ts">
  import { curveMonotoneX, line } from "d3-shape";
  import type { V2HistoryPoint } from "$lib/types/v2";
  import { V2_DIMENSIONS } from "$lib/types/v2";
  interface Props { points: V2HistoryPoint[]; visibleDimensions: Record<string, boolean>; }
  let { points, visibleDimensions }: Props = $props();
  const width = 1000;
  const height = 260;
  const x = (index: number) => points.length < 2 ? width / 2 : (index / (points.length - 1)) * width;
  const y = (score: number) => height - ((score + 2) / 4) * height;
  const path = (dimension: (typeof V2_DIMENSIONS)[number]) => line<V2HistoryPoint>()
    .defined((point) => point.dimensions[dimension].score !== null)
    .x((_point, index) => x(index))
    .y((point) => y(point.dimensions[dimension].score ?? 0))
    .curve(curveMonotoneX)(points) ?? "";
</script>

<section id="history" class="v2-section v2-history" aria-labelledby="history-title">
  <header class="v2-section__header"><div><p>DIMENSIONAL TREND</p><h2 id="history-title">History</h2></div><span>SIGNED SCALE −2…+2</span></header>
  {#if points.length}
    <div class="v2-history__chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="history-title history-description">
        <desc id="history-description">Historical capability, trajectory and impact scores on a signed minus two to plus two scale.</desc>
        <line x1="0" x2={width} y1={y(0)} y2={y(0)} class="v2-history__zero" />
        {#each V2_DIMENSIONS as dimension}{#if visibleDimensions[dimension]}<path d={path(dimension)} class={`v2-history__line v2-history__line--${dimension}`} />{/if}{/each}
      </svg>
      <div class="v2-history__legend">{#each V2_DIMENSIONS as dimension}{#if visibleDimensions[dimension]}<span data-dimension={dimension}>{dimension}</span>{/if}{/each}</div>
    </div>
  {:else}<div class="v2-empty"><strong>HISTORY STARTS AFTER THE FIRST VALID GENERATION</strong><p>No V1 series is substituted.</p></div>{/if}
</section>
