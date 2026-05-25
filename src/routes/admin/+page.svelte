<script lang="ts">
  import { page } from "$app/state"

  type LinkRow = {
    title: string
    url: string
    domain: string
    hnId: number | null
    hnScore: number | null
    hnComments: number | null
    hnTimestamp: number | null
    category: string | null
    status: string
    opinion: string | null
    summary: string
    reason: string
    refusalStage: "prefilter" | "classifier" | "category" | "unknown"
  }

  type PipelineCommand = {
    name: string
    label: string
    description: string
  }

  type PipelineRunRow = {
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

  type PipelineLockRow = {
    id: number
    run_id: number | null
    command: string
    pid: number | null
    acquired_at: string
    stale: boolean
  }

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
      currentRun: PipelineRunRow | null
      lock: PipelineLockRow | null
      recentRuns: PipelineRunRow[]
    }
    commands: PipelineCommand[]
    logViewer: {
      run: PipelineRunRow | null
      path: string | null
      exists: boolean
      tail: string
    }
  }

  let {
    data,
  }: {
    data: {
      configured: boolean
      dbExists: boolean
      counts: { total: number; approved: number; refused: number; pending: number; other: number }
      refusedLinks: LinkRow[]
      recentLinks: LinkRow[]
      pipeline: PipelineData
    }
  } = $props()

  function formatDate(timestamp: number | null): string {
    if (!timestamp) return "—"
    return new Date(timestamp * 1000).toISOString().split("T")[0]
  }

  function formatTimeAgo(timestamp: number | null): string {
    if (!timestamp) return "—"

    const diffMs = Date.now() - timestamp * 1000
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays < 1) return "today"
    if (diffDays < 7) return `${diffDays}d ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`
    return `${Math.floor(diffDays / 365)}y ago`
  }

  function formatCategory(category: string | null): string {
    if (!category) return "pending"
    return category.toLowerCase().replaceAll("_", " ")
  }

  function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return "—"
    return timestamp.replace("T", " ").replace("Z", " UTC")
  }

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
</script>

<svelte:head>
  <title>Admin - Is AI Good Yet?</title>
</svelte:head>

