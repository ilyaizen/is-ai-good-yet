# Is AI Good Yet? V2 design specification

**Status:** implementation-ready product and interaction specification  
**Scope:** public `/v2` experience, public static data contracts, and the visual port from `is-ai-good`  
**Stack:** SvelteKit 2, Svelte 5 runes, Tailwind CSS v4, shadcn-svelte primitives, D3/LayerCake, canvas effects  
**Design mode:** visual overhaul with existing pipeline methodology preserved

## 1. Executive summary

V2 is not a reskin of the current Hacker News article table. It is a new dashboard with two clearly ranked content tiers:

1. **Primary:** an editorial feed of AI links posted by the bot system (`aipostsbot`, `aimediabot`, `ainewsbot`), presented as rich preview cards.
2. **Secondary:** Hacker News stories with article and community sentiment, presented as evidence cards rather than rows.

The page answers two different questions:

- **What is moving through the AI information stream now?** The bot feed answers this quickly and visually.
- **What do the source material and visible HN discussion actually say about AI?** The HN sentiment tier answers this with inspectable evidence and visible uncertainty.

The verdict hero remains the entry point, but its job changes. It establishes the aggregate verdict and the three dimensions, then hands off to the feed. It must not become a dense methodology panel.

The V2 design language is a dark broadcast terminal rather than a collection of terminal windows. Full rectangular outlines and corner brackets are retired. Hierarchy comes from surfaces, signal rails, separators, typography, and restrained phosphor light.

## 2. Design read and operating dials

Reading this as a data-heavy terminal dashboard for technically literate readers, with an experimental broadcast-console language. The hero can be theatrical. The evidence UI cannot be cryptic.

| Dial | Value | Consequence |
| --- | ---: | --- |
| Design variance | 7/10 | Asymmetric hero and mixed card spans, but predictable reading order |
| Motion intensity | 6/10 | Ambient canvas motion, verdict decode, and deliberate state transitions |
| Visual density | 8/10 | Compact metadata and diagnostics, with progressive disclosure to prevent overload |

### Non-negotiable principles

1. **Tension is data.** Article and community disagreement is never averaged into invisibility.
2. **Confidence is not sentiment.** Confidence changes influence and visual certainty, not hue or direction.
3. **Evidence before decoration.** Quotes, source labels, and sample diagnostics outrank ornamental terminal chrome.
4. **One page, two tiers.** Bot content is primary. HN analysis is secondary and visually quieter.
5. **Cards, not a table.** Both feeds use cards, but bot cards and HN evidence cards have different structures.
6. **The terminal aesthetic must remain legible.** Monospace does not justify tiny type, low contrast, or unexplained abbreviations.
7. **Static-first delivery.** The public page reads generated JSON. It must not depend on the production SQLite database or admin process at request time.
8. **No production controls in public UI.** Public users see pipeline health, not buttons that run jobs.

## 3. Grounded current-state audit

### 3.1 What exists in `is-ai-good-yet`

The current `/v2` route is a visual shell over V1 static data:

- `src/routes/v2/+page.server.ts:1-33` loads `getStaticVerdictScore`, V1 weekly history, V1 article records, and placeholder pipeline stats.
- `src/routes/v2/+page.svelte:3-9` composes a V2 hero, metrics, chart, discussions, analysis details, and footer.
- `src/lib/components/v2/v2-analysis-details.svelte:5-14` explicitly labels the source as `STATIC V1 CONTRACT` and says no V2 sentiment contract is wired.
- `src/lib/components/v2/v2-discussions.svelte:16-26` still renders a compact discussion list, not evidence cards.
- `src/lib/static-data.ts:188-200` fabricates pipeline stats from article count. Those values are not operational pipeline telemetry.
- `src/lib/data/v2/` does not exist. The V2 exporter targets it, but no reviewed export is currently connected.
- No bot feed implementation or bot identifiers exist in the repository.
- `lil-gui` is not present in `package.json`.
- No cron or scheduler configuration exists in the repository. The current pipeline runner records manually triggered command runs only.
- The broad V2 prefilter contract exists as documentation, but the runner has no isolated `v2_prefilter` command or V2 prefilter storage path. Reusing V1 `prefilter_content` would violate the broadened V2 scope.
- Individual comment analyses are stored, but `export_v2.py` exports aggregate diagnostics only. Exact community comment text is not currently available to public cards.
- The global story influence formula is implemented but not assigned an immutable version identifier.

The current V2 visual layer also repeats the pattern the product owner rejected:

- `src/styles/v2.css:11` applies corner gradients to every `.v2-panel`.
- `src/styles/tokens.css:318-341` defines V2 tokens as hardcoded hex and RGB values inside the token source. These should be converted to the existing OKLCH token architecture before implementation.
- `src/routes/+layout.svelte:130-132` hides the existing scanline component on V2.

### 3.2 What exists in the V2 sentiment pipeline

The V2 methodology is implemented and versioned independently of the page:

- Normative contract: `docs/v2-sentiment-prompt.md`.
- Broad-scope prefilter: `docs/v2-prefilter-prompt.md`.
- Article analysis: `docs/v2-article-sentiment-prompt.md`.
- Strict models and aggregation: `pipeline/src/v2_models.py`.
- Static export target: `pipeline/src/export_v2.py`.

The implemented contract already provides the information needed for an inspectable story card:

- capability, trajectory, and impact scores;
- article and community confidence;
- visibility-weighted and diversity-balanced community scores;
- ranking sensitivity;
- positive, neutral, and negative shares;
- disagreement and polarization;
- effective sample size;
- applicable comment, author, and branch counts;
- dimension coverage and clarity;
- one opposing comment diagnostic when available;
- article evidence excerpts and attribution;
- source divergence;
- combined score and source list.

### 3.3 What exists in the redesign reference

`D:\GitHub\is-ai-good` is the visual reference and contains the correct hero implementation. It is not shader-based and does not require a hero effects package.

The hero consists of:

1. **Animated dotted field** in `src/lib/dotted-glow.ts`.
   - Pure canvas.
   - Staggered grid with independent triangle-wave shimmer.
   - ResizeObserver and IntersectionObserver gating.
   - Static reduced-motion frame.
2. **Dotted rotating globe** in `src/lib/wireframe-globe.ts`.
   - Pure canvas orthographic projection.
   - No D3 dependency.
   - Natural Earth 110m GeoJSON land data.
   - Dotted landmasses, optional graticule, city flicker, limb fade, and reduced-motion support.
3. **Verdict decode and sweep** in `src/lib/anim.ts:76-145` and `src/sections/hero.ts:98-116`.
   - Character scramble settles left to right.
   - A single CSS beam sweeps after decode.
4. **Panel-scoped monochrome grain** in `src/lib/tv-static.ts`.
   - Shared throttled requestAnimationFrame loop.
   - IntersectionObserver skips off-screen surfaces.
   - Disabled on mobile and frozen for reduced motion.

