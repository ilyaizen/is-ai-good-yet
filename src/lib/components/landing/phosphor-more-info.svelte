<script lang="ts">
  import themes from "$lib/data/themes.json"
  import type { PageData } from "../../../routes/$types"

  let { quotes }: { quotes: PageData["detailQuotes"] } = $props()

  const groups = [
    { key: "positive", label: "The good" },
    { key: "neutral", label: "The mixed" },
    { key: "negative", label: "The bad" },
  ] as const
</script>

<section id="details" class="ph-details" aria-labelledby="ph-details-heading">
  <h2 id="ph-details-heading"><span>/details</span> more info</h2>
  <p class="summary">
    Developers report that AI coding tools help small teams ship faster. They also describe heavy review overhead,
    reliability problems, concerns about losing skills, and uncertain long-term costs. The themes below summarize
    those arguments, not a consensus among all developers.
  </p>

  <div class="themes">
    {#each groups as group (group.key)}
      {@const quote = quotes.find((item) => item.sentiment === group.key)}
      <section class={group.key} aria-label={group.label}>
        <h3>{group.label}</h3>
        {#if quote}
          <blockquote>
            <p><q>{quote.text}</q></p>
            <a href={`https://news.ycombinator.com/item?id=${quote.hnId}`}>HN discussion</a>
          </blockquote>
        {/if}
        <ul>
          {#each themes[group.key].slice(0, 3) as theme (theme.title)}
            <li>
              <details>
                <summary>{theme.title}</summary>
                <p>{theme.description}</p>
              </details>
            </li>
          {/each}
        </ul>
      </section>
    {/each}
  </div>
</section>

<style>
  .ph-details {
    scroll-margin-top: 6rem;
    border-top: 1px solid var(--td-rule);
    padding-top: 1rem;
  }

  h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
  }

  h2 span {
    color: var(--td-accent);
  }

  .summary {
    max-width: 74ch;
    margin: 0.5rem 0 1.25rem;
    color: var(--td-muted);
  }

  .themes {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 17rem), 1fr));
    gap: 1rem;
  }

  .positive { --theme-tone: var(--td-pos); --theme-rule: var(--td-pos-soft); }
  .neutral { --theme-tone: var(--td-neu); --theme-rule: var(--td-neu-soft); }
  .negative { --theme-tone: var(--td-neg); --theme-rule: var(--td-neg-soft); }

  .themes section {
    border-top: 1px solid var(--theme-rule);
    background: var(--td-surface);
    padding: 0.85rem;
  }

  h3 {
    margin: 0 0 0.65rem;
    color: var(--theme-tone);
    font-weight: 700;
  }

  blockquote {
    margin: 0 0 0.65rem;
    color: var(--td-muted);
  }

  blockquote p { margin: 0 0 0.3rem; }

  a {
    color: var(--td-ink);
    font-size: 0.78rem;
    text-decoration: underline;
    text-underline-offset: 0.2em;
  }

  ul { margin: 0; padding: 0; list-style: none; }

  details {
    border-top: 1px solid var(--td-rule-soft);
    padding-block: 0.5rem;
  }

  summary { cursor: pointer; }
  details p { margin: 0.4rem 0 0; color: var(--td-muted); }

  :is(summary, a):focus-visible {
    outline: 2px solid var(--td-accent);
    outline-offset: 2px;
  }
</style>
