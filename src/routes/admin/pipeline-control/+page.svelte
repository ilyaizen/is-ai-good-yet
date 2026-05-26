<script lang="ts">
  import { page } from "$app/state"
  import ContentTable from "$lib/components/content-table.svelte"

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
      groqApiKeyConfigured: boolean
      mistralApiKeyConfigured: boolean
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
      stats: { totalUrls: number; resolved: number; scraped: number; relevant: number; analyzed: number; failed: number }
      tableData: UrlEntry[]
      pipeline: PipelineData
      controlHref: string
    }
  } = $props()

  let selectedCommand = $state<PipelineCommand | null>(null)
  let confirmValue = $state("")

  function humanizeCommand(command: string): string {
    return command.replaceAll("_", " ")
  }

  function runStatusLabel(status: string): string {
    if (status === "running") return "Running"
    if (status === "succeeded") return "Succeeded"
    if (status === "failed") return "Failed"
    if (status === "cancelled") return "Cancelled"
    if (status === "queued") return "Queued"
    return status
  }

  function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return "—"
    return timestamp.replace("T", " ").replace("Z", " UTC")
  }

  function phaseStatusLabel(status: StageStatus): string {
    if (status === "completed") return "Done"
    if (status === "active") return "Active"
    return "Waiting"
  }

  function stageTone(status: StageStatus): string {
    if (status === "completed") return "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
    if (status === "active") return "border-sky-400/20 bg-sky-500/10 text-sky-100"
    return "border-terminal-border-subtle bg-terminal-bg-subtle text-white/55"
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
</script>

<svelte:head>
  <title>Pipeline Control - Is AI Good Yet?</title>
</svelte:head>

<div class="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
  <section class="terminal-panel p-6 sm:p-8">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-white/45">Admin</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Pipeline control</h1>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          This is the control room. The admin page is the overview. The data table lives here.
        </p>
      </div>

      <div class="flex flex-wrap gap-3">
        <a
          href={data.controlHref}
          class="terminal-action"
        >
          Back to admin
        </a>
        <form method="post" action="?/logout">
          <button
            type="submit"
            class="terminal-action"
          >
            Log out
          </button>
        </form>
      </div>
    </div>

    <div class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
      <div class="terminal-card p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-white/40">Total URLs</div>
        <div class="mt-2 text-3xl font-semibold text-white">{data.stats.totalUrls}</div>
      </div>
      <div class="terminal-card border-sky-400/20 bg-sky-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-sky-200/70">Resolved</div>
        <div class="mt-2 text-3xl font-semibold text-sky-100">{data.stats.resolved}</div>
      </div>
      <div class="terminal-card border-amber-400/20 bg-amber-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-amber-200/70">Scraped</div>
        <div class="mt-2 text-3xl font-semibold text-amber-100">{data.stats.scraped}</div>
      </div>
      <div class="terminal-card border-emerald-400/20 bg-emerald-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-emerald-200/70">Relevant</div>
        <div class="mt-2 text-3xl font-semibold text-emerald-100">{data.stats.relevant}</div>
      </div>
      <div class="terminal-card border-violet-400/20 bg-violet-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-violet-200/70">Analyzed</div>
        <div class="mt-2 text-3xl font-semibold text-violet-100">{data.stats.analyzed}</div>
      </div>
      <div class="terminal-card border-rose-400/20 bg-rose-500/5 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-rose-200/70">Failed</div>
        <div class="mt-2 text-3xl font-semibold text-rose-100">{data.stats.failed}</div>
      </div>
    </div>

    <div class="mt-6 flex flex-wrap gap-3 text-sm text-white/65">
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
          <div class="terminal-card border-amber-400/20 bg-amber-500/5 p-4 text-sm text-amber-50">
            Admin password is not configured. Set <code>PIPELINE_ADMIN_PASSWORD</code> first.
          </div>
        {/if}
        {#if !data.dbExists}
          <div class="terminal-card p-4 text-sm text-white/65">
            Pipeline DB is missing on this checkout. The dashboard will populate once <code>pipeline/data/pipeline.db</code> exists.
          </div>
        {/if}
      </div>
    {/if}
  </section>

  <section class="grid gap-4 xl:grid-cols-[1.25fr_.75fr]">
    <div class="terminal-panel p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/45">Pipeline</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Stage health</h2>
          <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
            Heuristic status from the checked-in data. The point is to see what is alive, not to babysit buttons.
          </p>
        </div>

        <div class="terminal-card px-4 py-3 text-sm text-white/65">
          {#if data.pipeline.snapshot.lock}
            <div class="font-medium text-white">
              {data.pipeline.snapshot.lock.stale ? "Stale lock" : "Active lock"}
            </div>
            <div class="mt-1">
              {data.pipeline.snapshot.lock.command} · PID {data.pipeline.snapshot.lock.pid ?? "?"}
            </div>
          {:else}
            <div class="font-medium text-white">Idle</div>
            <div class="mt-1">No pipeline job is running right now.</div>
          {/if}
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {#each stages as stage}
          <div class={`terminal-card terminal-card--interactive p-4 ${stageTone(stage.status)}`}>
            <div class="flex items-center justify-between gap-3">
              <div class="text-sm font-semibold">{stage.name}</div>
              <div class="terminal-chip text-[11px] uppercase tracking-[0.2em] text-white/55">
                {phaseStatusLabel(stage.status)}
              </div>
            </div>
            <p class="mt-3 text-sm leading-6 text-current/75">{stage.description}</p>
          </div>
        {/each}
      </div>
    </div>

    <div class="terminal-panel p-6">
      <p class="text-xs uppercase tracking-[0.3em] text-white/45">Environment</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Runtime checks</h2>
      <p class="mt-3 text-sm leading-6 text-white/65">If one of these is missing, the pipeline will be annoying in the usual ways.</p>

      <div class="mt-5 space-y-3 text-sm">
        {#each [
          ["Repo root", data.pipeline.env.repoRootExists],
          ["Venv Python", data.pipeline.env.venvPythonExists],
          ["Pipeline dir", data.pipeline.env.pipelineDirExists],
          ["Admin DB", data.pipeline.env.adminDbExists],
          ["Logs dir", data.pipeline.env.logDirExists],
          ["Groq key", data.pipeline.env.groqApiKeyConfigured],
          ["Mistral key", data.pipeline.env.mistralApiKeyConfigured],
        ] as [label, ok]}
          <div class="terminal-card flex items-center justify-between gap-4 px-4 py-3">
            <span class="text-white/70">{label}</span>
            <span class={`terminal-chip text-xs font-medium ${ok ? "bg-emerald-500/15 text-emerald-100" : "bg-rose-500/15 text-rose-100"}`}>
              {ok ? "OK" : "Missing"}
            </span>
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="grid gap-4 xl:grid-cols-[1fr_.9fr]">
    <div class="terminal-panel p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/45">Current run</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Latest job state</h2>
        </div>
        <span class="terminal-chip">
          {data.pipeline.snapshot.currentRun ? runStatusLabel(data.pipeline.snapshot.currentRun.status) : "Idle"}
        </span>
      </div>

      {#if data.pipeline.snapshot.currentRun}
        <dl class="mt-5 space-y-3 text-sm text-white/70">
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-white/45">Run</dt>
            <dd class="text-right text-white">#{data.pipeline.snapshot.currentRun.id}</dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-white/45">Command</dt>
            <dd class="text-right text-white">{humanizeCommand(data.pipeline.snapshot.currentRun.command)}</dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-white/45">Started</dt>
            <dd class="text-right text-white">{formatTimestamp(data.pipeline.snapshot.currentRun.started_at)}</dd>
          </div>
          <div class="terminal-card flex items-start justify-between gap-4 px-4 py-3">
            <dt class="text-white/45">Log</dt>
            <dd class="max-w-[18rem] truncate text-right text-white/70" title={data.pipeline.snapshot.currentRun.log_path}>
              {data.pipeline.snapshot.currentRun.log_path}
            </dd>
          </div>
          {#if data.pipeline.snapshot.currentRun.error}
            <div class="terminal-card border-rose-400/20 bg-rose-500/5 p-4 text-rose-100">
              {data.pipeline.snapshot.currentRun.error}
            </div>
          {/if}
        </dl>
      {:else}
        <div class="terminal-card mt-5 border-dashed p-4 text-sm text-white/55">
          No active run. Start a job below if you need to move the data forward.
        </div>
      {/if}

      <div class="terminal-card mt-6 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-white">Log tail</h3>
            <p class="mt-1 text-sm text-white/55">The real subprocess output, not an invented summary.</p>
          </div>
          <span class="terminal-chip">
            {data.pipeline.logViewer.run ? `#${data.pipeline.logViewer.run.id}` : "None"}
          </span>
        </div>

        <div class="terminal-card mt-4 p-4">
          {#if data.pipeline.logViewer.run}
            <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-white/50">
              <span class="terminal-chip">{humanizeCommand(data.pipeline.logViewer.run.command)}</span>
              <span class="terminal-chip">{runStatusLabel(data.pipeline.logViewer.run.status)}</span>
              <span class="terminal-chip">PID {data.pipeline.logViewer.run.pid ?? "?"}</span>
            </div>
            <pre class="terminal-card max-h-[30rem] overflow-auto whitespace-pre-wrap break-words p-4 text-xs leading-6 text-emerald-100">{data.pipeline.logViewer.tail}</pre>
            <div class="mt-3 text-xs text-white/45" title={data.pipeline.logViewer.path ?? undefined}>
              {data.pipeline.logViewer.path}
            </div>
          {:else}
            <div class="terminal-card border-dashed p-4 text-sm text-white/55">
              No logs available yet.
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="terminal-panel p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/45">Recent runs</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Last 12 jobs</h2>
        </div>
        <span class="terminal-chip">
          {data.pipeline.snapshot.recentRuns.length}
        </span>
      </div>

      {#if data.pipeline.snapshot.recentRuns.length === 0}
        <div class="terminal-card mt-5 border-dashed p-4 text-sm text-white/55">
          No pipeline runs recorded yet.
        </div>
      {:else}
        <div class="terminal-card mt-5 overflow-hidden">
          <table class="w-full border-collapse text-left text-sm">
            <thead class="bg-terminal-bg-subtle text-white/45">
              <tr>
                <th class="px-3 py-2 font-medium">Run</th>
                <th class="px-3 py-2 font-medium">Status</th>
                <th class="px-3 py-2 font-medium">Exit</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5 bg-black/15">
              {#each data.pipeline.snapshot.recentRuns as run}
                <tr>
                  <td class="px-3 py-2 align-top">
                    <div class="font-medium text-white">#{run.id} · {humanizeCommand(run.command)}</div>
                    <div class="mt-1 text-xs text-white/45">{formatTimestamp(run.started_at)}</div>
                  </td>
                  <td class="px-3 py-2 align-top text-white/70">{runStatusLabel(run.status)}</td>
                  <td class="px-3 py-2 align-top text-white/70">{run.exit_code ?? "—"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </section>

  <section class="terminal-panel p-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-white/45">Actions</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Verified job runs</h2>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          Buttons open a verification dialog. The command name has to be typed before anything actually fires.
        </p>
      </div>
      {#if data.pipeline.snapshot.lock && !data.pipeline.snapshot.lock.stale}
        <div class="terminal-card border-amber-400/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-50">
          Job running already. The buttons are disabled until the lock clears.
        </div>
      {/if}
    </div>

    {#if page.form?.message}
      <div class="terminal-card mt-6 p-4 text-sm text-white/65">
        {page.form.message}
      </div>
    {/if}

    <div class="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {#each data.pipeline.commands as command}
        <button
          type="button"
          onclick={() => openCommand(command)}
          disabled={activeLock}
          class="terminal-card terminal-card--interactive flex h-full w-full flex-col justify-between p-4 text-left disabled:cursor-not-allowed disabled:opacity-50"
        >
          <div>
            <div class="text-base font-semibold text-white">{command.label}</div>
            <div class="mt-2 text-sm leading-6 text-white/60">{command.description}</div>
          </div>
          <div class="mt-4 text-xs uppercase tracking-[0.25em] text-white/35">{humanizeCommand(command.name)}</div>
        </button>
      {/each}
    </div>
  </section>

  <section class="terminal-panel p-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-white/45">Registry</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Content table</h2>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          This is the actual data table. Filters, detail links, and the usual junk live here.
        </p>
      </div>
      <div class="terminal-card px-4 py-3 text-sm text-white/65">
        {data.tableData.length} rows loaded
      </div>
    </div>

    <div class="terminal-card mt-6 overflow-hidden">
      <ContentTable data={data.tableData} enableDetailLinks={true} title="Pipeline Data Registry" syncWithUrl={true} />
    </div>
  </section>
</div>

{#if selectedCommand}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 py-6 backdrop-blur-sm">
    <div class="w-full max-w-xl terminal-panel p-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-white/45">Verify job</p>
          <h3 class="mt-2 text-2xl font-semibold tracking-tight text-white">{selectedCommand.label}</h3>
        </div>
        <button
          type="button"
          onclick={closeDialog}
          class="terminal-action px-3 py-2"
          aria-label="Close dialog"
        >
          ✕
        </button>
      </div>

      <p class="mt-4 text-sm leading-6 text-white/65">
        This is a real subprocess run. Type <code class="terminal-chip px-1.5 py-0.5 text-white">{selectedCommand.name}</code> to unlock the button.
      </p>

      <form method="post" action="?/run" class="mt-6 space-y-4">
        <input type="hidden" name="command" value={selectedCommand.name} />
        <label class="block">
          <span class="text-sm font-medium text-white/80">Verification</span>
          <input
            bind:value={confirmValue}
            name="confirm"
            autocomplete="off"
            spellcheck="false"
            placeholder={selectedCommand.name}
            class="terminal-input mt-2"
          />
        </label>

        <div class="terminal-card px-4 py-3 text-sm text-white/65">
          {#if activeLock}
            A job is already running. This dialog will still let you submit, but the backend will reject it.
          {:else}
            The button stays locked until the exact command name matches.
          {/if}
        </div>

        <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            onclick={closeDialog}
            class="terminal-action"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canConfirm}
            class="terminal-action border-emerald-400/20 bg-emerald-500/5 text-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Run {selectedCommand.label}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
