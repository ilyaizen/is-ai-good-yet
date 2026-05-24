# Pipeline admin and scheduling plan

> **For Hermes:** Use `claude-code` for implementation, then review with `systematic-debugging` and `requesting-code-review` before committing runtime changes.

**Goal:** Turn the manual Python scraper/analyzer pipeline into a controlled local admin workflow for the SvelteKit site.

**Architecture:** Keep the public site mostly static/data-driven. Add an authenticated admin surface that can inspect pipeline state, start safe bounded runs, show logs, and expose schedule status. Execute Python as explicit subprocesses behind a lock; do not embed scraper logic inside SvelteKit.

**Tech Stack:** SvelteKit adapter-node, Node subprocess APIs, SQLite, Python venv, Playwright, Groq, systemd timer or Hermes cron.

---

## Non-goals

- No Kubernetes.
- No distributed queue.
- No browser-based arbitrary command runner.
- No unauthenticated admin route.
- No rewrite of the pipeline into TypeScript.
- No new database if SQLite is enough.

This box has 4 GB RAM. Design like it.

## Current facts

- App runtime: `npm` + Node + SvelteKit adapter-node.
- Pipeline source: `pipeline/`.
- Manual phase modules: `pipeline/src/*.py`.
- Placeholder orchestration: `pipeline/run.py` exists but does not call real phases yet.
- DB artifact: `pipeline/data/pipeline.db`.
- Some frontend/server scripts already read SQLite through `better-sqlite3`.
- Production checkout should be `/srv/apps/is-ai-good-yet`.

## Recommended implementation

### 1. Normalize Python execution

Create one repo-local script/module that owns Python command construction.

Suggested file:

- `src/lib/server/pipeline/python.ts`

Responsibilities:

- resolve repo root
- resolve `.venv/bin/python`
- resolve `pipeline/` cwd
- expose named commands only, not arbitrary shell strings
- inject minimal env from process env
- stream stdout/stderr to a run log

Allowed command names initially:

- `catch_up`
- `scrape`
- `clean_articles`
- `prefilter_content`
- `sentiment_analyzer`
- `export`
- `test`

YAGNI: do not model every historical script on day one.

### 2. Add run state storage

Use SQLite. Either reuse `pipeline/data/pipeline.db` if the schema boundary is acceptable, or create a separate app-side DB at `pipeline/data/admin.db`.

Default recommendation: separate `pipeline/data/admin.db` for run metadata. It avoids polluting analysis data and keeps admin state disposable.

Tables:

```sql
create table if not exists pipeline_runs (
  id integer primary key autoincrement,
  command text not null,
  status text not null check (status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  started_at text,
  finished_at text,
  exit_code integer,
  log_path text not null,
  error text
);

create table if not exists pipeline_locks (
  id integer primary key check (id = 1),
  run_id integer,
  acquired_at text not null
);
```

Keep logs as files under `pipeline/data/logs/`. Store paths in SQLite. Do not shove megabytes of logs into the DB.

### 3. Add a single-run lock

Before starting a run:

1. open `admin.db`
2. begin immediate transaction
3. check `pipeline_locks`
4. insert lock row if absent
5. create run row
6. commit
7. spawn process

On completion, update run row and release lock.

If the process dies weirdly, a stale lock can be cleared manually from the admin page only if the PID is dead or the lock is older than a conservative threshold.

### 4. Wire the admin route

Suggested route:

- `src/routes/admin/pipeline/+page.server.ts`
- `src/routes/admin/pipeline/+page.svelte`
- `src/routes/admin/pipeline/+server.ts` only if a JSON endpoint is cleaner

UI sections:

- current status: idle/running/stale lock/missing DB/missing venv/missing env
- last run summary
- buttons for allowed commands
- recent run list
- selected run log tail
- schedule status
- export freshness: timestamp and file count

Use boring server actions first. Add polling later only if needed.

### 5. Protect the admin page

Use a single admin secret first:

- env: `PIPELINE_ADMIN_TOKEN`
- cookie: httpOnly, sameSite=lax, secure in production
- route guard in `hooks.server.ts` or route-level `load`

This is not a user platform. Do not invent accounts/roles yet.

### 6. Fix `pipeline/run.py` after admin basics

