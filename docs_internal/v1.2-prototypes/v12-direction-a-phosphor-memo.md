# v1.2 Direction A — Phosphor Boot

Prototype: `v12-direction-a-phosphor.html` (one self-contained file, no network requests, mock data only)

## Concept + idea sentence

**On this page, the nightly pipeline run becomes a machine booting:** every section is a device that the system probes at power-on. The corpus is the memory test, the articles are a device table (`/dev/hn0`), the history is a trace on a scope (`/dev/scope`), the verdict is the last thing compiled before the prompt comes up, and the footer is the halt screen counting down to the next 04:00 UTC boot.

It's meant to read as a modern product that happens to be a terminal, not a costume. That means one hue and no bezel, no fake chrome or window dots, no green-on-black "hacker" kitsch. The boot itself carries the joke (`/dev/hype optimism cache … FAIL  cleared, continuing`), and it does it once.

**Why green phosphor (not amber):**
1. **Brand continuity.** The repo's one accent is `--palette-lime-dark: oklch(0.68 0.18 140.85)`, which is already a P1-green hue. Every new phosphor token keeps hue 140.85 and changes only lightness and chroma, so the port is a ramp around the existing token, not a re-theme. Amber would become a second brand colour.
2. **The physics fits the chart.** Long-persistence green phosphors (P1/P39, used on scopes and radar) are the ones with visible afterglow, and the history "phosphor trace" depends on that afterglow.
3. **It leaves amber free.** V2 already uses `--v2-amber` as a secondary signal, so keeping v1.2 green avoids colliding with V2's semantics.

Because the display is monochrome, sentiment never relies on hue. It is encoded by **glyph + intensity + outline**:
- positive: `+`, full beam brightness
- neutral: `~`, muted
- negative: `−`, outlined box

In the breakdown bar the three shares are `█` / `▒` / `░`. `--palette-destructive-dark` and `--palette-warning-dark` stay in the token block for mapping but are unused. The single inverse-video `FAIL` is the only "alarm" on the page.

## Layout map (prototype → repo)