The reference package has no animation, shader, globe, or GUI dependency. Its only runtime dependency is `@fontsource/share-tech-mono`. The page uses custom TypeScript and canvas. V2 should port the behavior, not add Three.js or a shader framework for effects that already work without them.

## 4. Product goals and success criteria

### 4.1 Product goals

- Make the bot-curated AI stream the first content experience after the verdict.
- Preserve HN analysis as the trust and interpretation layer.
- Let a reader understand a story's directional result in under five seconds.
- Let a skeptical reader inspect why the result exists without leaving the card.
- Make source disagreement, polarized discussion, weak samples, and missing dimensions obvious.
- Show that the pipeline is automated, current, and covering the intended AI scope.
- Broaden the product from coding tools to all approved AI scopes.

### 4.2 Measurable acceptance criteria

A V2 release is complete when:

- the first content section after the hero is the bot feed;
- the bot feed can render preview image, title, description, source, bot identity, time, and tags;
- HN stories render as cards and the old article table is absent from `/v2`;
- every HN card exposes article, community, and combined results without implying they are one source;
- every addressed dimension displays score and confidence;
- source divergence is visually emphasized when it crosses the defined threshold;
- disagreement, polarization, and ESS are available without opening a separate route;
- all settings controls work, persist, and survive reload;
- the hero uses the reference dotted field, dotted globe, and verdict decode behavior;
- corner brackets are absent;
- the public pipeline display shows last run, processed count, next run, status, and coverage;
- coding, research, education, labor, economy, creativity, safety, governance, environment, and general are represented in filtering and tags;
- keyboard navigation, reduced motion, and mobile layouts are usable;
- public rendering does not read pipeline SQLite or expose admin logs, paths, process IDs, or credentials.

## 5. Information architecture

### 5.1 Page order

```text
Global masthead
Verdict hero
Pipeline status strip
Primary: Bot signal feed
Secondary: HN sentiment evidence
History and dimensional trends
Methodology summary
Compact footer
Toggleable lil-gui settings overlay
```

### 5.2 Masthead

Desktop layout:

- left: `is-ai-good-yet.com` wordmark and live cursor;
- center: current scope summary such as `ALL AI DOMAINS`;
- right: `FEED`, `HN EVIDENCE`, `HISTORY`, `METHOD`, and a settings trigger.

Rules:

- one line at 1024px and above;
- no version label;
- no decorative status dots except the real pipeline status indicator;
- settings trigger uses a terminal control label such as `[ CTRL ]`, not a gear-only mystery icon;
- the skip link targets `#main-content`.

Mobile layout:

- wordmark remains visible;
- section navigation collapses into a single accessible menu;
- settings remains a dedicated control;
- no horizontal overflow.

### 5.3 Composition wireframes

Desktop reading order:

```text
┌ wordmark ───────────── all AI domains ───── feed  evidence  history  [CTRL] ┐
│                                                                              │
│  $ ./assess --scope all-ai --window 12m          dotted globe                │
│  Is AI good yet?                                                            │
│  NOT YET                                                                    │
│  capability +0.6      trajectory +1.1      impact -0.2                      │
│                                                                              │
├ CURRENT ─ last run 18m ─ 143 stories ─ next 05:00 UTC ─ coverage 87% ───────┤
│                                                                              │
│  AI signal feed                                                             │
│  ┌──────────────────────── featured bot card ─────────────────────────────┐  │
│  │ preview image     source, title, description, scopes, bot, time         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│  ┌ standard bot card ─────────────┐  ┌ standard bot card ─────────────────┐  │
│  └────────────────────────────────┘  └─────────────────────────────────────┘  │
│                                                                              │
│  HN evidence                                                                │
│  ┌ story title, source, combined verdict, points, comments ────────────────┐  │
│  │ capability    article ●────────────○ community     divergence 1.3       │  │
│  │ trajectory    article ○────● community             ESS 9.4              │  │
│  │ impact        article ●──○ community               polarization 0.62    │  │
│  │ article evidence            community summary             [DETAILS]     │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  dimensional history                                                        │
│  methodology                                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

Mobile reading order:

```text
wordmark                         [CTRL]

hero verdict
capability
trajectory
impact

pipeline status, two rows

AI signal feed
featured card
standard card
standard card

HN evidence
story header
combined result
capability source axis
trajectory source axis
impact source axis
quotes
[DETAILS]

