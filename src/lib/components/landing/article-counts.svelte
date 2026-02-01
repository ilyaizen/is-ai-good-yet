<script lang="ts">
  let {
    positive,
    negative,
    neutral = 0,
    positiveContribution = 0,
    negativeContribution = 0,
    neutralContribution = 0,
    showContributions = false,
  }: {
    positive: number
    negative: number
    neutral?: number
    positiveContribution?: number
    negativeContribution?: number
    neutralContribution?: number
    showContributions?: boolean
  } = $props()

  function formatContribution(c: number): string {
    const prefix = c >= 0 ? "+" : ""
    if (Math.abs(c) >= 1_000_000) return `${prefix}${(c / 1_000_000).toFixed(1)}M`
    if (Math.abs(c) >= 1_000) return `${prefix}${(c / 1_000).toFixed(0)}k`
    return `${prefix}${c.toFixed(0)}`
  }
</script>

<div class="article-counts">
  <span class="count positive">
    {positive} positive
    {#if showContributions && positiveContribution !== 0}
      <span class="contribution">({formatContribution(positiveContribution)} pts)</span>
    {/if}
  </span>
  <span class="separator"></span>
  <span class="count negative">
    {negative} negative
    {#if showContributions && negativeContribution !== 0}
      <span class="contribution">({formatContribution(negativeContribution)} pts)</span>
    {/if}
  </span>
  {#if neutral > 0}
    <span class="separator"></span>
    <span class="count neutral">
      {neutral} neutral
      {#if showContributions && neutralContribution !== 0}
        <span class="contribution">({formatContribution(neutralContribution)} pts)</span>
      {/if}
    </span>
  {/if}
</div>

<style>
  .article-counts {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-muted-foreground);
    padding: 1rem 0;
  }

  .count {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
  }

  .count.positive {
    color: var(--color-primary);
  }

  .count.negative {
    color: var(--color-destructive);
  }

  .count.neutral {
    color: var(--color-warning);
  }

  .separator {
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: var(--color-border);
  }

  .contribution {
    opacity: 0.8;
    font-size: 0.7rem;
    margin-left: 0.15rem;
    font-weight: 600;
  }
</style>
