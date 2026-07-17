# Plan 002: Make the V2 admin page use the V2 design system exclusively

> **Executor instructions**: Read this entire plan before editing. Repository policy
> (see `AGENTS.md` §"Testing / Committing") requires **explicit user confirmation
> before running any check, lint, type-check, or build command**. So implement the
> edits, then STOP and ask the user before running `vp run check` / `vp lint`.
> Committing also requires a separate explicit confirmation. Follow every step in
> order; run each read-only `grep` verification and confirm the expected result
> before moving on. If anything in "STOP conditions" occurs, stop and report — do
> not improvise.
>
> **Drift check (run first, read-only)**:
> `git diff --stat 3e33cac..HEAD -- src/lib/components/v2/v2-admin-methodology.svelte src/routes/v2/admin/login/+page.svelte src/routes/v2/admin/+page.svelte src/styles/v2.css`
> (Note: commit `3e33cac` already includes the methodology prompt-reflow WIP; the
> "Current state" excerpts below match that committed base.)
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a material
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (presentation-only; no data, server, or pipeline logic changes)
- **Depends on**: none (independent of `plans/001-*.md`, which is pipeline-only)
- **Category**: tech-debt, dx
- **Planned at**: commit `3e33cac`, 2026-07-17 (re-based onto the committed methodology reflow WIP)

## Why this matters

`/v2/admin` renders two different design systems on one page. The observability
section is built in the V2 broadcast-terminal system (`--v2-*` tokens, mono type,
flat section cards, phosphor accent). The methodology section directly below it
is built in the V1 system (`--terminal-*` tokens, Tailwind utilities,
`terminal-panel/card/chip`, sans-serif headings, translucent shadowed cards).
The login page re-imports the entire V1 login (`amber-*` / `rose-*` colors,
`terminal-input/action`).

They cohere only because a fragile `.v2-admin { --terminal-bg: var(--v2-surface-1); … }`
block in `src/styles/v2.css` remaps ~10 V1 tokens to V2 values. That bridge is
incomplete (it omits `--terminal-btn-*`, so buttons/inputs still render with V1
colors) and is exactly the kind of V1/V2 coupling the project rules forbid
(`AGENTS.md`: _"V2 isolation… never reuse V1 contracts"_). The result reads as
two apps stitched together: mismatched container widths, border radii, elevation,
type voice, and badge/pill styles.

This plan makes V2 admin use the V2 design system exclusively and removes the
token bridge, so the page is one consistent design and the V1 terminal system is
no longer dragged into V2.

## Current state

### Files in scope (the only files you will modify)

- `src/lib/components/v2/v2-admin-methodology.svelte` — methodology viewer.
  Presentation only. **Keep the entire `<script>` block unchanged** (`reflowPrompt`,
  the `stages` derived array, the `Methodology` interface, `$props`). Only the
  markup and the scoped `<style>` change.
- `src/routes/v2/admin/login/+page.svelte` — the V2 login route view. Currently a
  thin re-export of the V1 login. Will become a self-contained V2-native form.
  **Keep `+page.server.ts` unchanged** (it re-exports V1 `load`/`actions` — that is
  server logic, intentionally shared, and out of scope).
- `src/styles/v2.css` — remove the `.v2-admin { … }` token-bridge block (the only
  edit to this file).

### Out of scope (do NOT touch)

- `src/routes/admin/login/+page.svelte` — the V1 login, still served at
  `/admin/login`. V1 must stay stable. The V2 route will simply stop importing it.
- `src/lib/components/v2/v2-admin-observability.svelte` — already V2-native; it is
  the **exemplar** to match, not a target. Do not restyle it.
- `src/routes/v2/admin/+page.svelte` and `+layout.server.ts` — no change needed
  (they just compose the two components).
- Any pipeline, server, data, or type-contract code. No props, no data shapes.

### Excerpt A — methodology is V1-styled (the thing to rewrite)

`src/lib/components/v2/v2-admin-methodology.svelte` — current outer markup:

```svelte
<section class="mx-auto max-w-7xl px-4 pb-12 sm:px-6 lg:px-8" aria-labelledby="v2-methodology-title">
  <div class="terminal-panel overflow-hidden">
    <header class="border-b border-terminal-border-subtle p-6 sm:p-8">
      <p class="text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Methodology</p>
      …
      <div class="terminal-chip self-start lg:self-auto">Analysis {methodology.versions.analysis}</div>
    </header>
    …
    <div class="terminal-card flex justify-between gap-4 px-4 py-3">
      <dt class="text-terminal-text-muted">Model</dt>
      <dd class="text-right text-terminal-text">{methodology.model}</dd>
    </div>
    …
```

… and its scoped `<style>` uses V1 tokens:

```css
.method-flow__node {
  border: 1px solid var(--terminal-border-subtle);
  background: var(--terminal-bg);
}
.method-flow__arrow {
  color: var(--terminal-accent);
}
```

### Excerpt B — login is a V1 transplant (the thing to rewrite)

`src/routes/v2/admin/login/+page.svelte` — the whole file:

```svelte
<script lang="ts">
  import type { PageData } from "./$types";
  import AdminLogin from "../../../admin/login/+page.svelte";

  let { data }: { data: PageData } = $props();
</script>

<div class="v2-admin">
  <AdminLogin {data} />
</div>
```

The imported V1 login (`src/routes/admin/login/+page.svelte`, OUT OF SCOPE — do not
edit, only read) uses: `terminal-panel`, `terminal-input`, `terminal-action`,
`text-xs uppercase tracking-[0.3em]`, and hardcoded Tailwind colors
`border-amber-400/30`, `bg-amber-500/10`, `text-amber-800 dark:text-amber-100`,
`text-rose-700 dark:text-rose-300`. Its `<script>` logic to reproduce in the new
V2 view:

```svelte
import { enhance } from "$app/forms";
import { page } from "$app/state";
let { data }: { data: { configured: boolean; next: string } } = $props();
let password = $state("");
```

…with a `<form method="post" use:enhance>` containing a hidden `next` input, a
password input bound to `password`, a `page.form?.message` error line, and a
submit button `disabled={!data.configured}`.

### Excerpt C — the token bridge to remove

`src/styles/v2.css`, near the end of the file:

```css
.v2-admin {
  --terminal-bg: var(--v2-surface-1);
  --terminal-bg-subtle: var(--v2-recess);
  --terminal-bg-header: var(--v2-surface-2);
  --terminal-border: var(--v2-separator);
  --terminal-border-strong: var(--v2-phosphor);
  --terminal-border-subtle: var(--v2-separator-quiet);
  --terminal-text: var(--v2-text);
  --terminal-text-muted: var(--v2-text-muted);
  --terminal-text-faint: var(--v2-text-faint);
  --terminal-accent: var(--v2-phosphor);
  min-height: 100vh;
}
```

### The target design language (exemplars to match — copy these exact values)

These are the V2 patterns the rewritten components must reproduce. They come from
`v2-admin-observability.svelte` (scoped) and `src/styles/v2.css` (global). The
executor will re-declare the scoped ones in the methodology component's own
`<style>` (Svelte scopes per-component, so they cannot be shared by class name).

Section card (match `v2-admin-observability.svelte`):

```css
.v2-admin-section {
  margin-top: 1.25rem;
  border: 1px solid var(--v2-separator);
  border-radius: 0.65rem;
  background: color-mix(in srgb, var(--v2-text) 1.5%, transparent);
  overflow: hidden;
}
```

Section header (match `v2-admin-observability.svelte`):

```css
/* kicker label */
font:
  500 0.68rem/1.4 ui-monospace,
  monospace;
letter-spacing: 0.18em;
color: var(--v2-text-faint);
/* h2 */
font-size: 1.35rem;
font-weight: 510;
letter-spacing: -0.025em;
color: var(--v2-text);
```

V2 card idiom (from global `.v2-bot-card` / `.v2-story-card` in `v2.css`) — use for
stage nodes and the login card:

```css
background: var(--v2-surface-1);
border-left: 2px solid var(--v2-phosphor);
box-shadow:
  inset 0 1px var(--v2-separator-quiet),
  var(--v2-shadow);
```