history
methodology
```

The wireframes define hierarchy, not literal borders. Final cards use the open signal-frame system described below.

## 6. Visual system

### 6.1 Theme

V2 is dark-only by product direction. Do not carry V1's light mode into V2. Set `color-scheme: dark` at the V2 route boundary and keep every section in the same dark family.

This is an explicit exception to the site's global theme behavior. It should not leak into V1 or admin routes.

### 6.2 Color roles

All final values belong in `src/styles/tokens.css` as OKLCH variables. Components consume semantic tokens only.

| Role | Use |
| --- | --- |
| `--v2-canvas` | page background, tinted near-black |
| `--v2-recess` | inset diagnostics and loading skeletons |
| `--v2-surface-1` | standard cards |
| `--v2-surface-2` | selected, expanded, or elevated cards |
| `--v2-text` | primary readable text |
| `--v2-text-muted` | metadata |
| `--v2-text-faint` | non-critical labels only |
| `--v2-phosphor` | brand accent, focus, positive direction |
| `--v2-amber` | neutral, caution, low adequacy |
| `--v2-red` | negative direction, failed status |
| `--v2-cyan` | article source identity only |
| `--v2-violet` | community source identity only |

The design uses multiple semantic colors because the data requires independent source and direction encoding. The brand accent remains phosphor lime. Cyan and violet must be muted and reserved for source comparison, not decorative gradients.

### 6.3 Sentiment encoding

Direction and confidence use different visual channels:

- **Direction:** hue and signed number.
- **Confidence:** opacity, line solidity, and explicit numeric or text label.
- **Source:** label and marker shape.
- **Disagreement:** distance between source markers and a tension treatment.
- **Polarization:** split directional distribution, never a confidence penalty.
- **Missingness:** `N/A`, never zero.

Do not use hue alone. Every colored result includes a sign and readable label.

### 6.4 Typography

- Display verdict: Share Tech Mono.
- Interface and data: IBM Plex Mono.
- Dense explanatory copy: Armata or the existing sans token.
- All numbers use tabular figures.
- Minimum body size: 14px.
- Minimum metadata size: 12px.
- Uppercase and wide tracking are restricted to compact control labels, not paragraphs.

The V2 page does not need the decorative serif.

### 6.5 Shape and border system

The current corner-bracket treatment is removed completely.

#### Recommended replacement: open signal frame

Cards use:

- a surface contrast step instead of a full bright perimeter;
- one 2px semantic rail on the left or top;
- one low-contrast separator where content sections meet;
- a faint inner top highlight;
- 2px to 4px radius, consistently;
- no pseudo-element corner marks.

This keeps the terminal instrumentation feel without drawing a box around every block.

#### Secondary alternative: channel plate

For wide sections such as history:

- no exterior border;
- a recessed header strip;
- one bottom hairline;
- clipped top-left notch using `clip-path`, used once per major section rather than on every card.

#### Rejected alternatives

- four corner ticks;
- repeated crosshairs;
- neon outlines on every card;
- macOS traffic-light terminal windows;
- glass cards with large rounded corners;
- heavy bevels that compete with the data.

### 6.6 Depth

Use three depth levels only:

1. page canvas;
2. card surface;
3. expanded diagnostic surface or settings overlay.

Shadows are dark green-tinted and restrained. Glow belongs to active phosphor text, focus, or a live marker, not every edge.

## 7. Hero specification

### 7.1 Content hierarchy

The hero contains:

1. command line: `$ ./assess --scope all-ai --window 12m`;
2. real pipeline state: `ANALYSIS CURRENT`, `UPDATING`, `STALE`, or `DEGRADED`;
3. question: `Is AI good yet?`;
4. aggregate answer: `YES`, `NO`, or `NOT YET`;
5. one-line aggregate explanation;
6. three compact dimension readouts;
7. data window and analyzed story count.

It must fit within the initial desktop viewport with the masthead. The hero is not a methodology dump.

### 7.2 Aggregate verdict treatment

- Decode the verdict once on first reveal.
- After decode, run one horizontal signal beam.
- Replay is allowed from a small text control near methodology or footer, not a sticky action bar.
- The final verdict remains selectable text and has an explicit screen-reader label.
- The combined composite is secondary to the three dimension readouts. The large word answers the brand question; the dimension row prevents it from pretending AI has one axis.

### 7.3 Dimension readouts

Each dimension shows:

- label;
- combined signed score in `-2..2`;
- 0-100 display mapping as optional secondary text;
- combined confidence;
- direction word: negative, mixed, or positive;
- addressed story count.

Do not show three large equal metric cards under the verdict. Use one horizontal instrument rail with three cells separated by spacing and thin rules.

### 7.4 Background effects to port

Port the reference effects as Svelte client components or Svelte actions:

```text
src/lib/components/v2/effects/dotted-glow.svelte
src/lib/components/v2/effects/dotted-globe.svelte
src/lib/components/v2/effects/crt-grain.svelte
src/lib/actions/verdict-decode.ts
```

Implementation requirements:

- direct port of the reference canvas math and timing;
- no Three.js dependency for the hero;
- cap device pixel ratio at 2;
- pause when the hero is outside the viewport;
- pause when the document is hidden;
- use ResizeObserver for canvas sizing;
- use a static frame under `prefers-reduced-motion: reduce`;
- tear down observers, timers, network work, and animation frames on component destroy;
- preserve the reference's shared low-frame-rate analog cadence;
- keep canvases `aria-hidden` and pointer-events disabled.

### 7.5 Globe asset strategy

The reference globe fetches Natural Earth GeoJSON. For production V2:

- vendor the compressed Natural Earth 110m data under `static/data/`;
- fetch it from the same origin;
- cache the parsed data at module scope;
- show the dotted field without the globe if the asset fails;
- do not block hero text or LCP on the globe request.

### 7.6 CRT treatment

V2 currently suppresses the site scanlines. V2 should provide its own adjustable overlay:

- fixed or document-sized pseudo-element, pointer-events none;
- scanline opacity controlled by `--v2-scanline-opacity`;
- vignette controlled by `--v2-vignette-opacity`;
- optional panel grain controlled by `--v2-grain-opacity`;
- disabled or frozen under reduced motion;
- mobile default intensity is lower than desktop.

## 8. Pipeline status strip

### 8.1 Purpose

This replaces the production user's need to visit the manual admin control panel. It proves the data is maintained by an automated cron job and tells the reader when it is not.

### 8.2 Placement

A single full-width status strip sits immediately below the hero and above the bot feed. It is visually integrated with the page, not a card grid.

### 8.3 Required fields

- status: current, running, delayed, degraded, or failed;
- last successful run timestamp and relative time;
- last run duration;
- articles or stories processed in the last successful run;
- comments analyzed in the last successful run;
- next scheduled run;
- corpus coverage percentage;
- article-analysis coverage percentage;
- community-analysis coverage percentage;
- bot preview coverage percentage;
- schedule description, for example `every 6 hours`.

### 8.4 Status rules

```text
if active run exists:
  RUNNING
else if last run failed:
  FAILED
else if now > next scheduled run + grace period:
  DELAYED
else if any required coverage is below configured floor:
  DEGRADED
else:
  CURRENT
