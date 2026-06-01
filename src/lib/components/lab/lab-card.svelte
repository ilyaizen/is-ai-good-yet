<script lang="ts">
  import { getContext } from "svelte"
  import type { LabTransitionCard } from "$lib/lab/transition-data"

  interface Props {
    card: LabTransitionCard
    compact?: boolean
  }

  let { card, compact = false }: Props = $props()

  const transition = getContext<{
    navigate: (card: LabTransitionCard) => Promise<void> | void
    busy: boolean
  } | null>("labTransition")

  function handleClick(event: MouseEvent) {
    if (!transition) return
    event.preventDefault()
    transition.navigate(card)
  }
</script>

<a
  href={card.href}
  class="lab-card group"
  class:lab-card--compact={compact}
  onclick={handleClick}
  aria-label={`Open ${card.title}`}
>
  <figure class="lab-card__poster">
    <img src={card.poster} alt="" aria-hidden="true" loading="lazy" />
  </figure>

  <div class="lab-card__meta">
    <div class="lab-card__kicker">
      <span>HN {card.article.hn_id}</span>
      <span>{card.tone}</span>
    </div>

    <h3 class="lab-card__title">{card.title}</h3>
    <p class="lab-card__summary">{card.summary}</p>

    <div class="lab-card__footer">
      <span>{card.topic}</span>
      <span>{card.hnScore} points</span>
    </div>
  </div>
</a>

<style>
  .lab-card {
    display: grid;
    gap: 1rem;
    grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
    padding: 1rem;
    border-radius: 1.5rem;
    border: 1px solid oklch(from var(--border) l c h / 0.8);
    background: oklch(from var(--card) l c h / 0.84);
    box-shadow: 0 24px 64px rgb(2 6 23 / 0.16);
    transition:
      transform 180ms ease,
      border-color 180ms ease,
      box-shadow 180ms ease;
    overflow: hidden;
    color: inherit;
    text-decoration: none;
  }

  .lab-card:hover {
    transform: translateY(-3px);
    border-color: oklch(from var(--primary) l c h / 0.55);
    box-shadow: 0 28px 72px rgb(2 6 23 / 0.24);
  }

  .lab-card--compact {
    grid-template-columns: 1fr;
  }

  .lab-card__poster {
    border-radius: 1.1rem;
    overflow: hidden;
    min-height: 280px;
    background: #06090f;
  }

  .lab-card--compact .lab-card__poster {
    min-height: 220px;
  }

  .lab-card__poster img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .lab-card__meta {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    min-width: 0;
  }

  .lab-card__kicker,
  .lab-card__footer {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    justify-content: space-between;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .lab-card__title {
    margin: 0;
    font-size: clamp(1.2rem, 2vw, 1.8rem);
    line-height: 1.08;
  }

  .lab-card__summary {
    margin: 0;
    color: var(--color-text-secondary);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 5;
    line-clamp: 5;
    overflow: hidden;
  }

  .lab-card__footer {
    margin-top: auto;
    padding-top: 0.25rem;
    border-top: 1px solid oklch(from var(--border) l c h / 0.4);
  }

  @media (max-width: 900px) {
    .lab-card {
      grid-template-columns: 1fr;
    }
  }
</style>
