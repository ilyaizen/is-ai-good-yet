# v1.2 Direction C — "Quiet Terminal"

Prototype: `v12-direction-c-quiet.html` (one self-contained file, no external requests, mock data only).

## Concept

**Idea sentence:** On this page, Hacker News sentiment becomes a typeset ledger. The verdict is the bottom line, set at headline size, and every section below is an itemized entry that adds up to it, down to the footer's checksum.

This direction is for developers who dislike theatrics, but it is still a clear redesign, not V1 with the effects removed. The page relies on scale contrast: one huge word ("NOT YET.") sits above small, dense, carefully set data. Typography does the work of the chart.

**Signature rule: the accent is rationed.** The lime `--palette-lime-dark` appears only where Hacker News liked something:
- the `+ for` sign, column rule, strip glyphs and history line
- positive net scores
- the verdict word, but only when the verdict is YES

Everything else is monochrome because AI is not good yet. If you scrub the history back to 22 Sep (the two YES days), the giant verdict turns lime. Red (`--palette-destructive-dark`) and warning yellow are deliberately unused. "Against" is set in ink, not alarm red. The site is deadpan, not alarmed.

**Sentiment is set in type.** It appears three ways:
- **Hero proportional columns.** Each column's width is its share (`grid-template-columns: f fr s fr a fr`). A fixed `50.0 · the line` tick marks the verdict boundary for both `for` and `against`.
- **20-glyph sign strips in the table** (`++++++······−−−−−−−−`). Each glyph is 5%, rounded with largest-remainder.
- **A 40-glyph strip plus mini proportional columns** in the details sheet.

All displayed shares use largest-remainder rounding to tenths, so they always sum to exactly 100.0. The footer prints that sum as a checksum.

**Live thing: scrubbing the scrollback recomputes the verdict.**
- Drag or hover the 90-day chart, or focus it and use the arrow keys (Shift = 1 week, Home/End, PgUp/PgDn = 30 days).
- The readout, the hero verdict word, the hero columns (widths and percentages), the gloss sentence, the distance-to-YES figure and the footer checksum all recompute for that day.
- A click or any key press pins the day. Esc or "back to today" returns to today.

The mock series contains a 2-day YES (09-22, "a model shipped") and a NO stretch (10-22, "the postmortem").

## Layout map (prototype → repo)

