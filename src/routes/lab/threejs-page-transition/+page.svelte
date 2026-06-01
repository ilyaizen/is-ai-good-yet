<script lang="ts">
  import type { PageData } from "./$types"
  import LabCard from "$lib/components/lab/lab-card.svelte"

  let { data }: { data: PageData } = $props()
</script>

<svelte:head>
  <meta name="robots" content="noindex" />
</svelte:head>

<section class="lab-hero">
  <div class="lab-hero__copy">
    <p class="lab-hero__eyebrow">lab / threejs-page-transition</p>
    <h1>Ported the page-transition idea into SvelteKit.</h1>
    <p class="lab-hero__lede">
      Click a card. The route change gets wrapped in a Three.js curtain instead of
      the usual dead, sterile navigation snap.
    </p>
  </div>

  <div class="lab-hero__note bg-card">
    <p>
      This is a local port, not a cargo-cult clone. The original repo is Next.js +
      React + Three.js. Here it is turned into a route-local Svelte lab using the
      current app’s data.
    </p>
  </div>
</section>

<section class="lab-grid">
  {#each data.cards as card}
    <LabCard {card} />
  {/each}
</section>

<style>
  .lab-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
    gap: 1.5rem;
    align-items: end;
    margin-bottom: 1.5rem;
  }

  .lab-hero__copy,
  .lab-hero__note {
    border-radius: 1.5rem;
    border: 1px solid oklch(from var(--border) l c h / 0.75);
    padding: 1.25rem 1.35rem;
    background: oklch(from var(--card) l c h / 0.82);
  }

  .lab-hero__eyebrow {
    margin: 0 0 0.75rem;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-size: 0.8rem;
  }

  .lab-hero h1 {
    margin: 0;
    font-size: clamp(2.2rem, 6vw, 5rem);
    line-height: 0.96;
    max-width: 11ch;
  }

  .lab-hero__lede,
  .lab-hero__note p {
    margin: 0.9rem 0 0;
    color: var(--color-text-secondary);
    font-size: 1.02rem;
  }

  .lab-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 1rem;
  }

  @media (max-width: 980px) {
    .lab-hero,
    .lab-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
