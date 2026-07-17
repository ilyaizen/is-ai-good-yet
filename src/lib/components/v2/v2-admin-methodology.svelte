<script lang="ts">
  interface Methodology {
    versions: {
      analysis: string;
      articlePrompt: string;
      commentPrompt: string;
      selection: string;
      aggregation: string;
    };
    model: string;
    modelParameters: string;
    limits: {
      articleCharacters: number;
      commentCharacters: number;
      contextCharacters: number;
      minimumArticleCharacters: number;
    };
    selection: {
      minimumStoryScore: number;
      minimumCommentCount: number;
      authorCap: number;
      target: string;
      branchCap: string;
    };
    aggregation: {
      articleWeight: number;
      communityWeight: number;
      verdictMonths: number;
      dimensions: string[];
      scoreScale: string;
    };
    articlePrompt: string;
    commentPrompt: string;
  }

  let { methodology }: { methodology: Methodology } = $props();

  // Prompts are soft-wrapped at ~100 cols in the Python source. Reflow soft wraps
  // into spaces so they read as normal prose, but keep paragraph breaks and list
  // items (lines starting with -, *, •, or N.) so structure survives.
  function reflowPrompt(text: string): string {
    const isListItem = (line: string) => /^\s*([-*•]|\d+[.)])\s+/.test(line);
    const out: string[] = [];
    let para: string[] = [];
    const flush = () => {
      if (para.length) {
        out.push(para.join(" "));
        para = [];
      }
    };
    for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
      const line = raw.trimEnd();
      if (line.trim() === "") {
        flush();
        out.push("");
        continue;
      }
      if (isListItem(line)) {
        flush();
        out.push(line.trim());
        continue;
      }
      para.push(line.trim());
    }
    flush();
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  const stages = $derived.by(() => [
    {
      marker: "01",
      name: "Discover + scrape",
      detail: `HN stories enter at ≥${methodology.selection.minimumStoryScore} points and ≥${methodology.selection.minimumCommentCount} comments. Article text is stored in the live pipeline database.`
    },
    {
      marker: "02",
      name: "Read the article",
      detail: `The article is analyzed independently across ${methodology.aggregation.dimensions.join(", ")}. Claims require attributed evidence; missing evidence is not scored as neutral.`
    },
    {
      marker: "03",
      name: "Sample the discussion",
      detail: `HN comments are selected deterministically across authors and branches. Each voting comment is annotated in isolation from contextual text.`
    },
    {
      marker: "04",
      name: "Combine the record",
      detail: `Article and community scores are confidence-weighted at ${methodology.aggregation.articleWeight * 100}/${methodology.aggregation.communityWeight * 100} over a ${methodology.aggregation.verdictMonths}-month verdict window.`
    }
  ]);
</script>