Once admin execution works, make `pipeline/run.py` a real orchestrator over the existing phase modules.

Expected contract:

```bash
python3 pipeline/run.py --phase ingest
python3 pipeline/run.py --phase scrape
python3 pipeline/run.py --phase analyze
python3 pipeline/run.py --phase export
python3 pipeline/run.py --phase catch-up
python3 pipeline/run.py --phase all
```

Each phase should call one narrow module/function and return a clear exit code.

### 7. Add scheduling

Default recommendation: systemd timer on the host for catch-up/export, because it is simple and visible.

Example shape:

- service: `is-ai-good-yet-pipeline.service`
- timer: `is-ai-good-yet-pipeline.timer`
- command: run a repo-local script that calls the same admin runner or `pipeline/run.py`
- schedule: once or twice daily, not every few minutes

Hermes cron is acceptable for notifications and watchdogs. It should not be the first scheduler for core production data generation unless we explicitly want agent involvement.

## Bite-sized implementation tasks

### Task 1: Add environment/status probe

Files:

- Create: `src/lib/server/pipeline/status.ts`
- Modify: `src/routes/admin/pipeline/+page.server.ts`

Implement checks for:

- `.venv/bin/python` exists
- `pipeline/requirements.txt` exists
- `pipeline/data/pipeline.db` exists
- `PIPELINE_ADMIN_TOKEN` configured
- `GROQ_API_KEY` visible to the app process

Verification:

```bash
npm run check
npm run build
```

### Task 2: Add admin auth

Files:

- Create or modify: `src/hooks.server.ts`
- Create: `src/routes/admin/+layout.server.ts`
- Create: `src/routes/admin/login/+page.server.ts`
- Create: `src/routes/admin/login/+page.svelte`

Use `PIPELINE_ADMIN_TOKEN`. Keep it ugly and secure before making it pretty.

Verification:

- unauthenticated `/admin/pipeline` redirects to login
- correct token sets cookie
- wrong token fails without leaking details

### Task 3: Add run DB and lock

Files:

- Create: `src/lib/server/pipeline/admin-db.ts`
- Create: `src/lib/server/pipeline/lock.ts`

Implement schema bootstrap, lock acquire/release, stale lock inspection.

Verification:

- unit tests or a small script proves duplicate lock acquisition fails
- stale lock display is read-only at first

### Task 4: Add subprocess runner

Files:

- Create: `src/lib/server/pipeline/runner.ts`

Implement named command execution only. No arbitrary args from the browser.

Verification:

```bash
npm run check
node -e "console.log('runner import smoke test')"
```

### Task 5: Add admin page actions

Files:

- Modify: `src/routes/admin/pipeline/+page.server.ts`
- Modify: `src/routes/admin/pipeline/+page.svelte`

Actions:

- run catch-up
- run scrape
- run analyze
- run export
- show recent runs
- show log tail

Verification:

- starting one run disables other run buttons
- second run request returns a locked/running message
- failed process is visible with exit code and log path

### Task 6: Wire `pipeline/run.py`

Files:

- Modify: `pipeline/run.py`
- Possibly modify phase modules to expose clean `main()`/`main_async()` functions

Keep compatibility with direct module commands.

Verification:

```bash
cd pipeline
../.venv/bin/python ../pipeline/run.py --phase export
```

### Task 7: Add systemd timer docs

Files:

- Create: `Agents/systemd-pipeline.md` or extend this file

Document service/timer, environment file, working directory, log paths, and rollback.

Verification:

```bash
systemctl status is-ai-good-yet-pipeline.timer
journalctl -u is-ai-good-yet-pipeline.service -n 100 --no-pager
```

## UX notes

Make the admin page operational, not cute:

- clear status pills
- visible last run time
- visible currently running command
- log tail with monospace text
- explicit missing-prerequisite warnings
- disabled buttons when unsafe
- manual refresh first; polling later if annoying

Good motion here is tiny: button pending states, log-tail update fade, status pill transitions. Anything more is dashboard cosplay.

## Commit strategy

1. docs/spec commit
2. admin auth/status commit
3. run DB/lock commit
4. subprocess runner commit
5. admin actions/UI commit
6. `pipeline/run.py` orchestration commit
7. systemd timer/docs commit

Each commit must pass `npm run check` and any relevant Python smoke tests.