<div class="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
  <section class="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-sm sm:p-8">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-white/45">Admin</p>
        <h1 class="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Pipeline control</h1>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          Single-user admin view. No accounts, no roles, no fake enterprise theater.
        </p>
      </div>

      <form method="post" action="?/logout">
        <button
          type="submit"
          class="rounded-2xl border border-white/10 bg-black/30 px-4 py-2 text-sm font-medium text-white transition hover:border-white/20 hover:bg-black/40"
        >
          Log out
        </button>
      </form>
    </div>

    <div class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div class="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-white/40">Total</div>
        <div class="mt-2 text-3xl font-semibold text-white">{data.counts.total}</div>
      </div>
      <div class="rounded-2xl border border-emerald-400/20 bg-emerald-500/10 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-emerald-200/70">Approved</div>
        <div class="mt-2 text-3xl font-semibold text-emerald-100">{data.counts.approved}</div>
      </div>
      <div class="rounded-2xl border border-rose-400/20 bg-rose-500/10 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-rose-200/70">Refused</div>
        <div class="mt-2 text-3xl font-semibold text-rose-100">{data.counts.refused}</div>
      </div>
      <div class="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4">
        <div class="text-xs uppercase tracking-[0.25em] text-amber-200/70">Pending</div>
        <div class="mt-2 text-3xl font-semibold text-amber-100">{data.counts.pending}</div>
      </div>
    </div>

    <div class="mt-6 flex flex-wrap gap-3 text-sm text-white/65">
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">Password {data.configured ? "configured" : "missing"}</span>
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">DB {data.dbExists ? "found" : "missing"}</span>
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">Other {data.counts.other}</span>
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">Python {data.pipeline.env.venvPythonExists ? "found" : "missing"}</span>
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">Logs {data.pipeline.env.logDirExists ? "ready" : "missing"}</span>
      <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1">Admin DB {data.pipeline.env.adminDbExists ? "found" : "missing"}</span>
    </div>

    {#if !data.configured || !data.dbExists}
      <div class="mt-6 grid gap-3 sm:grid-cols-2">
        {#if !data.configured}
          <div class="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
            Admin password is not configured. Set <code>PIPELINE_ADMIN_PASSWORD</code> first.
          </div>
        {/if}
        {#if !data.dbExists}
          <div class="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-white/65">
            Pipeline DB is missing on this checkout. The dashboard will populate once <code>pipeline/data/pipeline.db</code> exists.
          </div>
        {/if}
      </div>
    {/if}
  </section>

  <section class="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-sm">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.3em] text-white/45">Pipeline</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-white">Run named jobs</h2>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-white/65">
          These are real subprocess runs against the repo venv and the pipeline working directory. No shell textbox, no arbitrary commands.
        </p>
      </div>
      <div class="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/65">
        {#if data.pipeline.snapshot.lock}
          <div class="font-medium text-white">
            {data.pipeline.snapshot.lock.stale ? "Stale lock" : "Active run"}
          </div>
          <div class="mt-1">{data.pipeline.snapshot.lock.command} · PID {data.pipeline.snapshot.lock.pid ?? "?"}</div>
        {:else}
          <div class="font-medium text-white">Idle</div>
          <div class="mt-1">No run is active right now.</div>
        {/if}
      </div>
    </div>

    {#if page.form?.message}
      <div class="mt-6 rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm text-white/80">
        {page.form.message}
      </div>
    {/if}

    <div class="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {#each data.pipeline.commands as command}
        <form method="post" action="?/run" class="h-full">
          <input type="hidden" name="command" value={command.name} />
          <button
            type="submit"
            disabled={Boolean(data.pipeline.snapshot.lock && !data.pipeline.snapshot.lock.stale)}
            class="flex h-full w-full flex-col justify-between rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-white/20 hover:bg-black/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <div>
              <div class="text-base font-semibold text-white">{command.label}</div>
              <div class="mt-2 text-sm leading-6 text-white/60">{command.description}</div>
            </div>
            <div class="mt-4 text-xs uppercase tracking-[0.25em] text-white/35">{humanizeCommand(command.name)}</div>
          </button>
        </form>
      {/each}
    </div>

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
      <div class="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-white">Current run</h3>
            <p class="mt-1 text-sm text-white/55">Latest active job metadata from the admin DB.</p>
          </div>
          <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
            {data.pipeline.snapshot.currentRun ? runStatusLabel(data.pipeline.snapshot.currentRun.status) : "Idle"}
          </span>
        </div>

        {#if data.pipeline.snapshot.currentRun}
          <dl class="mt-4 space-y-3 text-sm text-white/70">
            <div class="flex items-start justify-between gap-4">
              <dt class="text-white/45">Run</dt>
              <dd class="text-right text-white">#{data.pipeline.snapshot.currentRun.id}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-white/45">Command</dt>
              <dd class="text-right text-white">{humanizeCommand(data.pipeline.snapshot.currentRun.command)}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-white/45">Started</dt>
              <dd class="text-right text-white">{formatTimestamp(data.pipeline.snapshot.currentRun.started_at)}</dd>
            </div>
            <div class="flex items-start justify-between gap-4">
              <dt class="text-white/45">Log</dt>
              <dd class="max-w-[18rem] truncate text-right text-white/70" title={data.pipeline.snapshot.currentRun.log_path}>
                {data.pipeline.snapshot.currentRun.log_path}
              </dd>
            </div>
            {#if data.pipeline.snapshot.currentRun.error}
              <div class="rounded-xl border border-rose-400/20 bg-rose-500/10 p-3 text-rose-100">
                {data.pipeline.snapshot.currentRun.error}
              </div>
            {/if}
          </dl>
        {:else}
          <div class="mt-4 rounded-2xl border border-dashed border-white/10 bg-black/15 p-4 text-sm text-white/55">
            No active run. Start one above.
          </div>
        {/if}
      </div>

      <div class="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-white">Log tail</h3>
            <p class="mt-1 text-sm text-white/55">Pick a run from the list and inspect the last lines of the real subprocess output.</p>
          </div>
          <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
            {data.pipeline.logViewer.run ? `#${data.pipeline.logViewer.run.id}` : "None"}
          </span>
        </div>

        <div class="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4">
          {#if data.pipeline.logViewer.run}
            <div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-white/50">
              <span class="rounded-full border border-white/10 bg-white/5 px-2 py-1">{humanizeCommand(data.pipeline.logViewer.run.command)}</span>
              <span class="rounded-full border border-white/10 bg-white/5 px-2 py-1">{runStatusLabel(data.pipeline.logViewer.run.status)}</span>
              <span class="rounded-full border border-white/10 bg-white/5 px-2 py-1">PID {data.pipeline.logViewer.run.pid ?? "?"}</span>
            </div>
            <pre class="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-2xl bg-black/40 p-4 text-xs leading-6 text-emerald-100">{data.pipeline.logViewer.tail}</pre>
            <div class="mt-3 text-xs text-white/45" title={data.pipeline.logViewer.path ?? undefined}>
              {data.pipeline.logViewer.path}
            </div>
          {:else}
            <div class="rounded-2xl border border-dashed border-white/10 bg-black/15 p-4 text-sm text-white/55">
              No logs available yet.
            </div>
          {/if}
        </div>
      </div>

      <div class="rounded-2xl border border-white/10 bg-black/20 p-4">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold text-white">Recent runs</h3>
            <p class="mt-1 text-sm text-white/55">Newest first. Shows the actual subprocess outcome.</p>
          </div>
          <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">
            {data.pipeline.snapshot.recentRuns.length}
          </span>
        </div>

        {#if data.pipeline.snapshot.recentRuns.length === 0}
          <div class="mt-4 rounded-2xl border border-dashed border-white/10 bg-black/15 p-4 text-sm text-white/55">
            No pipeline runs recorded yet.
          </div>
        {:else}
          <div class="mt-4 overflow-hidden rounded-2xl border border-white/10">
            <table class="w-full border-collapse text-left text-sm">
              <thead class="bg-black/25 text-white/45">
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
                      <a href={`?run=${run.id}`} class="mt-2 inline-flex text-xs font-medium text-emerald-200 hover:underline">
                        View log
                      </a>
                    </td>
                    <td class="px-3 py-2 align-top text-white/70">{runStatusLabel(run.status)}</td>
                    <td class="px-3 py-2 align-top text-white/70">
                      {run.exit_code ?? "—"}
                      {#if run.error}
                        <div class="mt-1 max-w-[18rem] truncate text-xs text-rose-200" title={run.error}>{run.error}</div>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
  </section>

  <section class="grid gap-6 xl:grid-cols-2">
    <div class="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-sm">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-xl font-semibold text-white">Refused by analysis</h2>
          <p class="mt-1 text-sm text-white/55">These links were classified away from AI discourse.</p>
        </div>
        <span class="rounded-full border border-rose-400/20 bg-rose-500/10 px-3 py-1 text-xs font-medium text-rose-100">
          {data.refusedLinks.length}
        </span>
      </div>

      {#if data.refusedLinks.length === 0}
        <div class="mt-6 rounded-2xl border border-dashed border-white/10 bg-black/20 p-6 text-sm text-white/55">
          No refused links in the current DB snapshot. Either the DB is empty or the pipeline hasn't classified anything yet.
        </div>
      {:else}
        <div class="mt-6 space-y-3">
          {#each data.refusedLinks as row}
            <article class="rounded-2xl border border-white/10 bg-black/20 p-4">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div class="min-w-0 space-y-1">
                  <div class="flex flex-wrap items-center gap-2 text-xs text-white/45">
                    <span class="rounded-full bg-white/5 px-2 py-1 uppercase tracking-[0.2em]">{formatCategory(row.category)}</span>
                    <span>{row.domain}</span>
                    {#if row.hnId}
                      <span>HN {row.hnId}</span>
                    {/if}
                  </div>
                  <h3 class="text-base font-semibold text-white">
                    {#if row.hnId}
                      <a href={`/details/${row.hnId}`} class="hover:underline">
                        {row.title}
                      </a>
                    {:else}
                      {row.title}
                    {/if}
                  </h3>
                  <p class="text-sm leading-6 text-white/60">{row.reason}</p>
                </div>

                <div class="shrink-0 text-right text-xs text-white/45">
                  <div>{formatTimeAgo(row.hnTimestamp)}</div>
                  <div class="mt-1">{formatDate(row.hnTimestamp)}</div>
                </div>
              </div>

              <div class="mt-4 flex flex-wrap items-center gap-2 text-xs">
                <a
                  href={row.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/70 transition hover:border-white/20 hover:bg-white/10"
                >
                  Original
                </a>
                {#if row.hnId}
                  <a
                    href={`/details/${row.hnId}`}
                    class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/70 transition hover:border-white/20 hover:bg-white/10"
                  >
                    Story page
                  </a>
                {/if}
                <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/55">Stage: {row.refusalStage}</span>
                <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/55">Status: {row.status}</span>
                {#if row.opinion}
                  <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-white/55">Opinion: {row.opinion}</span>
                {/if}
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </div>

    <div class="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-sm">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-xl font-semibold text-white">Recent links</h2>
          <p class="mt-1 text-sm text-white/55">Current pipeline snapshot, newest first.</p>
        </div>
        <span class="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-medium text-white/70">
          {data.recentLinks.length}
        </span>
      </div>

      <div class="mt-6 overflow-hidden rounded-2xl border border-white/10">
        <table class="w-full border-collapse text-left text-sm">
          <thead class="bg-black/25 text-white/45">
            <tr>
              <th class="px-4 py-3 font-medium">Link</th>
              <th class="px-4 py-3 font-medium">Class</th>
              <th class="px-4 py-3 font-medium">Score</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5 bg-black/15">
            {#each data.recentLinks as row}
              <tr>
                <td class="px-4 py-3 align-top">
                  <div class="font-medium text-white">{row.title}</div>
                  <div class="mt-1 text-xs text-white/45">{row.domain}</div>
                </td>
                <td class="px-4 py-3 align-top text-white/70">{formatCategory(row.category)}</td>
                <td class="px-4 py-3 align-top text-white/70">
                  {row.hnScore ?? "—"}
                  <span class="text-white/40">/ {row.hnComments ?? "—"}</span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </section>
</div>