```

Status color is semantic. The only animated status dot on the page belongs here.

### 8.5 Public telemetry contract

Generate `src/lib/data/v2/pipeline-status.json` from the cron wrapper after every run.

```ts
interface V2PipelineStatus {
  contractVersion: "pipeline-status-v2.0.0";
  generatedAt: string;
  schedule: {
    expression: string;
    timezone: string;
    human: string;
    nextRunAt: string;
    graceMinutes: number;
  };
  currentRun: null | {
    runId: string;
    startedAt: string;
    stage: "discover" | "scrape" | "prefilter" | "article" | "comments" | "export";
  };
  lastRun: {
    runId: string;
    status: "succeeded" | "failed" | "partial";
    startedAt: string;
    finishedAt: string;
    durationSeconds: number;
    storiesDiscovered: number;
    articlesProcessed: number;
    commentsAnalyzed: number;
    errorCode: string | null;
  } | null;
  coverage: {
    corpusEligible: number;
    articleAnalyzed: number;
    communityAnalyzed: number;
    botPreviewReady: number;
    articlePercent: number;
    communityPercent: number;
    botPreviewPercent: number;
  };
}
```

The public contract must not include log paths, PIDs, environment checks, API-key state, raw errors, or admin command names.

### 8.6 Pipeline gap

The existing `pipeline_runs` table in `src/lib/server/pipeline-runner.ts:146-167` records manual command runs. It does not represent an end-to-end scheduled job, next run, per-run processed counts, or coverage snapshots. A cron wrapper or orchestration record must write those values. Do not infer them from article count as `getStaticPipelineStats` currently does.

## 9. Primary content tier: bot signal feed

### 9.1 Purpose

The bot feed is the rapid-discovery surface. It is not sentiment-scored by default and must not inherit HN scoring language unless a bot link also has a matched HN analysis.

### 9.2 Feed hierarchy

Section title: `AI signal feed`  
Default sort: newest first  
Default time window: 7 days  
Default density: comfortable

The first viewport after the hero should show at least one complete card and the beginning of the next row.

### 9.3 Card layout

Desktop uses an asymmetric grid:

- first or most recent high-quality preview can span two columns;
- remaining cards use a two-column layout;
- do not use three equal cards;
- image aspect ratio is 16:9 for wide cards and 4:3 for standard cards;
- missing-image cards become text-led and do not reserve a blank image rectangle.

Each card contains:

1. preview image when available;
2. normalized source domain and favicon;
3. title, maximum three lines;
4. scraped description, maximum four lines;
5. source bot handle;
6. source post time;
7. canonical article time when available;
8. topic tags from the V2 scope taxonomy;
9. action links: `OPEN SOURCE` and `OPEN BOT POST`;
10. optional matched-HN indicator that links to the corresponding evidence card.

### 9.4 Bot card states

- **Complete:** image, title, description, source.
- **Text-only:** no valid image, clean text composition.
- **Partial metadata:** title and domain only, with `PREVIEW LIMITED`.
- **Duplicate:** hidden by default and represented by one card with a source-count disclosure.
- **Unavailable source:** card remains as an archive record, action disabled with reason.
- **Loading:** card-shaped skeleton with image region only when the expected record has an image.
- **Empty:** explain the selected filters have no bot links and offer one reset action.
- **Error:** retain cached cards and show a compact stale-data message.

### 9.5 Bot feed contract

The repository currently has no bot feed contract. The upstream platform is intentionally abstracted behind the pipeline. The frontend consumes normalized static JSON regardless of whether the source adapter reads Telegram, X, RSS, or another service.

Generate `src/lib/data/v2/bot-feed.json`:

```ts
interface BotFeedItem {
  id: string;
  contractVersion: "bot-feed-v2.0.0";
  bot: "aipostsbot" | "aimediabot" | "ainewsbot";
  botPostUrl: string;
  postedAt: string;
  canonicalUrl: string;
  canonicalUrlHash: string;
  domain: string;
  title: string;
  description: string | null;
  image: {
    url: string;
    width: number | null;
    height: number | null;
    alt: string;
  } | null;
  faviconUrl: string | null;
  publishedAt: string | null;
  author: string | null;
  scopes: V2Scope[];
  previewStatus: "complete" | "partial" | "failed";
  duplicateCount: number;
  matchedHnStoryId: number | null;
}

type V2Scope =
  | "coding"
  | "research"
  | "education"
  | "labor"
  | "economy"
  | "creativity"
  | "safety"
  | "governance"
  | "environment"
  | "general";
```

### 9.6 Metadata scraping rules

Priority:

1. Open Graph metadata;
2. Twitter card metadata;
3. document title, meta description, and first valid content image;
4. safe text fallback from the bot post.

Requirements:

- canonicalize URLs before deduplication;
- reject tracking pixels and images below minimum dimensions;
- proxy or cache remote images if required by the deployment's CSP and reliability policy;
- sanitize all scraped text;
- never render upstream HTML;
- store scrape timestamp and preview status in the pipeline even if not exposed on the card;
- one canonical link can aggregate posts from multiple bots.

## 10. Secondary content tier: HN sentiment evidence cards

### 10.1 Purpose

This tier is the analytical core. It should read like an evidence terminal, not a social feed and not a spreadsheet.

Section title: `HN evidence`  
Default sort: influence within the selected time window  
Default card state: summary expanded enough to show source tension and all three dimensions

### 10.2 Card summary anatomy

Every card shows:

1. title;
2. source domain;
3. publication or HN date;
4. topic tags;
5. HN points and comments;
6. combined verdict and composite score;
7. community verdict summary;
8. three dimension rows;
9. article versus community tension display;
10. one key article quote;
11. one key community quote or dissent quote when available;
12. sample adequacy summary;
13. disclosure control for full diagnostics.

### 10.3 Header row

The card header uses a two-column structure:

- left: title, source, scopes;
- right: combined composite, confidence, HN engagement.

The combined result is labeled `COMBINED`. Never present it as community sentiment.

### 10.4 Dimension score module

Each dimension row contains:

```text
CAPABILITY     COMBINED +0.8   CONF 0.74
ARTICLE +1.0 ●────────────○ COMMUNITY -0.3
DIVERGENCE 1.3  POLARIZED 0.62  ESS 9.4
```

This is a conceptual layout, not literal ASCII styling.

Required values:

- article score and confidence;
- community visibility-weighted score and confidence;
- combined score and confidence;
- source divergence;
- disagreement;
- polarization;
- ESS;
- not-addressed state per source.

Use a shared signed axis from `-2` to `+2` with separate article and community markers. The axis has no filled progress track. A connector between markers becomes the divergence signal.

### 10.5 Source divergence treatment

Per dimension:

```text
divergence = abs(article_score - community_score)
```

Display levels:

| Divergence | Treatment |
| ---: | --- |
| unavailable | no comparison, show source missing |
| `< 0.5` | aligned, quiet connector |
| `0.5 to < 1.0` | mild tension, visible label |
| `1.0 to < 2.0` | strong tension, amber connector and `SOURCES DIVERGE` |
| `>= 2.0` | direct conflict, split treatment and `SOURCE CONFLICT` |

If signs differ, show `OPPOSING DIRECTIONS` regardless of magnitude threshold. This is more important than the combined average.

The card's left signal rail may use a split cyan/violet treatment when sources oppose. Do not collapse conflict into a neutral gray card.

### 10.6 Confidence display

- show confidence as `0.00-1.00` in expanded diagnostics;
- summary can use `HIGH`, `MED`, or `LOW` plus the numeric value in a tooltip;
- never color low-confidence positive data as negative;
- low confidence uses a lighter marker and dashed connector;
- missing evidence uses `N/A`, not `0.00`.

Suggested summary labels:

```text
LOW: < 0.45
MED: 0.45 to < 0.75
HIGH: >= 0.75
```

These are display labels only. The underlying numeric value remains normative.

### 10.7 Community diagnostics

The expanded card shows, per dimension:

- visibility-weighted score, primary;
- diversity-balanced score, diagnostic;
- ranking sensitivity;
- positive, neutral, and negative shares;
- disagreement;
- polarization;
- effective sample size;
- applicable comments;
- applicable authors;
- applicable branches;
- dimension coverage;
- clarity;
- highest-influence opposing comment and share, when available.

Use a compact diagnostic grid grouped into:

1. **Estimate:** visibility, diversity, sensitivity.
2. **Distribution:** positive, neutral, negative, disagreement, polarization.
3. **Adequacy:** ESS, comments, authors, branches, coverage, clarity.

### 10.8 Sample adequacy treatment

ESS is not raw comment count and must not be labeled as such.

Display:

```text
SAMPLE  ESS 9.4 / 12 target
INPUT   18 analyzed, 11 applicable
SPREAD  8 authors across 5 branches
```

Adequacy state:

- `ROBUST` when ESS >= 12 and branch adequacy is saturated;
- `USABLE` when ESS >= 6;
- `THIN` when ESS < 6;
- `NONE` when the dimension is not addressed.

These are UI summaries, not changes to the confidence formula.

### 10.9 Disagreement and polarization

Disagreement and polarization are distinct:

- disagreement means comments vary around the community estimate;
- polarization requires meaningful positive and negative mass separated in direction.

Display both. Do not replace them with one `controversial` badge.

Distribution uses three numeric shares and a thin segmented line. It has no background track and includes text labels for accessibility.

### 10.10 Quotes

Summary state shows up to two quotes:

- one exact article evidence excerpt with attribution;
- one community summary, dissent, or representative quote.

Rules:

- maximum three visual lines per quote in summary;
- full exact excerpt available in expanded view;
- label article and HN source explicitly;
- do not manufacture a community quote from the model summary;
- if only a summary is exported, label it `COMMENT SUMMARY`, not a quote;
- link comment IDs to HN where possible.

Current export limitation: the dissent diagnostic contains `comment_id`, model summary, and opposing influence share, but not exact comment text. V2 must either add an allowlisted comment excerpt to the public export or render the diagnostic as `COMMENT SUMMARY`. It must not put quotation marks around generated summaries.

### 10.11 Card expansion

- use an inline disclosure, not a modal;
- only one card needs to be expanded at a time on mobile;
- desktop may allow multiple expanded cards;
- preserve expanded state while settings filters change if the story remains visible;
- use `aria-expanded` and an associated region;
- animate opacity and transform only;
- reduced motion opens instantly.

### 10.12 Story card contract

The frontend should define a typed adapter around `pipeline/src/export_v2.py:132-179`, not import arbitrary JSON as `any`.

```ts
interface V2StoryCard {
  hnId: number;
  title: string;
  url: string;
  domain: string;
  hnScore: number;
  hnComments: number;
  hnTimestamp: number;
  scopes: V2Scope[];
  summary: string;
  evidence: V2Evidence[];
  article: V2SourceAnalysis;
  community: V2CommunityAnalysis | null;
  combined: {
    dimensions: Record<V2Dimension, V2CombinedDimension>;
    composite: number | null;
    addressedDimensions: V2Dimension[];
  };
  sourceDivergence: Record<V2Dimension, number | null>;
}