<section class="v2-method" aria-labelledby="v2-methodology-title">
  <div class="v2-method__card">
    <header class="v2-method__head">
      <p class="v2-method__kicker">Methodology</p>
      <div class="v2-method__head-row">
        <div>
          <h2 id="v2-methodology-title" class="v2-method__title">
            How the verdict is produced
          </h2>
          <p class="v2-method__lede">
            This view reads its versions, limits, weights, and prompts from the Python pipeline source on the server.
            It describes the code that runs, not a separate editorial summary.
          </p>
        </div>
        <span class="v2-method__chip">Analysis {methodology.versions.analysis}</span>
      </div>
    </header>

    <div class="method-flow">
      {#each stages as stage, i (stage.marker)}
        {#if i > 0}
          <span class="method-flow__arrow" aria-hidden="true">→</span>
        {/if}
        <article class="method-flow__node">
          <div class="method-flow__node-head">
            <span class="method-flow__marker">{stage.marker}</span>
            <h3 class="method-flow__name">{stage.name}</h3>
          </div>
          <p class="method-flow__detail">{stage.detail}</p>
        </article>
      {/each}
    </div>

    <div class="v2-method__grid">
      <div class="v2-method__col">
        <section aria-labelledby="method-config-title">
          <h3 id="method-config-title" class="v2-method__subhead">Runtime contract</h3>
          <dl class="v2-kv">
            <div><dt>Model</dt><dd>{methodology.model}</dd></div>
            <div><dt>Parameters</dt><dd>{methodology.modelParameters}</dd></div>
            <div><dt>Article input</dt><dd>{methodology.limits.minimumArticleCharacters}–{methodology.limits.articleCharacters.toLocaleString()} chars</dd></div>
            <div><dt>Comment / context</dt><dd>{methodology.limits.commentCharacters.toLocaleString()} / {methodology.limits.contextCharacters.toLocaleString()} chars</dd></div>
            <div><dt>Comment target</dt><dd>{methodology.selection.target}</dd></div>
            <div><dt>Author / branch caps</dt><dd>{methodology.selection.authorCap} per author · {methodology.selection.branchCap}</dd></div>
            <div><dt>Display scale</dt><dd>{methodology.aggregation.scoreScale}</dd></div>
          </dl>
        </section>

        <section aria-labelledby="method-versions-title">
          <h3 id="method-versions-title" class="v2-method__subhead">Version ledger</h3>
          <dl class="v2-kv">
            {#each Object.entries(methodology.versions) as [name, version] (name)}
              <div><dt class="capitalize">{name.replace(/([A-Z])/g, " $1")}</dt><dd>{version}</dd></div>
            {/each}
          </dl>
        </section>
      </div>

      <section aria-labelledby="method-prompts-title">
        <h3 id="method-prompts-title" class="v2-method__subhead">Exact model prompts</h3>
        <p class="v2-method__lede">
          Input packets are appended at runtime. The system-level instructions below are shown verbatim after Python
          version placeholders are resolved.
        </p>

        <div class="v2-method__prompts">
          <details class="v2-method__prompt" open>
            <summary class="v2-method__prompt-head">
              <span>Article prompt</span>
              <span class="v2-method__prompt-ver">{methodology.versions.articlePrompt}</span>
            </summary>
            <pre class="v2-method__code">{reflowPrompt(methodology.articlePrompt)}</pre>
          </details>

          <details class="v2-method__prompt">
            <summary class="v2-method__prompt-head">
              <span>Voting-comment prompt</span>
              <span class="v2-method__prompt-ver">{methodology.versions.commentPrompt}</span>
            </summary>
            <pre class="v2-method__code">{reflowPrompt(methodology.commentPrompt)}</pre>
          </details>
        </div>
      </section>
    </div>
  </div>
</section>

<style>
  .v2-method {
    max-width: 96rem;
    margin: 1.25rem auto 0;
    padding: 0 1rem;
  }
  @media (min-width: 640px) {
    .v2-method {
      padding: 0 1.5rem;
    }
  }
  @media (min-width: 1024px) {
    .v2-method {
      padding: 0 2rem;
    }
  }

  .v2-method__card {
    border: 1px solid var(--v2-separator);
    border-radius: 0.65rem;
    background: color-mix(in srgb, var(--v2-text) 1.5%, transparent);
    overflow: hidden;
    color: var(--v2-text);
  }

  .v2-method__head {
    padding: 1.5rem;
    border-bottom: 1px solid var(--v2-separator);
  }
  @media (min-width: 1024px) {
    .v2-method__head {
      padding: 2rem;
    }
  }
  .v2-method__kicker {
    color: var(--v2-text-faint);
    font: 500 0.68rem/1.4 ui-monospace, monospace;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .v2-method__head-row {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-top: 0.5rem;
  }
  @media (min-width: 1024px) {
    .v2-method__head-row {
      flex-direction: row;
      align-items: flex-end;
      justify-content: space-between;
    }
  }
  .v2-method__title {
    font-size: 1.35rem;
    font-weight: 510;
    line-height: 1.15;
    letter-spacing: -0.025em;
    color: var(--v2-text);
  }
  .v2-method__lede {
    max-width: 48rem;
    margin-top: 0.75rem;
    color: var(--v2-text-muted);
    font: 0.85rem/1.65 var(--v2-font-copy);
  }
  .v2-method__chip {
    align-self: flex-start;
    border: 1px solid var(--v2-separator);
    border-radius: 999px;
    padding: 0.22rem 0.55rem;
    color: var(--v2-text-muted);
    font: 500 0.62rem ui-monospace, monospace;
    text-transform: uppercase;
    white-space: nowrap;
  }

  /* Stage flow — V2 card idiom */
  .method-flow {
    display: flex;
    align-items: stretch;
    gap: 0;
    padding: 1rem;
    overflow-x: auto;
  }
  .method-flow__node {
    flex: 1 1 0;
    min-width: 13rem;
    padding: 1.25rem;
    background: var(--v2-surface-1);
    border-left: 2px solid var(--v2-phosphor);
    box-shadow: inset 0 1px var(--v2-separator-quiet), var(--v2-shadow);
  }
  .method-flow__node-head {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  .method-flow__marker {
    color: var(--v2-phosphor);
    font: 500 0.68rem ui-monospace, monospace;
  }
  .method-flow__name {
    font-size: 0.85rem;
    font-weight: 510;
    color: var(--v2-text);
  }
  .method-flow__detail {
    margin-top: 0.75rem;
    color: var(--v2-text-muted);
    font: 0.8rem/1.6 var(--v2-font-copy);
  }
  .method-flow__arrow {
    flex: 0 0 2.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--v2-phosphor);
    font-size: 1.15rem;
    line-height: 1;
  }
  @media (max-width: 1023px) {
    .method-flow {
      flex-direction: column;
      padding: 0.75rem;
    }
    .method-flow__node {
      min-width: 0;
      width: 100%;
    }
    .method-flow__arrow {
      flex-basis: auto;
      height: 1.75rem;
      transform: rotate(90deg);
    }
  }

  /* Two-column body */
  .v2-method__grid {
    display: grid;
    gap: 1.5rem;
    padding: 1.5rem;
  }
  @media (min-width: 1280px) {
    .v2-method__grid {
      grid-template-columns: 0.8fr 1.2fr;
      padding: 2rem;
    }
  }
  .v2-method__col {
    display: grid;
    gap: 1.5rem;
  }
  .v2-method__subhead {
    color: var(--v2-text-faint);
    font: 500 0.68rem/1.4 ui-monospace, monospace;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  /* Key-value hairline grid (matches observability prefilter idiom) */
  .v2-kv {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1px;
    margin: 0.75rem 0 0;
    background: var(--v2-separator-quiet);
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.5rem;
    overflow: hidden;
  }
  .v2-kv div {
    padding: 0.65rem 1rem;
    background: var(--v2-recess);
  }
  .v2-kv dt {
    color: var(--v2-text-faint);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .v2-kv dd {
    margin: 0.25rem 0 0;
    color: var(--v2-text-muted);
    font: 400 0.72rem/1.45 ui-monospace, monospace;
    overflow-wrap: anywhere;
  }

  /* Prompts */
  .v2-method__prompts {
    display: grid;
    gap: 0.75rem;
    margin-top: 1rem;
  }
  .v2-method__prompt {
    background: var(--v2-recess);
    border: 1px solid var(--v2-separator-quiet);
    border-radius: 0.5rem;
    overflow: hidden;
  }
  .v2-method__prompt-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem 1rem;
    color: var(--v2-text);
    font-size: 0.82rem;
    cursor: pointer;
    list-style: none;
  }
  .v2-method__prompt-ver {
    color: var(--v2-text-faint);
    font: 500 0.65rem ui-monospace, monospace;
  }
  .v2-method__code {
    margin: 0;
    padding: 1rem;
    border-top: 1px solid var(--v2-separator-quiet);
    background: var(--v2-recess);
    color: var(--v2-text-muted);
    font: 0.68rem/1.6 ui-monospace, monospace;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
</style>
