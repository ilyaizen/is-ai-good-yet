<script lang="ts">
  import type { Snippet } from "svelte"
  import { cn } from "$lib/utils"

  interface Props {
    icon?: Snippet
    title: string
    description: string
    verdict: string
    sentiment?: "neutral" | "negative" | "positive"
    class?: string
  }

  let { icon, title, description, verdict, sentiment = "neutral", class: className = "" }: Props = $props()
</script>

<article class={cn("topic-card", className)}>
  {#if icon}
    <div class="topic-icon">
      {@render icon()}
    </div>
  {/if}
  <h3 class="topic-title">{title}</h3>
  <p class="topic-desc">{description}</p>
  <span class="sentiment-tag {sentiment}">Verdict: {verdict}</span>
</article>

<style>
  .topic-card {
    background: linear-gradient(145deg, var(--color-surface), rgba(255, 255, 255, 0.02));
    padding: 2rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
  }

  .topic-icon {
    color: var(--color-primary);
    margin-bottom: 1rem;
  }

  .topic-title {
    font-size: 1.25rem;
    margin-bottom: 0.75rem;
    color: var(--color-text-primary);
  }

  .topic-desc {
    font-size: 0.95rem;
    color: var(--color-text-secondary);
    margin-bottom: 1.5rem;
    flex-grow: 1;
  }

  .sentiment-tag {
    align-self: flex-start;
    padding: 0.25rem 0.75rem;
    background: rgba(45, 212, 191, 0.1);
    color: var(--color-secondary);
    border-radius: 99px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(45, 212, 191, 0.2);
  }

  .sentiment-tag.negative {
    background: rgba(248, 113, 113, 0.1);
    color: #f87171;
    border-color: rgba(248, 113, 113, 0.2);
  }

  .sentiment-tag.positive {
    background: color-mix(in srgb, var(--color-primary), transparent 90%);
    color: var(--color-primary);
    border-color: color-mix(in srgb, var(--color-primary), transparent 80%);
  }
</style>