type V2Dimension = "capability" | "trajectory" | "impact";
```

The exporter currently preserves snake_case story fields and nested result objects. Before wiring the route, add one explicit server-side mapping layer that returns stable camelCase page data. Do not let components know SQLite or Python naming conventions.

## 11. Scoring semantics

### 11.1 Dimension definitions

- **Capability:** present performance and usefulness.
- **Trajectory:** expected change from today's baseline.
- **Impact:** net effect on people, institutions, and society.

Scores are integers at annotation time from `-2` to `+2`. Aggregates are continuous in the same range.

`0` means expressed balance or neutrality. `not_addressed` means missing evidence. The UI must never treat those as equivalent.

### 11.2 Article source

The article result includes:

- applicability;
- score;
- confidence;
- rationale;
- evidence IDs;
- exact evidence excerpts;
- attribution;
- scopes;
- concise article summary.

Article confidence measures annotation clarity. It does not claim that the article is true.

### 11.3 Community source

Community sentiment measures visible expressed HN discussion at collection time. It does not represent all readers, all HN users, or public opinion.

Sampling:

```text
accepted_target = min(E, clamp(12, 32, ceil(4 * sqrt(E))))
top_level_target = ceil(0.60 * accepted_target)
reply_target = accepted_target - top_level_target
branch_cap = max(3, ceil(0.15 * accepted_target))
author_cap = 2
```

Each voting comment is analyzed in an isolated request with article thesis, root, and parent as context-only material.

### 11.4 Primary and diagnostic community estimates

```text
visibility_weighted_score = primary estimate
diversity_balanced_score = diagnostic estimate
ranking_sensitivity = abs(visibility_weighted_score - diversity_balanced_score)
```

The primary score represents the publicly ranked discussion. The diversity estimate tests how sensitive the result is to public visibility ordering.

### 11.5 Community confidence

```text
clarity = structurally weighted mean annotation confidence
ESS = (sum weights)^2 / sum(weights^2)
sample_adequacy = min(1, ESS / 12)
branch_adequacy = min(1, applicable_branch_count / 6)
dimension_coverage = applicable_selected / analyzed_selected
community_confidence = clarity * sqrt(sample_adequacy * branch_adequacy * dimension_coverage)
```

Disagreement and polarization do not reduce confidence. They describe the measured distribution.

### 11.6 Source combination

For every applicable dimension:

```text
combined = sum(score * prior * confidence) / sum(prior * confidence)
article prior = 0.4
community prior = 0.6
```

Rules:

- confidence changes influence only;
- confidence never changes score direction or distance from neutral;
- if one source is not addressed, use the other source without inventing a zero;
- show which sources contributed;
- compute the equal-dimension composite only across addressed dimensions;
- keep the three dimensions primary and the composite secondary.

### 11.7 Display mapping

The current exporter maps raw score to a 0-100 display value:

```text
display = (clamp(raw, -2, 2) + 2) * 25
YES      display >= 55
NO       display < 45
NOT YET  otherwise
```

V2 cards should primarily show the signed `-2..2` score because it preserves direction and magnitude. The 0-100 mapping is useful for the hero, aggregate history, and public familiarity. Never mix both scales without labels.

## 12. lil-gui settings overlay

### 12.1 Dependency and loading

Add `lil-gui` as a runtime dependency. It is currently absent.

Load it client-side only:

- dynamic import inside `onMount`;
- no SSR access to `window`, `document`, or `localStorage`;
- destroy the GUI instance on component teardown;
- isolate all GUI integration in one component.

Suggested file:

```text
src/lib/components/v2/v2-settings-gui.svelte
src/lib/state/v2-settings.svelte.ts
```

### 12.2 Controls

Folders and controls:

```text
DIMENSIONS
  Capability [on/off]
  Trajectory [on/off]
  Impact [on/off]

WINDOW
  Time window [24h, 7d, 30d, 90d, 12m, all]

SCORES
  Minimum combined score [-2..2]
  Maximum combined score [-2..2]
  Minimum confidence [0..1]
  Show source conflicts [on/off]

DISPLAY
  Density [compact, comfortable, expanded]
  Sort [newest, influence, divergence, polarization]
  Preview images [on/off]

CRT
  Scanline opacity [0..0.16]
  Vignette strength [0..0.30]
  Grain opacity [0..0.10]
  Ambient motion [on/off]

ACTIONS
  Reset filters
  Reset visual effects