| Prototype section | What it is | Repo component |
|---|---|---|
| Boot veil, block 1 (`fetch … ok`, `read [####] 100% 3/3 files`) | Loader: typed fetch log + progress readout | `comprehensive-loader.svelte` |
| Boot veil, blocks 2–4 (memory test, device probes, `compiling verdict`, `VERDICT: NOT YET.`, "show the answer" / "what is this?") | Intro veil: cold boot on first visit, warm boot afterwards (persisted `v12.veilSeen`), replay with R | `verdict-veil.svelte` + `use-veil.svelte` |
| Header: brand, boot stamp, article count, `optimism cache FAIL`, `re-scan R` | Minimal header | `+layout.svelte` header |
| Hero: `> is ai "good" yet?` prompt, `NOT YET.` display, `█▒░` breakdown bar + legend, lede, fine print | Verdict | `verdict-display.svelte` |
| Hero right column: verdict register (score, thresholds, distance, 7-day drift, last flip) + loudest +/− quotes | Verdict detail | `verdict-display.svelte` (new sub-block) |
| POST summary row: articles, window, sources, comments sampled, next-boot countdown | Stats bar | `stats-bar.svelte` |
| `/dev/hn0` recent articles: filter chips, grep, table, hover status line | Articles table | `articles-table.svelte` |
| `/dev/scope` sentiment trace: readout + canvas scope + notable-day buttons. **This is the live thing.** | History chart | `history-chart.svelte` (+ the readout from `verdict-display`'s `hoveredSnapshot`) |
| Inspect sheet: path, prev/next/close, title, meta grid, sentiment gauge, summary, evidence quotes | Article details | `article-details-sheet.svelte` |
| Halt footer: "System halted. Next boot … in hh:mm:ss", method, links, replay | Footer | `minimal-footer.svelte` / `app-footer.svelte` |
| Fixed dock: `FX: ON/OFF`, `SOUND: OFF/ON` | Settings proof | New `state/` store (V2 has a persisted-settings precedent) |
| CRT layer: scanlines, flicker, vignette | Ambient | `scanlines.svelte` + `crt-effect.css` |

**Live thing.** Drag, hover or use the keyboard on the scope to pick any of the 90 days:
- The readout (`> verdict --at <date>`, score, + / ~ / −, sample index, wry note) updates instantly.
- Once the scrub settles (110 ms), the verdict line re-types.
- The beam re-excites the phosphor around the cursor.
- The stinger plays only when the answer changes (YES on 2026-09-23, NO on 2026-10-29).
- Keyboard: `role="slider"` with ←/→ for a day, PgUp/PgDn for a week, Home/End, and an `aria-live` summary.
- Re-scan (R) re-runs the boot and recompiles the verdict.

**Responsive compositions:**
- **1440 (desktop):** hero has two columns (verdict + register), the POST row has 5 cells, the scope has 2 columns (readout + screen).
- **≤1080 (768 tablet):** single-column hero; the register becomes a two-column band; the POST grid is 3+2; the readout sits above the screen in two columns; the domain column is dropped.
- **≤640 (390 phone):** the table becomes a two-line log (status glyph + title, then meta line); the legend becomes a dotted leader list; POST is 2 columns; the sheet becomes an 88 dvh bottom sheet; the dock becomes a bottom bar; probe rows drop the dot leaders and wrap notes.

## Motion language

- **Easing:** `--ease-swift: cubic-bezier(0, 0.7, 0.1, 1)` everywhere. Exceptions:
  - the scope beam sweeps linearly (a physical beam has constant speed)
  - the caret uses `steps(1)`
- **Durations:**
  - entrance 420 ms
  - stagger 70 ms (`--stagger`)
  - sheet 360 ms
  - veil lift 460 ms
  - toast 200 ms
  - control feedback 90–120 ms
- **Only transform and opacity animate.** Typed text and counters change `textContent`, which is not motion travel.

**Choreography:**
1. **Cold boot (~6 s).**
   - Fetch lines print with ticks, then the read progress bar fills.
   - The memory test counts 0→1,365 articles and 0→48,210 comments.
   - Six probes: each prints `..` and then resolves `ok`, or `FAIL` in inverse video after a longer pause.
   - POST beep.
   - `compiling verdict` progress runs with an ASCII spinner `|/-\`.
   - Weighting lines print, then `VERDICT: NOT YET.` types at 55 ms/char, then the stinger.
   - The prompt and the "show the answer" button appear and the button takes focus.
2. **Warm boot (~1.5 s).** Three summary lines, then the verdict types, then the veil auto-lifts.
3. **Lift.** The CRT power-off collapse: `scale(1, .004)` at 55%, then `scale(0, .004)` with opacity 0. Hero typing starts at 200 ms, underneath the collapse.
4. **Hero.**
   - The prompt types at 26 ms/char; "good" types slowly at 110 ms/char, a nod to V1.
   - `NOT YET.` types at 80 ms/char, then the stinger.
   - Legend, lede, register and voices fade up on the 70 ms stagger.
   - The `█▒░` bar prints left to right over 640 ms (ease-out cubic).
5. **Scroll** (IntersectionObserver).
   - The device-header rule draws out with `scaleX` (700 ms).
   - Tools and rows enter on a 70 ms stagger; POST cells stagger.
   - The scope beam sweeps 90 samples in 1.5 s. Afterglow decays each point toward a 0.5 "persisted" level with τ = 650 ms. The glow is a 5 px pass at ≤13% alpha under a 1.6 px core, with no `shadowBlur` and no bloom.
6. **Sheet.** Slides in (`translateX`, or `translateY` on phone). The gauge scales from the centre line. Evidence quotes type at 9 ms/char with a 90 ms gap between quotes.
7. **Ambient.**
   - Static scanlines.
   - Phosphor flicker: an 8 s `steps()` opacity blip at 1.8% tint (`--crt-flicker-speed`).
   - Vignette: inset `box-shadow`, not a gradient.
   - Blinking carets (hero, scope, footer halt line).

**Distinct moving elements (≥8):** boot log lines, read progress bar, memory counters, probe status flips, compile spinner + bar, veil collapse, hero typewriter + caret, breakdown bar print, staggered legend/register, device-rule draw, row stagger, scope beam + afterglow, scrub cursor + re-excite, verdict re-type, sheet slide, gauge fill, quote typing, toast, flicker, countdown.

## Sound palette (WebAudio synthesis only)

- The AudioContext is created **only** when the user switches `SOUND: ON` (a click gesture). The default is OFF on every load and is not persisted.
- Signal chain: master gain 0.9 → DynamicsCompressor (threshold −18 dB) → destination.
- Envelopes are linear attack followed by an exponential decay to 0.0001.
- Every cue is wrapped in try/catch and is silent when Sound is off **or** FX is off.

| Cue | Trigger | Waveform | Frequency | Envelope | Peak gain |
|---|---|---|---|---|---|
| `tick` | each boot/loader line, each typed verdict char | square | 2100–2380 Hz (steps by line index) | 1 ms attack, 14 ms decay | 0.022 |
| `probe` | device probe answers `ok` | square → lowpass 3.5 kHz | 1320 Hz | 2 ms / 40 ms | 0.018 |
| `fail` | `/dev/hype … FAIL` | square → lowpass 1.2 kHz | 220 Hz | 2 ms, 50 ms hold, 110 ms total | 0.03 |
| `post` | all probes done (single POST beep) | square → lowpass 3 kHz | 1000 Hz | 4 ms, 120 ms hold, 170 ms total | 0.032 |
| `reveal` | veil-lift gesture (click / Enter / Esc / Space) | sine sweep + lowpassed noise | 140→42 Hz exp sweep; noise lowpass 900 Hz | 5 ms / 380 ms; noise 220 ms | 0.09 + 0.035 |
| `stinger` | verdict printed (boot, hero, scope answer change) | 2 × square → lowpass 1.8 kHz | NOT YET D5→A4 (587→440); YES A4→E5 (440→659); NO E4→B3 (330→247) | 140 ms + 200 ms, second at +180 ms | 0.045 (×0.7 on scope) |
| `hover` | row hover/focus, sheet prev/next, control hover | triangle | 520 + 2.2·sentiment Hz (−100 → 300 Hz, +100 → 740 Hz): pitch carries the data | 2 ms / 28 ms, throttled 45 ms | 0.02 |
| `scrub` | scope crosses a day | sine | 1600 Hz | 9 ms, throttled 32 ms | 0.014 |
| `toggle` | FX/SOUND, chips, notable-day buttons | white noise → highpass 2 kHz | n/a | 8 ms | 0.05 |
| `open` / `close` | details sheet | noise click + sine glide | open 220→330 Hz; close 330→196 Hz | 70 ms | 0.03 / 0.025 |

## Toggle mapping (`FX: ON/OFF`, persisted `v12.fx`, applied before first paint)

| Bucket | Dies with FX off | Stays |
|---|---|---|
| **Intro** | Boot veil never mounts (`.fx-off .veil{display:none}`); a running boot is cancelled and lifted instantly; R / re-scan only shows a toast explaining why | All verdict content is already in the hero |
| **Sound** | All cues muted; SOUND control becomes `aria-disabled` with an explanatory label | Nothing |
| **Ambient** | Scanlines, flicker, vignette, caret blink, verdict text-shadow glow | n/a |
| **Motion** | Typewriters complete instantly; `.rv` entrances, rule draw, sheet slide, gauge, toast and button transitions are removed; scope beam/afterglow is replaced by a static full-brightness trace with no glow pass | Every control works: scrub (cursor + readout still update), filters, grep, sheet, keyboard shortcuts, countdown |

**`prefers-reduced-motion`:**
- The ambient layer is hidden.
- Travel (translate/scale) drops, and entrances become a 200 ms opacity fade.
- The veil lift becomes a fade.
- The boot still runs, but each step is capped at 40 ms and counters and bars are instant.
- The scope is drawn statically.
- Sound stays opt-in.

## Porting notes

- **Tokens.** Copy the NEW block into `tokens.css` under `.dark`. Keep `--phosphor-*` derived from the lime hue, and swap `--font-mono` to the system stack to drop the webfont.
- **Repo token inconsistency to fix while porting.** `--palette-lime-dark` is hue **140.85**, but `--terminal-border` / `-glow` / `-hover` use hue **130.85**. The prototype keeps the repo values verbatim; the hue drift is visible next to the new phosphor ramp.
- **Ground and panel contrast.** `--terminal-bg` (gray-900) on gray-950 is only 1.03:1, so panels are nearly invisible. The prototype uses gray-800 (`--terminal-bg-header`) for raised surfaces.
- **Veil + loader in one sequencer.** Make it a single `boot-sequence.svelte` driven by an async generator with a generation token (as in the prototype) so skip, replay and FX-off cancel cleanly.
  - The fetch block should reflect real load progress. The mock timings are placeholders.
  - Keep `useVeil` for persistence, and add `warm`/`cold` modes.
- **Typewriter.** Port it as a composable (it replaces `use-token-stream` for these lines). It must check `motionOK()` on every step so FX-off completes text immediately. Keep the screen-reader text separate (`sr-only` full text, `aria-hidden` typed text).
- **Breakdown bar.** Text glyphs sized by a measured char width, recomputed on resize. The risk is fallback fonts with mismatched block-glyph widths; the bar clips with `overflow:hidden`. A CSS `scaleX` segment bar is the safe fallback.
- **Scope = canvas, not LayerCake.** LayerCake/SVG can't do per-segment afterglow cheaply.
  - The rAF loop stops itself once energy settles, so there is no idle CPU.
  - Canvas colours are hard-coded sRGB equivalents of the OKLCH tokens, because canvas OKLCH support is uneven. Regenerate them if tokens change.
  - Keep the `role="slider"` wrapper and the HTML readout outside the canvas.
- **Svelte transitions vs CSS.** Use CSS classes for `.rv` staggers (the `--i` custom property), because Svelte `transition:` doesn't respect the FX store without wrapping. The sheet can use shadcn Sheet, but override the backdrop to a solid scrim (no blur) and the easing to `--ease-swift`.
- **Audio.** A singleton module with a lazy context; never create it in `onMount`. Gate every cue on a `sound && fx` store.
- **Risks:**
  - The cold boot is about 6 s. It is skippable and first-visit only, but watch bounce analytics, and consider cold-boot-once / warm-thereafter as the default (as in the prototype).
  - The flicker must stay at 1–2% or it reads as a bug.
  - The `FAIL` gag and the "optimism cache" header status are the only jokes in the chrome; resist adding more.
  - The mobile table→log conversion uses `display:grid` on `<tr>`. Verify screen-reader table semantics, or render a `<ul>` at that breakpoint instead.
- **Not verified:** under the cost-control instruction the prototype was **not** opened in a browser. Only a static syntax parse of the script was run.
