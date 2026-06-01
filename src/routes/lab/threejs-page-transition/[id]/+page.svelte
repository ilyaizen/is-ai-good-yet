<script lang="ts">
  import { goto } from "$app/navigation"
  import type { PageData } from "./$types"
  import { getContext } from "svelte"
  import type { LabTransitionCard } from "$lib/lab/transition-data"

  let { data }: { data: PageData } = $props()

  const transition = getContext<{
    navigate: (card: LabTransitionCard) => Promise<void> | void
    busy: boolean
  } | null>("labTransition")

  function goBack() {
    if (transition) {
      transition.navigate({ ...data.card, href: "/lab/threejs-page-transition" })
      return
    }

    goto("/lab/threejs-page-transition")
  }

  function goNext() {
    if (!data.nextCard) return
    if (transition) {
      transition.navigate(data.nextCard)
      return
    }

    goto(data.nextCard.href)
  }
</script>

<svelte:head>
  <title>{data.card.title} · Three.js page transition lab</title>
  <meta name="description" content={data.card.summary} />
</svelte:head>

<section class="detail-shell">
  <div class="detail-shell__nav">
    <a href="/lab/threejs-page-transition" class="detail-shell__back">← back to lab</a>
    <button type="button" class="detail-shell__button" onclick={goNext} disabled={!data.nextCard}>next card</button>
  </div>

  <div class="detail-grid">
    <figure class="detail-poster">
      <img src={data.card.poster} alt="" aria-hidden="true" />
      <figcaption>
        <span>HN {data.card.article.hn_id}</span>
        <span>{data.card.tone}</span>
      </figcaption>
    </figure>

    <aside class="detail-panel bg-card">
      <p class="detail-panel__eyebrow">route detail / HN {data.card.article.hn_id}</p>
      <h1>{data.card.title}</h1>
      <p class="detail-panel__lede">{data.card.summary}</p>

      <dl class="detail-stats">
        <div>
          <dt>Tone</dt>
          <dd>{data.card.tone}</dd>
        </div>
        <div>
          <dt>Sentiment</dt>
          <dd>{data.card.score.toFixed(2)}</dd>
        </div>
        <div>
          <dt>HN score</dt>
          <dd>{data.card.hnScore}</dd>
        </div>
        <div>
          <dt>Comments</dt>
          <dd>{data.card.hnComments}</dd>
        </div>
      </dl>

      <div class="detail-panel__links">
        <a href={data.card.article.url} target="_blank" rel="noreferrer">open source article</a>
        <button type="button" onclick={goBack}>replay transition</button>
      </div>
    </aside>
  </div>
</section>

<style>
  .detail-shell {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .detail-shell__nav {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }

  .detail-shell__back,
  .detail-shell__button,
  .detail-panel__links a,
  .detail-panel__links button {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .detail-shell__button,
  .detail-panel__links button {
    border: 1px solid oklch(from var(--border) l c h / 0.85);
    border-radius: 999px;
    padding: 0.75rem 1rem;
    background: oklch(from var(--card) l c h / 0.8);
    color: var(--color-text-primary);
  }

  .detail-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
    gap: 1rem;
    align-items: start;
  }

  .detail-poster {
    margin: 0;
    border-radius: 1.5rem;
    border: 1px solid oklch(from var(--border) l c h / 0.75);
    overflow: hidden;
    background: #06090f;
    box-shadow: 0 24px 64px rgb(2 6 23 / 0.16);
  }

  .detail-poster img {
    display: block;
    width: 100%;
    height: auto;
  }

  .detail-poster figcaption {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.9rem 1rem;
    border-top: 1px solid oklch(from var(--border) l c h / 0.45);
    background: rgb(255 255 255 / 0.03);
    font-family: var(--font-mono);
    font-size: 0.74rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--color-text-secondary);
  }

  .detail-panel {
    border-radius: 1.5rem;
    border: 1px solid oklch(from var(--border) l c h / 0.75);
    padding: 1.25rem 1.35rem;
    background: oklch(from var(--card) l c h / 0.82);
    box-shadow: 0 24px 64px rgb(2 6 23 / 0.16);
  }

  .detail-panel__eyebrow {
    margin: 0 0 0.8rem;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .detail-panel h1 {
    margin: 0;
    font-size: clamp(1.9rem, 4vw, 3.4rem);
    line-height: 0.98;
  }

  .detail-panel__lede {
    margin: 1rem 0 0;
    color: var(--color-text-secondary);
    font-size: 1rem;
  }

  .detail-stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.8rem;
    margin: 1.25rem 0;
  }

  .detail-stats div {
    border-radius: 1rem;
    border: 1px solid oklch(from var(--border) l c h / 0.55);
    padding: 0.85rem 0.95rem;
    background: rgb(255 255 255 / 0.03);
  }

  .detail-stats dt {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--color-text-secondary);
  }

  .detail-stats dd {
    margin: 0.3rem 0 0;
    font-size: 1.1rem;
    color: var(--color-text-primary);
  }

  .detail-panel__links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .detail-panel__links a,
  .detail-panel__links button {
    text-decoration: none;
  }

  @media (max-width: 980px) {
    .detail-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