| Prototype section | Repo component(s) | Notes |
|---|---|---|
| `#veil` (question + GET log + progress rule, curtain lift) | `verdict-veil.svelte` + `comprehensive-loader.svelte` | **Fused.** The loader becomes the veil's progress rule and request log. One overlay, ≤1.12s. Production keeps `useVeil` persistence (first visit only); the prototype plays on every load so reviewers can see it. |
| `header.top` (sticky, brand / nav / run #, updated) | `+layout.svelte` header | Hairline only. Nav collapses at ≤1024. |
| `.hero`: question h1, rule-defs (YES/NO/NOT YET thresholds), giant verdict, proportional breakdown, gloss, distance-to-YES | `verdict-display.svelte` | The V1 token-streamed description becomes one static deadpan sentence. Number roll is dropped. |
| `.ledger` (6 cells: articles, comments sampled, points weighed, sources, verdict changes, days at yes) | `stats-bar.svelte` | Every value is derived from the history series. Laid out 6 → 3 → 2 columns. |
| `#scrollback`: readout (4 col) + SVG chart (8 col) with 50% line, event annotations, articles/day band | `history-chart.svelte` | **Promoted** to the second screen. V1 nests it, collapsed, inside verdict-display, and hovering it already changes the counts. This keeps that behaviour and makes it the page's one interaction. |
| `#entries`: filter (all/for/shrug/against + counts), grep input, sortable table, empty state | `articles-table.svelte` | Columns: rank · entry (title + domain + thesis) · pts · cmts · 20-glyph strip · net · date. j/k to move, Enter to open. |
| `.sheet`: entry n/N, prev/next, title (≤2 lines), meta, thesis, strip + mini columns, net/utility/trajectory, ranked evidence quotes, mock links | `article-details-sheet.svelte` | Has a real 200ms loading skeleton ("reading 120 comments…"), a focus trap, and returns focus to the row on close. Use `[` / `]` for prev/next. |
| `footer#method`: checksum, method, source, next run, keys, fine print, "balance carried forward 100.0" | `minimal-footer.svelte` / `app-footer.svelte` | The ledger's closing line. The checksum follows the scrub. |
| `.controls` (replay R, sound, fx) + `.status` live line | new: `fx-controls.svelte` | Fixed bottom-left, or a full-width bottom bar at ≤640. |
| `.scanlines` | `crt-scanlines.svelte` | Static repeating lines at 0.02 white alpha. No roll, no flicker, no vignette. |

Responsive compositions:
- **1440:** 12-column grid.
- **768:** the readout sits above the chart as a two-column header block; rank and date columns are hidden.
- **390:** a different composition, not a squeezed desktop.
  - The verdict stacks as `NOT / YET.` at 27.5vw.
  - Hero columns become rows, each with its own share track and 50% tick.
  - Table rows become two-column list rows, with the strip and net on one line and pts/comments on the next.
  - The sheet goes full-screen and the controls become a bottom bar.

## Motion language

- **Easing:** `--ease-swift: cubic-bezier(0, 0.7, 0.1, 1)` everywhere except the 140ms veil question fade (linear).
- **Allowed vocabulary:** opacity, 1px `translateY`, `scaleX` line-draws (origin left), and SVG `stroke-dashoffset` line-draw on the two history lines (with `pathLength="1"`).
- **Nothing** spins, glows, bounces, blinks or types character by character.
- The verdict word is the one character stagger: opacity plus 1px at 60ms per character. At 230px it reads as typesetting, not typing.
- **Durations:** `--q-dur-1` 160ms (hover/colour), `--q-dur-2` 420ms (entrances, sheet), `--q-dur-3` 560ms (line-draws). Staggers run 60–80ms.

Load choreography, from t=0:

| t | What happens |
|---|---|
| 0 | Veil question fades in (140ms) |
| 80 | Progress rule draws over 500ms |
| 120 / 190 / 260 | GET log lines appear |
| 600 | "ready." appears + **tick** |
| 640 | Curtain lifts (translateY −100%, 460ms) + **stinger** |
| 640 | Hero entrances begin: question h1 → verdict characters (60ms + i·60) → rule-defs 120 → breakdown columns 300/380/460 (rule line-draw + numbers) → 50% tick 520 → gloss 560 → distance 640 |
| ~1110 | Veil removed. The IntersectionObserver starts for the rest of the page. |

On scroll, each section entrance fires once:
- ledger cells (70ms stagger)
- section-head rule draws
- scrollback readout, then the chart, whose two lines draw in over 1100ms (against delayed 100ms)
- table rows (60ms stagger)
- footer rule draw → footer list → checksum figure

On interaction:
- **Table row hover:** background tone, underline colour, and a `→` marker (opacity plus 1px translateX).
- **Nav and controls:** underline line-draw.
- **Control press:** opacity flash. A status line fades in.
- **Sheet:** slides in (translateX 100% → 0, 420ms), then content staggers at 70ms.
- **Scrub:** the cursor follows directly (transform, no easing). The verdict word restaggers when it changes.

**Distinct moving elements (14):** veil rule, veil log, curtain, verdict characters, breakdown rules, breakdown numbers, 50% tick, ledger cells, section rules, chart line draw, scrub cursor, table rows, sheet plus its content, footer rule, control underlines/flash, status line.

**Reduced motion** (`prefers-reduced-motion: reduce`):
- All translate and scale travel is removed. Line-draws appear fully drawn and chart lines are fully stroked.
- The curtain becomes a 200ms opacity fade, so the intro is about 640ms total.
- The sheet fades instead of sliding, and smooth scroll is off.
- Opacity fades remain, so content still arrives but nothing travels.

## Sound palette

**Two cues. That is the entire sound design, on purpose.** Both are WebAudio synthesis with zero audio files.

- Sound is off by default, and that is never persisted.
- The `AudioContext` is created lazily, only inside a user gesture (the SOUND toggle click). Turning sound on plays the tick once as confirmation.
- A reload always starts silent, so no autoplay-policy warnings.

| Cue | Trigger | Waveform | Frequency | Envelope | Peak gain |
|---|---|---|---|---|---|
| **Tick** | Loader done ("ready.", t≈600ms); also when sound is switched on | triangle | 1760 → 1320 Hz, exponential glide over 30ms | 2ms exponential attack, exponential decay to silence by 45ms, stop at 60ms | 0.035 |
| **Stinger** | Veil lift (t≈640ms). It serves as both the veil-reveal cue and the verdict stinger, because the lift reveals the verdict. | 2 × sine through a lowpass (1800 Hz, Q 0.5) | Falling minor third G4 392 Hz → E4 329.6 Hz for NOT YET / NO. Rising E4 → G4 when the verdict is YES. | Note 1: 10ms attack, 220ms exponential decay. Note 2 starts at +140ms: 10ms attack, 600ms exponential decay. | 0.05 per note |

**Deliberately omitted:**
- **Hover blip.** Hover sounds over a 12-row table would be exactly the theatrics this direction exists to remove.
- **A separate verdict stinger.** The veil lift is the verdict moment, so one cue covers both.

FX off suspends the context and disables the SOUND button.

## Toggle mapping (FX: ON/OFF)

FX is persisted in `localStorage` (`v12q-fx`, guarded). FX off sets `html.fx-off`.

| Bucket | Dies with FX off | Stays |
|---|---|---|
| Intro | Veil/curtain, request log, progress rule. In-flight timers are cancelled instantly. R shows "FX is off, so there is no intro to replay." | Page is fully revealed immediately |
| Sound | Both cues. The context is suspended and the SOUND control is disabled ("Sound is part of FX"). | — |
| Ambient | Scanlines (faded out) | — |
| Motion | Every entrance, stagger, line-draw, chart stroke draw, verdict character stagger, sheet slide and control flash. Implemented as `.fx-off * { transition-duration: 0s; transition-delay: 0s; animation: none }`, and `[data-enter]` hidden states only apply under `.fx-on`. | Hover and focus feedback as instant colour and underline changes; the scrub (direct manipulation); sorting, filtering, grep, empty state; sheet open and close (instant), with its 200ms loading skeleton because that is a real state; keyboard shortcuts; focus trap |

## Porting notes (Svelte 5)

- **Tokens.** Everything outside the `--q-*` names already exists in `tokens.css`, `app.css` (`--ease-swift`) or `crt-effect.css`. Add `--q-*` to `tokens.css` as a scoped layer, e.g. `body.v12`, mirroring how V2 is scoped.
  - Production should keep the self-hosted `--font-mono` (IBM Plex Mono). The prototype stack (`ui-monospace, Cascadia Code, …`) exists only because webfonts are disallowed here.
  - Re-check the verdict's `letter-spacing: -0.065em` against Plex Mono, whose glyphs are wider.
  - `--radius` is 0 in this direction.
- **Veil + loader.**
  - Merge `verdict-veil.svelte` and `comprehensive-loader.svelte` into one component driven by `useVeil`.
  - Bind the progress rule's `scaleX` to real fetch progress, or to an indeterminate CSS draw.
  - Keep first-visit persistence and the replay hook (`handleReplayScrollToTop`).
- **Entrances.** Use CSS classes plus an `IntersectionObserver` action (`use:enter={{ delay }}`), not Svelte `transition:`. The elements are always in the DOM, and the FX kill switch needs to be a single root class. Svelte `transition:` fits only the sheet, if it is conditionally mounted.
- **Chart.** Use SVG, not canvas: about 90 points × 2 lines plus 90 rects is trivial, and SVG keeps text crisp and stylable by tokens.
  - Rebuild it with LayerCake (already in the stack) or a plain `$derived` path string.
  - The cursor should be a `<g transform>` updated from `$state idx`.
  - Keep `role="slider"` and its aria-valuetext on the wrapper.
- **Scrub state.** Hold one `$state` (`selectedIndex`, `pinned`). Hero, readout and footer each `$derived` from `snapshots[selectedIndex]`. The V1 equivalent is `hoveredSnapshot`.
  - Data granularity: the prototype treats each day as a trailing-7-day share. V1 has `weeklySnapshots`, so either export daily trailing values or scrub weekly (13 points); the layout works with either.
- **Hero columns.** `grid-template-columns` changes instantly on scrub; it is layout, not animated. Don't animate grid tracks, which is a layout-thrash risk. The mobile track fills use `transform: scaleX(var(--s))`.
- **Glyph strips.** Generate them with a pure `signStrip(f, s, a, n)` util with largest-remainder rounding. Mark them `aria-hidden` with an sr-only sentence. **Risk:** U+2212 and U+00B7 need to be exactly one cell wide in the production mono face. Plex Mono is fine; verify any fallback.
- **Sound.** Put it in a tiny `audio.ts` module: lazy context, two functions. Keep it behind the FX flag.
- **Other risks.**
  - The verdict size (`clamp(88px, 15.6vw, 238px)`) must stay within 2 lines. If a future verdict string is longer than "NOT YET.", add a `fit` clamp.
  - The details sheet title is clamped to 2 lines. Titles over about 88 characters at 620px will truncate, so the full title should also appear in the meta or tooltip.
  - `stroke-dashoffset` is paint-only, not compositor-only. That is acceptable for a single 1.1s draw.
  - The V1 CRT overlay currently also has a vignette and flicker variables. This direction uses scanlines only.
