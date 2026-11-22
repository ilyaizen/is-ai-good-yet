# v1.2 Direction B — TELEMETRY DECK

Prototype: `v12-direction-b-telemetry.html` (single file, zero external requests, mock data only).

## 1. Concept

**Idea sentence:** On this page, Hacker News sentiment becomes *telemetry*. The verdict, the daily scrollback, points and comments, and the evidence quotes are all readings on one calibrated instrument deck, and the instruments stay deadpan whatever the commenters are doing.

How each section carries the idea:
- **Intro** is a power-on self test (bus, feed link, cache, comment sampler, "HYPE FILTER … ENGAGED"). The veil arms the deck.
- **Hero** is the main readout: a 240° gauge with a sprung needle, a mechanical verdict drum (YES. / NOT YET. / NO.), and three 50-segment LED bar meters for POS/NEU/NEG.
- **Stats** are odometer counters that roll in with stepped digits.
- **Trace** is an oscilloscope on a fine grid, with event flags, threshold rails at 45/55 and a cursor. **The live thing:** scrubbing it re-reads the verdict for that date, and the hero gauge, drum, meters and meta re-settle to it.
- **Feed** is a set of signal channels (CH01–CH12). Each row has a center-zero VU meter with peak hold, plus PTS/CMT odometers.
- **Details sheet** is "CHANNEL INSPECT". Evidence quotes appear as "CAPTURE 01…" transmissions, and a linear meter shows the article's sentiment.
- **Footer** is the instrument plate: serial number, a calibration disclaimer ("Not calibrated against reality, which declined to participate"), and a live **NEXT SYNC** countdown for the daily ritual.
- **Ambient:** a blinking status lamp, a faint scope sweep, needle tremor, and a geiger flux lamp whose rate tracks how negative the current view is.

Verdict thresholds mirror `pipeline/src/export.py` (≥55 YES, <45 NO). The mock live reading is 47.6 → **NOT YET** (POS 37 / NEU 22 / NEG 41).

## 2. Layout map (prototype → repo)

| Prototype section | Repo component | Notes |
|---|---|---|
| `#intro .post` (POST self-test, 24-seg stepped bar) | `landing/comprehensive-loader.svelte` | In prod, show it while `veil.isLoading`. The prototype plays it as stage 1 of the intro. |
| `#intro .veil` (question, trace line, ARM / ARM + SOUND) | `landing/verdict-veil.svelte` + `composables/use-veil.svelte` | Keep the persisted first-visit logic from `useVeil`. The prototype auto-plays on every load so reviewers can see it. R / the Replay button = `handleReplayScrollToTop`. |
| `.hdr` (wordmark, section nav, LINK lamp, last sync) | `+layout.svelte` header | The lamp turns amber and reads PLAYBACK while scrubbing. |
| `#verdict` (gauge, drum, deadpan, meta, breakdown) | `landing/verdict-display.svelte` | Data: `verdictScore` (score, counts, rawSentiment, windowMonths). |
| `.stats` (6 odometers) | `landing/stats-bar.svelte` (+ `article-counts.svelte`) | Data: `verdict.json` permanent / current / pipeline totals. |
| `#trace` (scope canvas, timebase, events, readout) | `landing/history-chart.svelte` | In V1 the chart is a child of verdict-display. Here it moves directly under the stats so scrubbing stays next to the gauge it drives. Source data: `weekly.json` (weekly) or a new daily rolling series. |
| `#feed` (band filter, grep, sort, rows with VU + odometers) | `landing/articles-table.svelte` | `band()` uses the V1 neutral band \|s\| ≤ 0.2. Contribution = s × influence, shown in the sheet. |
| `#sheet` (CHANNEL INSPECT, kv grid, meter, captures, J/K) | `landing/article-details-sheet.svelte` | Data: `quotes`, `summary`, `topic`, `trajectory`, `influenceScore`. |
| `.foot` (instrument plate, countdown) | `landing/minimal-footer.svelte` / `app-footer.svelte` | |
| `.ctl` (flux readout, FX, SOUND, Replay) | NEW `fx-controls.svelte` + a persisted-settings store | |
| `.scanlines` | `crt-scanlines.svelte` / `crt-effect.css` | Uses `--crt-scanline-opacity: 0.04`. Static. |

The tokens are the `:root` block at the top of the CSS, mapping 1:1 to `tokens.css` (dark values) plus `--ease-swift` and `--crt-scanline-opacity`. Every new token is marked `NEW` (`--deck-*`, `--dur-*`, `--stagger`, `--font-instrument`, `--ease-mech` alias). One repo inconsistency is preserved rather than fixed: `--terminal-border*` and `--terminal-accent-glow` use lime hue 130.85, while `--palette-lime-dark` uses 140.85.

## 3. Motion language

The motion should feel precise and mechanical, never organic. Motion uses transform and opacity only (needle rotation, translate, scaleX). Canvas redraws count as paint, not layout.