Key-value hairline grid (match `v2-admin-observability.svelte` `.v2-admin-source dl`):

```css
dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}
dl div {
  padding: 0.65rem 1rem;
  border-bottom: 1px solid var(--v2-separator-quiet);
}
dt {
  color: var(--v2-text-faint);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
dd {
  margin-top: 0.25rem;
  color: var(--v2-text-muted);
  font:
    400 0.68rem/1.45 ui-monospace,
    monospace;
}
```

Status pill / badge (match `v2-admin-observability.svelte` `.v2-admin-status`):

```css
border: 1px solid var(--v2-separator);
border-radius: 999px;
padding: 0.22rem 0.45rem;
color: var(--v2-text-muted);
font:
  500 0.62rem ui-monospace,
  monospace;
text-transform: uppercase;
```

Code/prompt block (match `v2-admin-observability.svelte` `.v2-admin-json pre`):

```css
pre {
  background: var(--v2-recess);
  color: var(--v2-text-muted);
  font:
    0.68rem/1.6 ui-monospace,
    monospace;
}
```

Fonts: headings use `var(--v2-font-display)` ("Share Tech Mono") to match the
observability hero and the public methodology (`v2-methodology-summary.svelte`).
Body/kickers use `ui-monospace` / `var(--v2-font-data)`. State colors are
`var(--v2-amber)` and `var(--v2-red)` — never Tailwind `amber-*`/`rose-*`.

Container width: the observability section sits inside
`.v2-admin-shell { max-width: 96rem; padding: … px-4 sm:px-6 lg:px-8 }`. The
rewritten methodology section must use the same width so the two sections' edges
align. Put the methodology `<section>` inside the same shell, or give it
`max-width: 96rem` with matching horizontal padding and `margin-top: 1.25rem`.

## Commands you will need

All read-only until the user confirms (repo policy — see top of plan).

| Purpose           | Command                        | Expected on success |
| ----------------- | ------------------------------ | ------------------- |
| Svelte type check | `vp run check`                 | exit 0, no errors   |
| Lint              | `vp lint`                      | exit 0              |
| Grep gate (any)   | `grep -rn "<pattern>" <paths>` | no matches          |

(`vp build` is slow and only for deploys — do NOT run it.)

## Scope

**In scope** (only these three files):

- `src/lib/components/v2/v2-admin-methodology.svelte`
- `src/routes/v2/admin/login/+page.svelte`
- `src/styles/v2.css` (remove the `.v2-admin { … }` block only)

**Out of scope**: `src/routes/admin/login/+page.svelte`, `v2-admin-observability.svelte`,
`src/routes/v2/admin/+page.svelte`, `+page.server.ts`, `+layout.server.ts`, anything
under `pipeline/`, `docs/`, or `src/lib/data/`.

## Git workflow

