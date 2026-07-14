<script lang="ts">
  import { invalidateAll } from "$app/navigation"
  import { page } from "$app/state"
  import ContentTable from "$lib/components/content-table.svelte"
  import type { V2AdminData } from "$lib/server/v2-admin-data"

  type UrlEntry = {
    id: number
    url: string
    hn_id: number | null
    hn_score: number | null
    hn_comments: number | null
    hn_title: string | null
    hn_timestamp: number | null
    hn_author: string | null
    status: string
    scraped_status: string | null
    filter_score: number | null
    opinion: string | null
    is_opinion: boolean | null
    sentiment_score: number | null
    content_category: string | null
    content_confidence: number | null
    classification_json: string | null
    content_filter_json: string | null
  }

  type PipelineCommand = {
    name: string
    label: string
    description: string
    readiness: { ready: boolean; reasons: string[] }
  }

  type RunRow = {
    id: number
    command: string
    status: string
    started_at: string
    finished_at: string | null
    exit_code: number | null
    log_path: string
    pid: number | null
    error: string | null
  }

  type LockRow = {
    id: number
    run_id: number | null
    command: string
    pid: number | null
    acquired_at: string
    stale: boolean
  }

  type StageStatus = "completed" | "active" | "pending"

  type PipelineData = {
    env: {
      repoRootExists: boolean
      venvPythonExists: boolean
      pipelineDirExists: boolean
      adminDbExists: boolean
      logDirExists: boolean
      preflight: {
        python: { ok: boolean; reason: string }
        storage: { ok: boolean; reason: string }
        scraper: { ok: boolean; reason: string }
        groq: { ok: boolean; reason: string }
        residential: { ok: boolean; reason: string }
      }
    }
    snapshot: {
      currentRun: RunRow | null
      lock: LockRow | null
      recentRuns: RunRow[]
    }
    commands: PipelineCommand[]
    logViewer: {
      run: RunRow | null
      path: string | null
      exists: boolean
      tail: string
    }
    storage: {
      dataDir: string
      pipelineDbPath: string
      adminDbPath: string
      logDir: string
    }
  }

  let {
    data,
  }: {
    data: {
      configured: boolean
      dbExists: boolean
      counts: { total: number; approved: number; refused: number; pending: number; other: number }
      stats: {
        totalUrls: number
        resolved: number
        scraped: number
        relevant: number
        analyzed: number
        failed: number
      }
      tableData: UrlEntry[]
      pipeline: PipelineData
      controlHref: string
      v2?: V2AdminData
    }
  } = $props()

  let selectedCommand = $state<PipelineCommand | null>(null)
  let confirmValue = $state("")

  function humanizeCommand(command: string): string {
    return command.replaceAll("_", " ")
  }

  function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return "—"
    return timestamp.replace("T", " ").replace("Z", " UTC")
  }

  function runStatusLabel(status: string): string {
    if (status === "running") return "Running"
    if (status === "succeeded") return "Succeeded"
    if (status === "failed") return "Failed"
    if (status === "cancelled") return "Cancelled"
    if (status === "queued") return "Queued"
    return status
  }

  function phaseStatusLabel(status: StageStatus): string {
    if (status === "completed") return "Done"
    if (status === "active") return "Active"
    return "Waiting"
  }

  function stageTone(status: StageStatus): string {
    if (status === "completed") return "border-emerald-400/20 bg-emerald-500/10"
    if (status === "active") return "border-sky-400/20 bg-sky-500/10"
    return "border-terminal-border-subtle bg-terminal-bg-subtle"
  }

  function openCommand(command: PipelineCommand): void {
    selectedCommand = command
    confirmValue = ""
  }

  function closeDialog(): void {
    selectedCommand = null
    confirmValue = ""
  }

  let canConfirm = $derived.by(() => {
    if (!selectedCommand) return false
    return confirmValue.trim().toLowerCase() === selectedCommand.name.toLowerCase()
  })

  let activeLock = $derived.by(() => Boolean(data.pipeline.snapshot.lock && !data.pipeline.snapshot.lock.stale))

  let stages = $derived.by(() => {
    const stats = data.stats
    const total = Math.max(stats.totalUrls, 1)
    const isIngestDone = stats.totalUrls > 0
    const isResolveDone = stats.resolved > 0 && stats.resolved >= total * 0.9
    const isScrapeDone = stats.scraped > 0 && stats.scraped >= Math.max(stats.resolved, 1) * 0.9
    const isFilterDone = stats.relevant > 0 && stats.relevant >= Math.max(stats.scraped, 1) * 0.8
    const isAnalyzeDone = stats.analyzed > 0 && stats.analyzed >= stats.relevant

    return [
      {
        id: "ingest",
        name: "Ingestion",
        status: (isIngestDone ? "completed" : "active") as StageStatus,
        description: "Load URLs into the pipeline",
      },
      {
        id: "resolve",
        name: "Resolution",
        status: (isResolveDone ? "completed" : isIngestDone ? "active" : "pending") as StageStatus,
        description: "Resolve HN metadata and timestamps",
      },
      {
        id: "scrape",
        name: "Scraping",
        status: (isScrapeDone ? "completed" : isResolveDone ? "active" : "pending") as StageStatus,
        description: "Fetch and clean article content",
      },
      {
        id: "filter",
        name: "Filtering",
        status: (isFilterDone ? "completed" : isScrapeDone ? "active" : "pending") as StageStatus,
        description: "Keep the rows worth spending tokens on",
      },
      {
        id: "analyze",
        name: "Analysis",
        status: (isAnalyzeDone ? "completed" : isFilterDone ? "active" : "pending") as StageStatus,
        description: "Score the final sentiment and verdict",
      },
    ]
  })

  let selectedRunId = $derived(data.pipeline.logViewer.run?.id ?? null)

  // Auto-refresh while a job runs so status + log tail update without a manual reload.
  $effect(() => {
    if (data.pipeline.snapshot.currentRun?.status !== "running") return
    const handle = setInterval(() => {
      invalidateAll().catch(() => {})
    }, 4000)
    return () => clearInterval(handle)
  })