```

Bot feed ignores sentiment score thresholds but obeys time window, topic scope, density, preview image, and sort where applicable. HN evidence obeys all relevant controls.

### 12.3 Settings state

```ts
interface V2Settings {
  version: 1;
  dimensions: {
    capability: boolean;
    trajectory: boolean;
    impact: boolean;
  };
  timeWindow: "24h" | "7d" | "30d" | "90d" | "12m" | "all";
  scoreMin: number;
  scoreMax: number;
  confidenceMin: number;
  conflictsOnly: boolean;
  density: "compact" | "comfortable" | "expanded";
  sort: "newest" | "influence" | "divergence" | "polarization";
  previewImages: boolean;
  scanlineOpacity: number;
  vignetteStrength: number;
  grainOpacity: number;
  ambientMotion: boolean;
}
```

Persist under `is-ai-good-yet:v2:settings:1`.

On load:

1. start from defaults;
2. parse stored JSON defensively;
3. migrate known old versions;
4. clamp all numeric values;
5. discard invalid enums;
6. apply visual values as CSS custom properties on the V2 route root.

Do not place filter state in URL for the first release. Add shareable query state only if users demonstrate a need.

### 12.4 Native terminal styling

Override lil-gui variables inside a V2-scoped wrapper:

- square 2px corners;
- Share Tech Mono or IBM Plex Mono;
- dark recessed background;
- phosphor focus and active state;
- thin separators instead of rounded field boxes;
- no default blue accents;
- labels in readable sentence case or compact uppercase;
- controller widths large enough for full labels;
- overlay title `DISPLAY CONTROL`;
- close button rendered as `[x]` or `ESC`, not a floating circular icon.

The overlay enters from the right as an instrumentation drawer at desktop and becomes a near-full-width bottom sheet on mobile.

### 12.5 Accessibility

- trigger is a native button with `aria-expanded` and `aria-controls`;
- Escape closes the panel;
- focus moves into the overlay on open and returns to the trigger on close;
- background content is inert while the mobile sheet is open;
- every control has an accessible name and visible value;
- keyboard operation is verified for lil-gui controllers;
- reduced motion and OS contrast preferences override saved ambient-motion preferences where required.

## 13. History and trends

### 13.1 Chart purpose

History answers how sentiment changes over time, by dimension and source. It comes after both content tiers so current evidence has context before abstraction.

### 13.2 Required series

- combined capability;
- combined trajectory;
- combined impact;
- optional composite;
- article and community source lines when source comparison is enabled.

Dimension toggles from settings control visible series. The chart's own legend can temporarily isolate a series without changing global settings.

### 13.3 Chart behavior

- LayerCake/D3 handles scales and interaction;
- no hand-built string polyline as in the partial V2 chart;
- signed raw axis from `-2` to `+2` is preferred for detailed mode;
- optional 0-100 mode is only for aggregate verdict continuity;
- zero line is explicit;
- tooltip shows date, source, score, confidence, story count, and addressed count;
- source conflict periods can be shaded lightly;
- keyboard focus can step through data points or use an adjacent accessible data summary;
- no endless radar ping on the endpoint when reduced motion is requested.

## 14. Scope taxonomy

The approved V2 scopes are:

| Scope | Definition cue |
| --- | --- |
| coding | software development, tools, agents, code generation |
| research | scientific work, discovery, reasoning, evaluation |
| education | teaching, learning, assessment, student use |
| labor | jobs, work design, displacement, productivity |
| economy | firms, markets, investment, macroeconomic effects |
| creativity | art, writing, music, design, media |
| safety | reliability, misuse, alignment, systemic risk |
| governance | regulation, institutions, policy, rights |
| environment | energy, water, emissions, climate effects |
| general | substantive cross-domain or uncategorized AI claims |

Rules:

- a story can have multiple scopes;
- scopes are not sentiment;
- use the same labels and order in bot cards, HN cards, settings, and methodology;
- no coding-first default filter;
- `general` is a real fallback, not a place to dump failed classification.

## 15. Responsive behavior

### 15.1 Desktop, 1200px and above

- content max width: 1280px to 1440px;
- hero uses left verdict and right globe bleed;
- bot feed uses asymmetric two-column layout;
- HN cards are one column for readability, with internal multi-column diagnostics;
- settings drawer width: approximately 360px;
- pipeline status is a single horizontal strip.

### 15.2 Tablet, 768px to 1199px

- hero globe becomes quieter and shifts farther right;
- bot feed uses two equal reading columns only when cards remain at least 320px wide;
- HN card diagnostics collapse from three groups to two columns;
- masthead labels condense;
- pipeline strip wraps into two logical rows.

### 15.3 Mobile, below 768px

- strict one-column layout;
- hero globe opacity reduced or disabled on low-power mode;
- verdict size capped to avoid clipping;
- dimension rail becomes three stacked rows;
- bot preview images use 16:9 full width;
- HN source axis remains visible and horizontally fits without scrolling;
- expanded diagnostics become stacked groups;
- settings becomes a bottom sheet;
- card metadata wraps by semantic groups, not arbitrary flex wrapping;
- no sticky footer bar;
- panel grain defaults off.

## 16. Interaction and motion

### 16.1 Motion inventory

| Motion | Meaning | Behavior |
| --- | --- | --- |
| Dotted field shimmer | ambient signal activity | low-frame-rate canvas, hero only |
| Globe rotation | global AI scope | slow, background, pauses off-screen |
| Verdict decode | analysis resolving | once on reveal, replayable |
| Verdict beam | result lock-in | once after decode |
| Card expansion | hierarchy and state change | short transform and opacity |
| Settings drawer | control context | directional slide |
| Pipeline pulse | active run only | one semantic live indicator |
| Chart transition | filter change | preserve shape continuity |

No animation exists only because it looks terminal-like.

### 16.2 Reduced motion

Under `prefers-reduced-motion: reduce`:

- verdict renders final text immediately;
- globe and dotted field render a static frame;
- grain freezes or disappears;
- settings opens without travel;
- card disclosures open instantly;
- chart transitions are disabled;
- status pulse becomes a static marker.

Saved `ambientMotion: true` cannot override the OS preference.

### 16.3 Performance budget

- no Three.js for hero effects;
- one shared animation scheduler for V2 ambient canvases where practical;
- no more than 20 frames per second for analog ambient effects;
- no canvas larger than 2x device-pixel ratio;
- lazy-load bot preview images below the fold;
- reserve image aspect ratio to avoid layout shift;
- dynamically import lil-gui;
- parse large V2 exports on the server and return filtered initial page data when export size requires it;
- virtualize only after measurement proves card count causes a real problem;
- target LCP under 2.5 seconds, INP under 200ms, CLS under 0.1.

## 17. Accessibility and semantics

- page uses semantic `main`, `section`, `article`, `header`, `footer`, and `nav` elements;
- every story card is an `article` with a unique heading;
- external links disclose that they open a new destination;
- score axes include readable text equivalents;
- no information relies only on color, glow, animation, or spatial position;
- focus-visible outline uses the phosphor token and remains visible over every surface;
- all controls have at least 44px mobile hit targets;
- headings follow one hierarchy without skipped levels;
- decorative canvases and CRT overlays are hidden from assistive technology;
- image alt text describes the preview content when meaningful, otherwise the image is decorative because title and source already identify the card;
- chart has a text summary and accessible point data;
- loading, empty, stale, partial, and failed states are announced appropriately without interruptive alerts.

## 18. Loading, empty, stale, and error states

### 18.1 Page loading

Do not use the current full-page theatrical loader on every navigation. It delays access to static data.

- first cold visit may use a brief hero signal acquisition sequence capped at 500ms;
- client navigations render immediately;
- content skeletons match card shapes;
- hero text is server-rendered and never waits for canvas effects.

### 18.2 Stale data

If current time exceeds next scheduled run plus grace:

- pipeline status becomes `DELAYED`;
- hero continues to show the last accepted verdict;
- timestamp remains visible;
- feeds remain usable;
- no modal or full-page blocker.

### 18.3 Partial analysis

If article exists but community is missing:

- show article source normally;
- community displays `PENDING` or `NOT AVAILABLE` based on pipeline state;
- combined score uses the article source only and explicitly says `ARTICLE ONLY`;
- never insert community zero.

If community exists but article analysis is unavailable:

- show `COMMUNITY ONLY`;
- preserve the same rule in combined source labels.

### 18.4 Export failure

Serve the last known good static export. Public status reports the failed run. Do not replace good data with empty JSON.

## 19. Component architecture

Suggested public V2 structure:

```text
src/lib/components/v2/
  shell/
    v2-masthead.svelte
    v2-pipeline-status.svelte
    v2-footer.svelte
  hero/
    v2-verdict-hero.svelte
    v2-dimension-rail.svelte
  effects/
    dotted-glow.svelte
    dotted-globe.svelte
    crt-overlay.svelte
    panel-grain.svelte
  bot-feed/
    bot-feed-section.svelte
    bot-feed-card.svelte
    bot-feed-skeleton.svelte
    bot-feed-empty.svelte
  evidence/
    hn-evidence-section.svelte
    hn-story-card.svelte
    source-tension-axis.svelte
    dimension-score-row.svelte
    community-diagnostics.svelte
    evidence-quotes.svelte
    sample-adequacy.svelte
  history/
    v2-history-chart.svelte
    chart-legend.svelte
  settings/
    v2-settings-gui.svelte
  methodology/
    v2-methodology-summary.svelte

