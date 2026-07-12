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

<section class="mx-auto max-w-7xl px-4 pb-12 sm:px-6 lg:px-8" aria-labelledby="v2-methodology-title">
  <div class="terminal-panel overflow-hidden">
    <header class="border-b border-terminal-border-subtle p-6 sm:p-8">
      <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Methodology</p>
      <div class="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 id="v2-methodology-title" class="text-2xl font-semibold tracking-tight text-terminal-text">
            How the verdict is produced
          </h2>
          <p class="mt-3 max-w-3xl text-sm leading-6 text-terminal-text-muted">
            This view reads its versions, limits, weights, and prompts from the Python pipeline source on the server.
            It describes the code that runs, not a separate editorial summary.
          </p>
        </div>
        <div class="terminal-chip self-start lg:self-auto">Analysis {methodology.versions.analysis}</div>
      </div>
    </header>

    <div class="grid gap-px bg-terminal-border-subtle lg:grid-cols-4">
      {#each stages as stage (stage.marker)}
        <article class="bg-terminal-bg p-5">
          <div class="flex items-center gap-3">
            <span class="text-xs text-terminal-accent">{stage.marker}</span>
            <h3 class="text-sm font-semibold text-terminal-text">{stage.name}</h3>
          </div>
          <p class="mt-3 text-sm leading-6 text-terminal-text-muted">{stage.detail}</p>
        </article>
      {/each}
    </div>

    <div class="grid gap-6 p-6 sm:p-8 xl:grid-cols-[0.8fr_1.2fr]">
      <div class="space-y-6">
        <section aria-labelledby="method-config-title">
          <h3 id="method-config-title" class="text-xs uppercase tracking-[0.25em] text-terminal-text-faint">
            Runtime contract
          </h3>
          <dl class="mt-3 grid gap-2 text-sm">
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Model</dt>
              <dd class="text-right text-terminal-text">{methodology.model}</dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Parameters</dt>
              <dd class="text-right text-terminal-text">{methodology.modelParameters}</dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Article input</dt>
              <dd class="text-right text-terminal-text">
                {methodology.limits.minimumArticleCharacters}–{methodology.limits.articleCharacters.toLocaleString()} chars
              </dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Comment / context</dt>
              <dd class="text-right text-terminal-text">
                {methodology.limits.commentCharacters.toLocaleString()} / {methodology.limits.contextCharacters.toLocaleString()} chars
              </dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Comment target</dt>
              <dd class="max-w-[22rem] text-right text-terminal-text">{methodology.selection.target}</dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Author / branch caps</dt>
              <dd class="max-w-[22rem] text-right text-terminal-text">
                {methodology.selection.authorCap} per author · {methodology.selection.branchCap}
              </dd>
            </div>
            <div class="terminal-card flex justify-between gap-4 px-4 py-3">
              <dt class="text-terminal-text-muted">Display scale</dt>
              <dd class="max-w-[22rem] text-right text-terminal-text">{methodology.aggregation.scoreScale}</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="method-versions-title">
          <h3 id="method-versions-title" class="text-xs uppercase tracking-[0.25em] text-terminal-text-faint">
            Version ledger
          </h3>
          <dl class="mt-3 grid gap-2 text-sm">
            {#each Object.entries(methodology.versions) as [name, version] (name)}
              <div class="terminal-card flex justify-between gap-4 px-4 py-3">
                <dt class="capitalize text-terminal-text-muted">{name.replace(/([A-Z])/g, " $1")}</dt>
                <dd class="text-right text-terminal-text">{version}</dd>
              </div>
            {/each}
          </dl>
        </section>
      </div>

      <section aria-labelledby="method-prompts-title">
        <h3 id="method-prompts-title" class="text-xs uppercase tracking-[0.25em] text-terminal-text-faint">
          Exact model prompts
        </h3>
        <p class="mt-3 text-sm leading-6 text-terminal-text-muted">
          Input packets are appended at runtime. The system-level instructions below are shown verbatim after Python
          version placeholders are resolved.
        </p>

        <div class="mt-4 space-y-3">
          <details class="terminal-card group" open>
            <summary class="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm text-terminal-text">
              <span>Article prompt</span>
              <span class="text-xs text-terminal-text-faint">{methodology.versions.articlePrompt}</span>
            </summary>
            <pre class="max-h-[34rem] overflow-auto border-t border-terminal-border-subtle bg-terminal-bg-subtle p-4 text-xs leading-6 whitespace-pre-wrap text-terminal-text-muted">{methodology.articlePrompt}</pre>
          </details>

          <details class="terminal-card group">
            <summary class="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm text-terminal-text">
              <span>Voting-comment prompt</span>
              <span class="text-xs text-terminal-text-faint">{methodology.versions.commentPrompt}</span>
            </summary>
            <pre class="max-h-[34rem] overflow-auto border-t border-terminal-border-subtle bg-terminal-bg-subtle p-4 text-xs leading-6 whitespace-pre-wrap text-terminal-text-muted">{methodology.commentPrompt}</pre>
          </details>
        </div>
      </section>
    </div>
  </div>
</section>