</script>

<svelte:head>
  <title>Admin - Is AI Good Yet?</title>
</svelte:head>

<div class="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
  <!-- Header -->
  {#if !data.v2}
  <section class="terminal-panel p-6 sm:p-8">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Admin</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight text-terminal-text sm:text-4xl">Pipeline overview</h1>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-terminal-text-muted">
          Status, control, and data table — all in one place.
        </p>
      </div>

      <div class="flex flex-wrap gap-3">
        {#if data.controlHref.startsWith("/v2/")}
          <a href="#v2-methodology-title" class="terminal-action">Methodology</a>
        {/if}
        <form method="post" action="?/logout">
          <button type="submit" class="terminal-action">Log out</button>
        </form>
      </div>
    </div>

    <!-- Stats cards -->
    <div class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
      <div class="terminal-card p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text/40">Total URLs</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.totalUrls}</div>
      </div>
      <div class="terminal-card border-sky-400/20 bg-sky-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text">Resolved</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.resolved}</div>
      </div>
      <div class="terminal-card border-amber-400/20 bg-amber-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text">Scraped</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.scraped}</div>
      </div>
      <div class="terminal-card border-emerald-400/20 bg-emerald-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text">Relevant</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.relevant}</div>
      </div>
      <div class="terminal-card border-violet-400/20 bg-violet-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text">Analyzed</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.analyzed}</div>
      </div>
      <div class="terminal-card border-rose-400/20 bg-rose-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-terminal-text">Failed</div>
        <div class="mt-2 text-3xl font-semibold text-terminal-text">{data.stats.failed}</div>
      </div>
    </div>

    <!-- Config chips -->
    <div class="mt-6 flex flex-wrap gap-3 text-sm text-terminal-text-muted">
      <span class="terminal-chip">Password {data.configured ? "configured" : "missing"}</span>
      <span class="terminal-chip">DB {data.dbExists ? "found" : "missing"}</span>
      <span class="terminal-chip">Storage {data.pipeline.storage.dataDir}</span>
      <span class="terminal-chip">Rows {data.counts.total}</span>
      <span class="terminal-chip">Approved {data.counts.approved}</span>
      <span class="terminal-chip">Refused {data.counts.refused}</span>
      <span class="terminal-chip">Pending {data.counts.pending}</span>
      <span class="terminal-chip">Other {data.counts.other}</span>
    </div>

    {#if !data.configured || !data.dbExists}
      <div class="mt-6 grid gap-3 sm:grid-cols-2">
        {#if !data.configured}
          <div class="terminal-card border-amber-400/20 bg-amber-500/5 p-4 text-sm text-amber-800 dark:text-amber-100">
            Admin password is not configured. Set <code>PIPELINE_ADMIN_PASSWORD</code> first.
          </div>
        {/if}
        {#if !data.dbExists}
          <div class="terminal-card p-4 text-sm text-terminal-text-muted">
            Pipeline DB is missing on this checkout. The dashboard will populate once <code
              >pipeline/data/pipeline.db</code
            > exists.
          </div>
        {/if}
      </div>
    {/if}
  </section>
  {/if}

  <!-- Stage health + Environment -->
  {#if !data.v2}
  <section class="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
    <div class="terminal-panel p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Pipeline</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-terminal-text">Stage health</h2>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-terminal-text-muted">
            Heuristic status from the checked-in data.
          </p>
        </div>

        <div class="terminal-card px-4 py-3 text-sm text-terminal-text-muted">
          {#if data.pipeline.snapshot.lock}
            <div class="font-medium text-terminal-text">
              {data.pipeline.snapshot.lock.stale ? "Stale lock" : "Active lock"}
            </div>
            <div class="mt-1">
              {data.pipeline.snapshot.lock.command} · PID {data.pipeline.snapshot.lock.pid ?? "?"}
            </div>
          {:else}
            <div class="font-medium text-terminal-text">Idle</div>
            <div class="mt-1">No pipeline job is running right now.</div>
          {/if}
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {#each stages as stage}
          <div class={`terminal-card terminal-card--interactive p-4 ${stageTone(stage.status)}`}>
            <div class="flex items-center justify-between gap-3">
              <div class="text-sm font-semibold text-terminal-text">{stage.name}</div>
              <div class="terminal-chip text-[11px] uppercase tracking-[0.2em] text-terminal-text-muted">
                {phaseStatusLabel(stage.status)}
              </div>
            </div>
            <p class="mt-3 text-sm leading-6 text-terminal-text-muted">{stage.description}</p>
          </div>
        {/each}
      </div>
    </div>

    <div class="terminal-panel p-6">
      <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Environment</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-terminal-text">Runtime checks</h2>
      <p class="mt-3 text-sm leading-6 text-terminal-text-muted">
        Real import, browser, storage, API-key, and fallback diagnostics. Failed prerequisites block execution.
      </p>

      <div class="mt-5 space-y-3 text-sm">
        {#each [["Repo root", data.pipeline.env.repoRootExists], ["Venv Python", data.pipeline.env.venvPythonExists], ["Pipeline dir", data.pipeline.env.pipelineDirExists], ["Admin DB", data.pipeline.env.adminDbExists], ["Logs dir", data.pipeline.env.logDirExists]] as [label, ok]}
          <div class="terminal-card flex items-center justify-between gap-4 px-4 py-3">
            <span class="text-terminal-text-muted">{label}</span>
            <span
              class={`terminal-chip text-xs font-medium ${ok ? "bg-emerald-500/15 text-terminal-text" : "bg-rose-500/15 text-terminal-text"}`}
            >
              {ok ? "OK" : "Missing"}
            </span>
          </div>
        {/each}
        {#each Object.entries(data.pipeline.env.preflight) as [label, check]}
          <div class="terminal-card px-4 py-3">
            <div class="flex items-center justify-between gap-4">
              <span class="capitalize text-terminal-text-muted">{label}</span>
              <span
                class={`terminal-chip text-xs font-medium ${check.ok ? "bg-emerald-500/15 text-terminal-text" : "bg-rose-500/15 text-terminal-text"}`}
              >
                {check.ok ? "Ready" : "Blocked"}
              </span>
            </div>
            <p class="mt-2 break-words text-xs leading-5 text-terminal-text-faint">{check.reason}</p>
          </div>
        {/each}
      </div>
    </div>
  </section>
  {/if}

  <!-- Current run + Recent runs -->
  <section class="grid gap-4">
    <div class="terminal-panel p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Current run</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-terminal-text">Latest job state</h2>
        </div>
        <span class="terminal-chip">
          {data.pipeline.snapshot.currentRun ? runStatusLabel(data.pipeline.snapshot.currentRun.status) : "Idle"}
        </span>
      </div>

      {#if data.pipeline.snapshot.currentRun}
        <dl class="mt-5 space-y-3 text-sm text-terminal-text-muted">
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-terminal-text-faint">Run</dt>
            <dd class="text-right text-terminal-text">#{data.pipeline.snapshot.currentRun.id}</dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-terminal-text-faint">Command</dt>
            <dd class="text-right text-terminal-text">{humanizeCommand(data.pipeline.snapshot.currentRun.command)}</dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-terminal-text-faint">Started</dt>
            <dd class="text-right text-terminal-text">
              {formatTimestamp(data.pipeline.snapshot.currentRun.started_at)}
            </dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-terminal-text-faint">Log</dt>
            <dd
              class="max-w-[18rem] truncate text-right text-terminal-text-muted"
              title={data.pipeline.snapshot.currentRun.log_path}
            >
              {data.pipeline.snapshot.currentRun.log_path}
            </dd>
          </div>
          {#if data.pipeline.snapshot.currentRun.error}
            <div class="terminal-card border-rose-400/20 bg-rose-500/5 p-4 text-terminal-text">
              {data.pipeline.snapshot.currentRun.error}
            </div>
          {/if}
        </dl>
      {:else}
        <div class="terminal-card mt-5 border-dashed p-4 text-sm text-terminal-text-muted">
          No active run. Start a job below if you need to move the data forward.
        </div>
      {/if}

      <!-- Log viewer -->
      <div class="terminal-card mt-6 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-terminal-text">Log tail</h3>
            <p class="mt-1 text-sm text-terminal-text-muted">The real subprocess output, not an invented summary.</p>
          </div>
          <span class="terminal-chip">
            {data.pipeline.logViewer.run ? `#${data.pipeline.logViewer.run.id}` : "None"}
          </span>
        </div>

        <div class="terminal-card mt-4 p-4">
          {#if data.pipeline.logViewer.run}
            <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-terminal-text-faint">
              <span class="terminal-chip">{humanizeCommand(data.pipeline.logViewer.run.command)}</span>
              <span class="terminal-chip">{runStatusLabel(data.pipeline.logViewer.run.status)}</span>
              <span class="terminal-chip">PID {data.pipeline.logViewer.run.pid ?? "?"}</span>
            </div>
            <pre
              class="terminal-card max-h-120 overflow-x-auto overflow-y-auto whitespace-pre p-4 text-xs leading-6 text-terminal-text">{data
                .pipeline.logViewer.tail}</pre>
            <div class="mt-3 text-xs text-terminal-text-faint" title={data.pipeline.logViewer.path ?? undefined}>
              {data.pipeline.logViewer.path}
            </div>
          {:else}
            <div class="terminal-card border-dashed p-4 text-sm text-terminal-text-muted">No logs available yet.</div>
          {/if}
        </div>
      </div>
    </div>

    <div class="terminal-panel p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Recent runs</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-terminal-text">Last 12 jobs</h2>
        </div>
        <span class="terminal-chip">
          {data.pipeline.snapshot.recentRuns.length}
        </span>
      </div>

      {#if data.pipeline.snapshot.recentRuns.length === 0}
        <div class="terminal-card mt-5 border-dashed p-4 text-sm text-terminal-text-muted">
          No pipeline runs recorded yet.
        </div>
      {:else}
        <div class="terminal-card mt-5 overflow-hidden">
          <table class="w-full border-collapse text-left text-sm">
            <thead class="bg-terminal-bg-subtle text-terminal-text-faint">
              <tr>
                <th class="px-3 py-2 font-medium">Run</th>
                <th class="px-3 py-2 font-medium">Status</th>
                <th class="px-3 py-2 font-medium">Exit</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-terminal-border-subtle bg-terminal-bg-subtle">
              {#each data.pipeline.snapshot.recentRuns as run}
                <tr class={selectedRunId === run.id ? "bg-sky-500/5" : ""}>
                  <td class="px-3 py-2 align-top">
                    <a
                      href="?run={run.id}"
                      data-sveltekit-keepfocus
                      data-sveltekit-noscroll
                      class="block font-medium text-terminal-text hover:underline {selectedRunId === run.id
                        ? 'text-sky-500'
                        : ''}"
                    >
                      #{run.id} · {humanizeCommand(run.command)}
                    </a>
                    <div class="mt-1 text-xs text-terminal-text-faint">{formatTimestamp(run.started_at)}</div>
                  </td>
                  <td class="px-3 py-2 align-top text-terminal-text-muted">{runStatusLabel(run.status)}</td>
                  <td class="px-3 py-2 align-top text-terminal-text-muted">{run.exit_code ?? "—"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </section>

  <!-- Verified job runs -->
  <section class="terminal-panel p-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Actions</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-terminal-text">
          {data.controlHref.startsWith("/v2/") ? "Manual v2 runs" : "Verified job runs"}
        </h2>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-terminal-text-muted">
          Buttons open a verification dialog. The command name has to be typed before anything actually fires.
        </p>
      </div>
      {#if data.pipeline.snapshot.lock && !data.pipeline.snapshot.lock.stale}
        <div
          class="terminal-card border-amber-400/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-800 dark:text-amber-100"
        >
          Job running already. The buttons are disabled until the lock clears.
        </div>
      {/if}
    </div>

    {#if page.form?.message}
      <div class="terminal-card mt-6 p-4 text-sm text-terminal-text-muted">
        {page.form.message}
      </div>
    {/if}

    <div class="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {#each data.pipeline.commands as command}
        <button
          type="button"
          onclick={() => openCommand(command)}
          disabled={activeLock || !command.readiness.ready}
          class="terminal-card terminal-card--interactive flex h-full w-full flex-col justify-between p-4 text-left disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div>
            <div class="text-base font-semibold text-terminal-text">{command.label}</div>
            <div class="mt-2 text-sm leading-6 text-terminal-text-muted">{command.description}</div>
            {#if !command.readiness.ready}
              <div class="mt-3 space-y-1 text-xs leading-5 text-rose-500">
                {#each command.readiness.reasons as reason}
                  <div>{reason}</div>
                {/each}
              </div>
            {/if}
          </div>
          <div class="mt-4 text-xs uppercase tracking-[0.25em] text-terminal-text/35">
            {humanizeCommand(command.name)}
          </div>
        </button>
      {/each}
    </div>
  </section>

  <!-- Confirmation dialog -->
  {#if selectedCommand}
    <div class="fixed inset-0 z-50" aria-hidden="true">
      <button
        type="button"
        class="absolute inset-0 h-full w-full border-0 bg-black/60 p-0"
        aria-label="Close confirmation dialog"
        onclick={closeDialog}
      ></button>
      <div class="relative z-10 flex h-full items-center justify-center p-4">
        <div class="terminal-panel w-full max-w-md p-6 sm:p-8" role="document">
          <h2 class="text-2xl font-semibold tracking-tight text-terminal-text">Run {selectedCommand.label}</h2>
          <p class="mt-3 max-w-xl text-sm leading-6 text-terminal-text-muted">
            {selectedCommand.description}
          </p>

          <p class="mt-6 text-sm text-terminal-text-muted">
            Type <code class="rounded bg-terminal-bg-subtle px-1.5 py-0.5 font-mono text-terminal-text"
              >{selectedCommand.name}</code
            > to confirm:
          </p>

          <input
            type="text"
            bind:value={confirmValue}
            placeholder={selectedCommand.name}
            class="mt-3 w-full rounded border border-terminal-border bg-terminal-bg px-3 py-2 font-mono text-sm text-terminal-text outline-none transition-colors focus:border-terminal-text/40"
            onkeydown={(e) => {
              if (e.key === "Enter" && canConfirm) {
                e.preventDefault()
                const form = e.currentTarget?.closest("div")?.querySelector("form")
                form?.requestSubmit()
              }
            }}
          />

          <div class="mt-6 flex items-center justify-end gap-3">
            <button onclick={closeDialog} class="terminal-action text-sm">Cancel</button>
            <form method="post" action="?/run">
              <input type="hidden" name="command" value={selectedCommand.name} />
              <input type="hidden" name="confirm" value={confirmValue} />
              <button
                type="submit"
                disabled={!canConfirm}
                class="terminal-action disabled:cursor-not-allowed disabled:opacity-40"
              >
                Run
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Content Table -->
  {#if !data.v2}
  <section class="terminal-panel p-6">
    <ContentTable data={data.tableData} title="Pipeline Data" enableDetailLinks />
  </section>
  {/if}
</div>