src/lib/state/
  v2-settings.svelte.ts

src/lib/types/
  v2.ts

src/lib/server/
  v2-data.ts
  v2-page-adapter.ts
```

### Architecture rules

- use Svelte 5 runes;
- shared data transformations live outside components;
- no component reads localStorage directly except the settings store boundary;
- no component imports raw JSON directly;
- no component knows pipeline table names;
- canvas effects are isolated and disposable;
- CSS variables carry user-adjustable visual effects;
- design tokens remain the only source of color values;
- shadcn-svelte can provide accessible disclosure, tooltip, toggle, and sheet behavior, but default styling must be replaced.

## 20. Static export architecture

### 20.1 Public files

```text
src/lib/data/v2/
  verdict.json
  stories.json
  history.json
  bot-feed.json
  pipeline-status.json
  manifest.json
```

### 20.2 Manifest

```ts
interface V2Manifest {
  contractVersion: "v2-manifest-1";
  generatedAt: string;
  influenceVersion: string;
  files: Record<string, {
    contractVersion: string;
    recordCount: number;
    sha256: string;
  }>;
}
```

The manifest lets the server reject mixed-generation files and keep the last known good dataset.

The global influence function (`HN score^0.85` with a 24-month half-life) must receive an immutable version before production publication. A changed exponent or half-life changes the aggregate verdict even when story-level analyses are identical.

### 20.3 Atomic publication

The cron job should:

1. run collection and analysis;
2. write all exports to a temporary generation directory;
3. validate required contracts and counts;
4. write the manifest last;
5. atomically swap the generation into the public data path;
6. retain the previous generation for rollback;
7. update public pipeline status even when analysis fails.

Do not write public JSON files one by one into the live directory. That can expose a verdict from one run with stories from another.

### 20.4 Server load

`src/routes/v2/+page.server.ts` should use one `loadV2PageData()` adapter that:

- validates manifest and contract versions;
- maps snake_case export fields to camelCase page data;
- returns initial bot and HN pages plus aggregate data;
- returns status and generated timestamp;
- falls back to the last known good generation;
- returns typed empty states rather than V1 data.

Never silently fall back from V2 to V1. A V2 route showing V1 methodology is worse than an explicit `data unavailable` state.

## 21. Pipeline automation design

### 21.1 Scheduled sequence

```text
Cron trigger
  -> discover new HN and bot links
  -> resolve and canonicalize URLs
  -> scrape article and preview metadata
  -> isolated broad V2 prefilter
  -> article analysis
  -> ranked HN comment collection
  -> isolated community analysis
  -> aggregate and export
  -> validate generation
  -> atomic publish
  -> write status and coverage
