<script lang="ts">
  let {
    nowScore,
    allTimeScore,
    totalArticles,
  }: {
    nowScore: number
    allTimeScore: number
    totalArticles: number
  } = $props()
</script>

<div class="stats-bar">
  <span class="stat">
    <span class="stat-label">now</span>
    <span class="stat-value">{Math.round(nowScore)}</span>
  </span>
  <span class="separator"></span>
  <span class="stat">
    <span class="stat-label">all-time</span>
    <span class="stat-value">{Math.round(allTimeScore)}</span>
  </span>
  <span class="separator"></span>
  <span class="stat">
    <span class="stat-value">{totalArticles.toLocaleString()}</span>
    <span class="stat-label">articles</span>
  </span>
</div>

<style>
  .stats-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    color: var(--color-muted-foreground);
    padding: 1rem 0;
  }

  .stat {
    display: flex;
    align-items: baseline;
    gap: 0.375rem;
  }

  .stat-label {
    color: var(--color-muted-foreground);
  }

  .stat-value {
    color: var(--color-foreground);
    font-weight: 500;
  }

  .separator {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--color-border);
  }
</style>