| Element | Mechanism | Timing |
|---|---|---|
| Gauge needle | Damped spring: k=90, ζ≈0.6. One small overshoot, then a stop pin at −1.5. Semi-implicit Euler in rAF, dt clamped to 33 ms. | ~900 ms to settle; the stinger fires on settle |
| Needle tremor (ambient) | CSS keyframes ±0.22° on a wrapper `g` | 3.1 s loop |
| Verdict drum | `translateY` on a 3-word strip, `steps(4,end)` (detent feel) | 380 ms |
| Breakdown LED meters | Segments light one at a time (`setInterval` 14 ms/segment), up or down to the target | ≤700 ms |
| Odometers (stats, PTS/CMT) | Per-digit strip, `steps(distance)` easing, staggered right-to-left by 45 ms; columns stagger 80 ms | 140 + 60·distance ms |
| Scope trace | Left-to-right canvas draw with a bright write-head, eased by `cubic-bezier(0,0.7,0.1,1)` (JS Newton solver) | 1100 ms (700 ms on timebase change) |
| Scope sweep (ambient) | Full-width element whose right border translates −100% → 0 | 7 s linear |
| Status lamp (ambient) | `steps(1)` blink, 89% on | 2.4 s |
| Section legend rule | `::after` scaleX 0→1 when the section enters | 700 ms, 120 ms delay |
| Section content | `.rv` opacity + translateY(10px), `--i × 70ms` stagger | 360/520 ms |
| Feed rows | opacity + translateX(−8px), 70 ms stagger; VU segments then light outward from center at 28 ms per segment | 300/420 ms |
| Sheet | translateX(100%) → 0 (bottom sheet on mobile: translateY). Captures stagger 70 ms after 160 ms. The meter pointer starts at center and springs to the reading. | 420 ms |
| Intro POST | Lines tick in every 190 ms; the 24-segment bar fills in steps | ~1.8 s |
| Intro veil | Words rise with a 90 ms stagger; a mask uncovers the trace line (translateX); copy fades in; ARM splits two shutters (translateY ±101%) | 1.1 s draw, 620 ms open |
| Geiger lamp | 40 ms flash per Poisson-scheduled tick | rate-mapped |
| Footer countdown | 1 s digit updates | — |

Easing everywhere is `--ease-swift` / `--ease-mech` = `cubic-bezier(0, 0.7, 0.1, 1)`. The only exception is `steps()`, used for detented mechanics.

**Reduced motion** (`@media (prefers-reduced-motion: reduce)` plus a JS `matchMedia` listener): all content stays; travel is dropped. Entrances become 200 ms opacity fades. The needle, drum, odometers, trace and LED meters snap to their values. The sweep, lamp, tremor and peak blink stop. Intro shutters fade instead of sliding, and the trace mask is removed.

## 4. Sound palette (WebAudio synthesis only)

The AudioContext is created lazily inside a user gesture: the SOUND button or "ARM + SOUND". Master gain is 0.7. Sound defaults to OFF and is never persisted ON. Every cue goes through `canSound()`, which requires SOUND on, FX on, a running context and a visible document.

| Cue | Trigger | Waveform | Frequency | Envelope (attack / decay, exp) | Peak gain |
|---|---|---|---|---|---|
| Loader tick | Each POST line | square | 1900 Hz | 1 ms / 18 ms | 0.022 |
| Veil reveal (arm) | ARM click, Enter, Esc, click-to-skip | lowpass noise at 520 Hz, plus a sine sweep, plus a square latch tick 180 ms later | noise; sine 220 → 70 Hz; tick 1760 Hz | noise 1/120 ms; sine 4/320 ms; tick 1/20 ms | 0.12 / 0.11 / 0.02 |
| Hover blip | Hover or focus on rows, buttons, events (rate-limited to 45 ms) | sine | 1320 → 1480 Hz | 2 ms / 40 ms | 0.016 |
| Instrument click | Every control activation | highpass noise at 2400 Hz, plus a triangle | noise; 2600 Hz | 1/14 ms; 1/8 ms | 0.06 / 0.02 |
| Scrub detent | Each change in the scope cursor index (rate-limited to 28 ms) | triangle | 880 Hz | 1 ms / 10 ms | 0.014 |
| Verdict stinger | Gauge settles on first reveal, or when the verdict changes during playback | sine pair, each doubled by a triangle an octave down; the second note follows 160 ms later | NOT YET: D5 → A4 (587 → 440). YES: A4 → E5 (440 → 659). NO: A4 → E♭4 (tritone, 440 → 311). | 6 ms / 380 ms, then 6 ms / 500 ms | 0.07 (sine) / 0.025 (triangle) |
| Sonar ping | First entrance of the stats, trace, feed and footer sections (once per intro cycle) | sine into an echo bus: delay 230 ms, feedback 0.28, 2.4 kHz lowpass in the loop, wet 0.5 | 1174.66 → 1108 Hz | 3 ms / 900 ms | 0.045 |
| Geiger tick | Poisson process, λ = 0.25 + 10·n^1.6 per second, where n = negativity of the current view | bandpass noise (Q 3) at 3600 Hz | — | 1 ms / 4 ms | 0.022–0.034 (randomized) |