```

The external scheduler owns timing. The application exposes status only.

The isolated prefilter stage is a required implementation gap, not an alias for the existing coding-focused V1 prefilter. It must persist its own versioned decision and scopes without overwriting V1 category fields.

### 21.2 Run identity

Every scheduled run needs one orchestration-level `runId` shared across stages. Existing command-level rows can remain for admin diagnostics, but public status and export provenance should reference the orchestration run.

### 21.3 Retry behavior

- failed individual stories remain retryable without failing the whole generation;
- failed export validation blocks publication;
- failed bot preview scraping produces a partial bot card, not a dropped link;
- model failures preserve prior accepted analyses when contract versions match;
- retries must not create duplicate public cards;
- cron overlap is rejected by a lock;
- stale locks become a failed run with an explicit machine-readable error code.

## 22. SEO and metadata

Update V2 metadata to reflect the broadened scope:

- title: `Is AI Good Yet? AI sentiment from Hacker News`;
- description mentions article and community analysis across capability, trajectory, and impact;
- remove coding-tools-only keywords and copy;
- canonical URL must match the actual production host and `/v2` rollout strategy;
- generate a V2 OG image using the verdict and three dimension values;
- story cards are not separate indexable pages unless a stable V2 detail route is intentionally added;
- preserve existing V1 URLs during rollout.

## 23. Privacy and security

- sanitize scraped metadata and never render raw HTML;
- restrict image sources through CSP or a controlled proxy;
- strip tracking parameters during canonicalization;
- do not expose bot platform credentials or private post identifiers;
- public pipeline telemetry is an allowlisted export, not a serialized admin object;
- no admin action endpoints are linked from public V2;
- external links use `rel="noreferrer"` where appropriate;
- localStorage contains only display preferences, no user identity or server state.

## 24. Implementation phases

### Phase 1: contract and shell

Deliver:

- typed V2 frontend contracts;
- executable and stored V2 broad-prefilter contract, isolated from V1;
- immutable global-influence version;
- `src/lib/data/v2/` manifest structure;
- V2 page adapter with explicit unavailable states;
- token cleanup to OKLCH semantic variables;
- masthead and page section skeleton;
- removal of V1 fallback from `/v2`.

Done when the route renders fixture V2 data without importing V1 static helpers.

### Phase 2: hero port and visual primitives

Deliver:

- dotted glow port;
- dotted globe port with vendored Natural Earth asset;
- verdict decode and sweep;
- adjustable CRT overlay;
- open signal frame surface system;
- removal of corner brackets.

Done when reduced motion, teardown, resize, and off-screen pause behavior are implemented.

### Phase 3: bot feed

Deliver:

- normalized bot feed export contract;
- metadata scraper output;
- deduplication and matched-HN ID;
- rich bot cards;
- all bot-card states;
- responsive feed layout.

Done when all three bot identities render and duplicate canonical URLs collapse correctly.

### Phase 4: HN evidence cards

Deliver:

- story mapping adapter;
- card summary;
- source tension axis;
- all three dimension rows;
- quotes and dissent;
- exact exported community excerpts where available, otherwise explicitly labeled summaries;
- progressive diagnostics;
- loading, partial, and unavailable states.

Done when every exported V2 diagnostic is either displayed or explicitly documented as intentionally hidden.

### Phase 5: settings and history

Deliver:

- lil-gui integration;
- persisted settings store;
- filters, score thresholds, density, and CRT controls;
- LayerCake/D3 multidimensional history;
- accessible chart summary.

Done when reload restores state and all controls work by keyboard.

### Phase 6: automation status and production publication

Deliver:

- orchestration-level cron run record;
- public pipeline status export;
- next-run calculation;
- coverage snapshots;
- atomic generation publication and rollback;
- public status strip.

Done when a failed scheduled run leaves the prior good dataset visible and reports failure without leaking admin details.

### Phase 7: QA and rollout

Deliver:

- desktop, tablet, and mobile visual QA;
- keyboard and screen-reader pass;
- reduced-motion pass;
- malformed and partial data fixtures;
- performance measurement;
- V2 metadata and OG image;
- rollout decision for `/v2` versus root.

## 25. What not to build

- No shader framework for the hero. The reference effect is canvas and already sufficient.
- No Three.js globe. The existing orthographic canvas globe is lighter and correct.
- No new generic design system. Keep Svelte, Tailwind v4, and existing shadcn-svelte primitives.
- No table view as the default HN display.
- No card-level manual rerun controls.
- No public admin logs.
- No sentiment score for bot links unless they have an actual analyzed source contract.
- No single `controversy` number that merges disagreement and polarization.
- No confidence penalty for disagreement.
- No raw comment count multiplier in sentiment or global influence.
- No URL-synchronized settings in the first release.
- No virtualization until measured card volume requires it.
- No silent V1 fallback inside `/v2`.
- No corner brackets.

## 26. Open decisions with defaults

### 26.1 Bot platform adapter

**Open:** the repository does not establish whether the three bots are read from Telegram, X, RSS, or another source.  
**Default:** define the normalized `bot-feed.json` contract now and implement the first source adapter separately. Frontend work must not depend on the platform.

### 26.2 Cron schedule

**Open:** exact expression and timezone are deployment decisions.  
**Default:** every six hours in UTC, with a 60-minute grace period. Export both the expression and a human label.

### 26.3 Aggregate window

**Open:** the current V2 exporter uses 12 months while the partial UI says rolling six months.  
**Default:** 12 months for the hero verdict, 7 days for the bot feed, and user-selectable history windows.

### 26.4 Source identity colors

**Open:** final OKLCH values need contrast calibration.  
**Default:** cyan for article, violet for community, phosphor lime for combined. Direction colors remain lime, amber, and red.

### 26.5 V2 rollout route

**Open:** whether V2 replaces `/` or remains `/v2` at launch.  
**Default:** complete and stabilize `/v2`, then switch root only after data automation and metadata are production-ready. Preserve redirects and canonical URLs deliberately.

## 27. Final acceptance checklist

### Structure

- [ ] Hero is followed by pipeline status, bot feed, then HN evidence.
- [ ] Bot feed is visually primary.
- [ ] HN stories use cards, not rows or a table.
- [ ] History and methodology follow current evidence.

### Scoring

- [ ] Capability, trajectory, and impact are visible.
- [ ] Article, community, and combined sources remain distinct.
- [ ] 40/60 confidence-aware combination is represented correctly.
- [ ] `0` and `not_addressed` are different states.
- [ ] Source conflict remains visible after combination.
- [ ] Disagreement, polarization, ranking sensitivity, and ESS are available.
- [ ] Confidence never changes direction styling.
- [ ] Visibility-weighted community score is primary.
- [ ] Diversity-balanced score is labeled diagnostic.

### Visual system

- [ ] Corner brackets are gone.
- [ ] Open signal frames and semantic rails replace boxy panel chrome.
- [ ] V2 colors originate in OKLCH tokens.
- [ ] Typography remains readable at high density.
- [ ] Mobile uses one column and no horizontal scrolling.

### Hero and motion

- [ ] Dotted glow is ported from the reference.
- [ ] Dotted globe is ported from the reference.
- [ ] Verdict decode and one-shot beam are ported.
- [ ] No shader or Three.js dependency is introduced.
- [ ] Canvas work pauses off-screen and tears down correctly.
- [ ] Reduced motion produces a complete static experience.

### Settings

- [ ] `lil-gui` is dynamically loaded client-side.
- [ ] Dimension, window, threshold, density, and CRT controls exist.
- [ ] Settings persist under a versioned localStorage key.
- [ ] Invalid saved state is clamped or discarded.
- [ ] Overlay keyboard and focus behavior works.

### Data and automation

- [ ] V2 route no longer reads V1 static helpers.
- [ ] V2 broad prefilter is executable, persisted, and isolated from V1.
- [ ] Bot and HN exports have explicit versioned contracts.
- [ ] Global story influence has an immutable version identifier.
- [ ] Community summaries are never presented as exact quotes.
- [ ] Public pipeline status is real telemetry, not inferred counts.
- [ ] Last run, processed count, next run, and coverage are visible.
- [ ] Static publication is atomic and rollback-safe.
- [ ] Failed runs preserve the last known good public generation.
- [ ] Public data exposes no admin internals.

### Scope and accessibility

- [ ] All ten V2 scopes are supported.
- [ ] Coding is not selected as the implicit default.
- [ ] Every color-coded value has text and sign.
- [ ] Cards and disclosures are keyboard operable.
- [ ] Chart has a non-visual summary.
- [ ] Empty, loading, stale, partial, and error states are designed.