- Branch: `refactor/v2-admin-design-system` (matches repo's `refactor/` convention).
- Commit per step or as one logical unit. Conventional Commits style, e.g.:
  `refactor(v2-admin): use v2 design system for methodology and login`
- Do NOT push or open a PR unless the operator instructs it.

## Steps

### Step 1: Rewrite the methodology component to the V2 design system

File: `src/lib/components/v2/v2-admin-methodology.svelte`.

1. Keep the entire `<script>` block byte-for-byte (the `Methodology` interface,
   `reflowPrompt`, the `stages` derived array, `$props`). Do not change props or data.
2. Rewrite the markup:
   - Outer container becomes a V2 section card matching observatory: a
     `<section>` with a scoped class (e.g. `v2-method`) sized to `max-width: 96rem`
     with `px-4 sm:px-6 lg:px-8` and `margin-top: 1.25rem`, containing an inner card
     with `border: 1px solid var(--v2-separator); border-radius: .65rem; overflow: hidden`.
   - Header: replace `terminal-panel` / `text-xs uppercase tracking-[0.3em]` with the
     V2 kicker style (mono `.68rem`, `letter-spacing:.18em`, `--v2-text-faint`). h2
     uses `var(--v2-font-display)`, `1.35rem`, `font-weight:510`, `--v2-text`.
   - Version chip: replace `terminal-chip` with the V2 status-pill style
     (`999px`, mono `.62rem`, `--v2-separator` border, `--v2-text-muted`).
   - Stage flow `.method-flow__node`: switch to the V2 card idiom —
     `background: var(--v2-surface-1); border-left: 2px solid var(--v2-phosphor);
box-shadow: inset 0 1px var(--v2-separator-quiet), var(--v2-shadow);`
     (no `border-radius`, matching the flat V2 card look). Keep the `→` arrows in
     `var(--v2-phosphor)`. Keep the existing responsive flip below 1024px.
   - "Runtime contract" / "Version ledger" `<dl>` rows: replace each
     `terminal-card flex justify-between …` with the V2 hairline key-value grid
     (exact values in "The target design language" above). Keep the dt/dd content.
   - Prompt `<details>`: replace `terminal-card` with a V2 card (`--v2-recess` bg,
     `1px solid var(--v2-separator-quiet)`). The inner `<pre>` uses the V2 code-block
     style (`--v2-recess`, `--v2-text-muted`, mono `.68rem/1.6`). Keep `reflowPrompt()`
     and the `whitespace-pre-wrap` / `overflow-wrap:anywhere` behavior.
   - Replace every `--terminal-*` reference with the corresponding `--v2-*` token
     (see the mapping already present in the bridge block, Excerpt C).
   - Replace Tailwind text-size/weight utilities with the V2 type scale above.
3. Remove all `terminal-*` class names and all `--terminal-*` CSS references.

**Verify (read-only)**:

```
grep -n "terminal-\|--terminal-\|max-w-7xl\|font-semibold\|tracking-\[" src/lib/components/v2/v2-admin-methodology.svelte
```

→ no matches. (The component still has its `<script>` logic; visually it should now
match the observability section's card/kicker/type language.)

### Step 2: Replace the V2 login route with a self-contained V2-native form

File: `src/routes/v2/admin/login/+page.svelte`.

1. Remove the `import AdminLogin from "../../../admin/login/+page.svelte";` line.
   The V2 route must no longer import or render the V1 login.
2. Reproduce the V1 login's logic in the V2 route's own `<script>` (see Excerpt B):
   `import { enhance } from "$app/forms";`, `import { page } from "$app/state";`,
   `let { data } = $props();` typed `{ configured: boolean; next: string }`,
   `let password = $state("");`. (You can keep the existing `PageData` import/typing
   if it already carries `configured`/`next`; if not, type the prop inline as shown.)
3. Render a V2-native form:
   - Centered V2 card using the V2 card idiom (`--v2-surface-1`,
     `border-left: 2px solid var(--v2-phosphor)`, `--v2-shadow`), max-width ~`28rem`,
     vertically centered (`min-h-[70vh] grid place-items-center`).
   - Kicker `ADMIN` + h1 in `var(--v2-font-display)`, matching the observatory hero
     type. A short subtitle in `--v2-text-muted`.
   - Hidden `<input name="next" value={data.next} />`.
   - Password `<input name="password" type="password" bind:value={password}>` styled
     with V2 tokens: `border: 1px solid var(--v2-separator); background: var(--v2-recess);
color: var(--v2-text);` focus ring `box-shadow: 0 0 0 2px var(--v2-phosphor)`.
   - The "not configured" warning: border/text in `var(--v2-amber)` (NOT
     `amber-*`/`rose-*`). The form-message error line: `var(--v2-red)` (NOT `rose-*`).
   - Submit button: V2 action style — `background: var(--v2-phosphor);
color: var(--v2-canvas);` with a hover darkening (`color-mix`), `disabled`
     at `opacity:.5`. Keep `disabled={!data.configured}` and `use:enhance`.
   - Add a small link `← /v2` and `← /v2/admin` affordance in `--v2-text-faint`.
4. Wrap in `<div class="v2-admin">` (kept as a harmless layout wrapper; its CSS is
   removed in Step 3, which is fine — the card provides its own styling).

**Verify (read-only)**:

```
grep -n "admin/login/+page\|amber-\|rose-\|terminal-" src/routes/v2/admin/login/+page.svelte
```

→ no matches.

### Step 3: Remove the now-unused token bridge from v2.css

File: `src/styles/v2.css`.

1. Delete the entire `.v2-admin { --terminal-bg: …; … min-height: 100vh; }` block
   shown in Excerpt C. Nothing in V2 admin references `--terminal-*` after Steps 1–2.
2. Leave the surrounding CSS (animations, media queries) untouched.

**Verify (read-only)** — confirm no V1 terminal references remain anywhere in V2 admin:

```
grep -rn "terminal-panel\|terminal-card\|terminal-chip\|terminal-input\|terminal-action\|--terminal-" src/routes/v2 src/lib/components/v2/v2-admin-methodology.svelte src/lib/components/v2/v2-admin-observability.svelte
grep -n "v2-admin {" src/styles/v2.css
```

→ both return no matches.

### Step 4: Run the verification gates (ASK THE USER FIRST)

Per `AGENTS.md`, **ask the user for explicit confirmation before running these**.
Once confirmed:

- `vp run check` → exit 0, no type errors.
- `vp lint` → exit 0.

If either fails, fix and re-run. If a failure stems from something not described
in this plan, treat it as a STOP condition.

## Test plan

There is no JavaScript component-test harness in this repo (frontend verification
is `vp run check` + `vp lint`; the Python tests under `pipeline/tests` are
unrelated to this UI change). So verification is:

- Type/lint gates above (machine-checked).
- Manual visual review of `/v2/admin` and `/v2/admin/login`:
  - Both pages share one type voice (mono display headings), one card idiom
    (`--v2-surface-1` + phosphor left border), one section radius (`.65rem`), one
    badge/pill style, and aligned content edges (both `96rem` max-width).
  - No V1 lime/amber/rose hues leak through; accent is `--v2-phosphor`.
  - Check at mobile width (≤640px): sections still collapse sensibly.
  - Check with `prefers-reduced-motion` (no new motion is introduced).

## Done criteria (ALL must hold)

- [ ] `grep -rn "terminal-panel\|terminal-card\|terminal-chip\|terminal-input\|terminal-action\|--terminal-" src/routes/v2 src/lib/components/v2/v2-admin-methodology.svelte src/lib/components/v2/v2-admin-observability.svelte` → no matches
- [ ] `grep -rn "amber-\|rose-" src/routes/v2/admin` → no matches
- [ ] `grep -n "v2-admin {" src/styles/v2.css` → no match (bridge removed)
- [ ] `grep -n "admin/login/+page" src/routes/v2/admin/login/+page.svelte` → no match
- [ ] `git status` shows ONLY the three in-scope files modified
- [ ] (after user confirmation) `vp run check` exits 0
- [ ] (after user confirmation) `vp lint` exits 0
- [ ] `plans/README.md` status row for 002 updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts (drift
  since `3e33cac`).
- `v2-admin-observability.svelte` turns out to also use `terminal-*` classes (it
  should not, per this audit) — do not silently restyle it; report.
- The V1 `src/routes/admin/login/+page.svelte` cannot be safely NOT imported by the
  V2 route (e.g. its server module has side effects the V2 route depends on) — report
  rather than coupling them.
- Removing the `.v2-admin` block breaks a rule elsewhere (grep shows consumers not
  listed here).
- A verification gate fails twice after a reasonable fix attempt.

## Maintenance notes

- After this lands, V2 admin is a pure `--v2-*` surface. Future admin components
  must use V2 tokens only — do not reintroduce `terminal-*` or the token bridge.
  If a shared "admin section card" primitive is wanted later, promote it from
  `v2-admin-observability.svelte` into `v2.css` (un-scoped) and have both
  components consume it; that refactor is intentionally deferred here to keep the
  diff small and risk low.
- The V2 login now duplicates the V1 login's _view_ intentionally (V1 stays
  untouched). If the login UX diverges later, keep the two views independent — do
  not re-import one from the other; the server `load`/`actions` may stay shared via
  `+page.server.ts` re-exports.
- Reviewer focus: confirm no `--terminal-*` / `amber-*` / `rose-*` / `terminal-*`
  classes remain in V2 admin, and that container widths/radii match observability.