Geiger "current view": hero → NEG% of the reading (live or playback). Stats → live NEG%. Trace → NEG% at the cursor or hover day. Feed → mean max(0, −s) over rows ≥50% visible. Open sheet → max(0, −s) of that article. Footer → 0.03. The live reading (NEG 41%) gives about 2.6 ticks/s, and a −0.71 article about 5.9/s. The fixed control shows the rate ("NEG FLUX 2.6/s · VIEW") and flashes a lamp on each tick, so the mapping can be read without audio.

## 5. Toggle mapping (FX: ON/OFF, persisted as `iagy.v12.fx`)

| Bucket | Dies with FX OFF | Stays |
|---|---|---|
| Intro | POST loader animation, veil, shutters. FX off mid-intro finishes it at once. Replay (button and R) is disabled and shows a toast. | Page renders directly in its final state. |
| Sound | Every cue: `canSound()` returns false, SOUND is forced OFF and its button disabled, and the AudioContext is suspended. The geiger scheduler stops firing. | — |
| Ambient | Lamp blink (steady on), scope sweep (hidden), needle tremor, peak-hold blink, geiger lamp, trace glow pass. | Static scanlines at 0.04 (brand texture, not motion). |
| Non-essential motion | Spring needle snaps; drum, odometers, LED meters, VU segments, sheet slide and backdrop fade are all instant; section/row/capture entrances are skipped; the trace draws fully at once. | All data and every interaction: scrubbing re-reads the verdict, filters, grep, sort, sheet, J/K, keyboard slider. Hover and focus color states remain (no travel). |

Turning FX back ON restores the ambient effects and enables sound and replay. It does not auto-replay the intro.

## 6. Porting notes (Svelte 5)

- **Canvas vs SVG vs CSS:**
  - Keep the scope on `<canvas>`: 90+ points plus a fine grid redrawn on every pointer move is cheaper than SVG DOM churn. Use one `$effect` keyed on `[timebase, cursor, hover, progress]`. Resolve colors from tokens once, with sRGB fallbacks for canvas engines without oklch (already in the prototype).
  - Keep the gauge as SVG, generated once, with the needle `transform` set from a small spring module (`use-spring-needle.svelte.ts`). Don't use Svelte's `spring` store: its stiffness/damping semantics differ, and we need the stop pin and an `onSettle` callback for the stinger.
  - Odometers become `<odometer value={n} delay from0 />`. Recommend this over `@number-flow/svelte`, which V1 uses, because number-flow eases organically and the brand here needs `steps()`. Keep the visually hidden real value for screen readers.
  - Section, row and capture entrances use CSS classes toggled by one IntersectionObserver action (`use:enter`), not Svelte `transition:`, so FX off and reduced motion stay pure CSS overrides.
  - The sheet can sit on the existing shadcn Sheet, restyled. Keep `inert` on the closed state, return focus on close, and the Tab trap.
- **State:** `fx`, `sound` (session only) and `playback` (day index or null) go in a runes store next to `src/lib/state/` (V2 already persists visual settings there). V1 data must not be mutated. Playback only selects which reading feeds the hero.
- **Data gaps:** V1 exports a weekly series (`weekly.json`) and a monthly one (`historical.json`). A daily 30-day rolling series doesn't exist yet. Either scrub weekly snapshots (13 points per quarter) or add a daily export in a pipeline PR, with `cli.ts` exposure per AGENTS.md. Per-quote sentiment and quote source attribution (article vs comment, author, points) are not in `articles.json` today. Either drop them from the sheet or add them to the export contract. The event flags (E1–E3) are editorial and have no data source; they could be derived from days with the largest |Δ| together with the top article.
- **Risks:**
  1. The sound layer needs careful gesture handling on iOS Safari (it requires `resume()` within the gesture). The prototype does this on SOUND and ARM + SOUND.
  2. Geiger audio can annoy. It is subtle (≤0.034) and sits behind two opt-ins, but consider a separate "geiger" sub-toggle if reviewers complain.
  3. Pointer scrubbing on mobile uses `touch-action: pan-y`, so vertical scroll still works; horizontal drags scrub.
  4. The hero is visually dense. Keep the gauge and drum dominant, and don't add more meta cells.
  5. With 1,365 rows in prod, render odometers only for visible rows; the `odo` strip DOM is 10 spans per digit.
  6. The `--terminal-*` hue mismatch noted above.
- **Accessibility:**
  - Scope = `role="slider"` with `aria-valuetext` ("2026-10-08: score 61.2, YES"), arrows ±1 day, PageUp/PageDown ±7, Home/End.
  - Feed rows are buttons with full aria-labels; Enter opens the sheet; J/K steps through articles; Esc closes.
  - The drum has a live sr-only verdict; the readout panel is `aria-live="polite"`.
  - All controls have accessible names and `aria-pressed`.
