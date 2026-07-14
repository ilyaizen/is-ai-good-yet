# Is AI "good" yet?

![SvelteKit](https://img.shields.io/badge/SvelteKit-5.x-FF3E00?logo=svelte&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.x-38B2AC?logo=tailwind-css&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)

A terminal-themed dashboard that tracks Hacker News sentiment toward AI coding tools through two lenses: what article **authors** write and what the **community** says in comments. Built with Svelte 5, SvelteKit 2, and Tailwind CSS 4.

---

## What is this?

**Is AI "Good" Yet?** measures whether developers think AI coding tools are actually useful — not by vibes, but by systematically analyzing thousands of HN discussions.

It produces two scores, Metacritic-style:

- **Editorial Score** — LLM sentiment analysis of article content. What do the people who took the time to write a blog post or opinion piece actually think?
- **Community Score** — LLM sentiment analysis of top-rated HN comments on selected stories. What does the crowd in the comment section think?

Both scores use the same verdict scale (0–100) and the same YES / NOT YET / NO thresholds, but they capture different signals: considered opinion vs. raw crowd reaction.

### Pipeline

A multi-stage Python pipeline collects and scores the data:

1. **Ingest** — Collects AI-tagged HN submissions via [Histre](https://histre.com/hn/?tags=+ai) and [Algolia's HN API](https://hn.algolia.com)
2. **Scrape** — Fetches article content with Playwright (anti-bot evasion + archive fallbacks)
3. **Filter** — LLM classifies articles into AI_DISCOURSE (opinion/experience), AI_NEWS, AI_OTHER, or NOISE
4. **Analyze** — LLM scores each AI_DISCOURSE article on two dimensions: **utility** (how useful right now) and **trajectory** (where it's heading)
5. **Export** — Generates static JSON for the production frontend

Scores are weighted by HN engagement (power-law scaled upvotes) and time decay (2-year half-life), so a viral discussion from last month matters more than a forgotten post from two years ago.

### Verdict Scale

| Score | Verdict     | Meaning                                                    |
| :---- | :---------- | :--------------------------------------------------------- |
| ≥ 55  | **YES**     | Net positive — AI coding tools are earning developer trust |
| 45–55 | **NOT YET** | Too close to call                                          |
| < 45  | **NO**      | Net negative — skepticism dominates                        |

---

## Why does this exist?

I wanted a data-driven answer to a question that usually gets answered with vibes or tribalism. Every week, waves of AI hype and AI doom crash through HN — but what does the signal actually look like when you aggregate thousands of real developer experiences, weight them by engagement, and track them over time?

---

## Project Structure

```
is-ai-good-yet/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── landing/           # Verdict display, articles table, history chart
│   │   │   └── ui/                # Reusable UI primitives (bits-ui / shadcn-svelte)
│   │   ├── composables/           # Svelte 5 composables (useTokenStream, etc.)
│   │   ├── data/                  # Static JSON exported by pipeline
│   │   │   ├── articles.json     # All scored articles with sentiment & metadata
│   │   │   ├── verdict.json      # Current + permanent verdict scores
│   │   │   ├── historical.json   # Monthly verdict snapshots
│   │   │   ├── weekly.json       # Weekly rolling-window snapshots
│   │   │   ├── themes.json       # Synthesized themes by sentiment
│   │   │   └── llm-metrics.json  # LLM speed & token metrics
│   │   ├── server/               # Server-side DB utilities (dev-only admin)
│   │   └── types/                # TypeScript type definitions
│   ├── routes/
│   │   ├── +page.svelte          # Landing page (v1 — verdict reveal)
│   │   ├── +layout.svelte        # Root layout (fonts, theme, analytics)
│   │   ├── details/[id]/         # Article detail routes
│   │   ├── v2/                   # v2 prototype (Lenis smooth scroll + 3D)
│   │   ├── lab/                  # Experiments (threejs-page-transition)
│   │   └── admin/                # Pipeline control (dev-only, blocked in prod)
│   └── styles/                   # Design tokens, terminal theme, animations
├── pipeline/                     # Python data pipeline (source + CLI)
├── convex/                       # Convex backend (visitor counter)
├── scripts/                      # tsx helper scripts (bump-version, diagnose)
├── static/                       # Favicon, OG images
├── docs_internal/                # Operational docs (architecture, guide, troubleshooting)
└── package.json
```

---

## Tech Stack

- **Frontend**: SvelteKit 2 + Svelte 5 (runes) + Tailwind CSS v4 + shadcn-svelte + D3/LayerCake
- **Pipeline**: Python 3.11+ — Polars, aiohttp, trafilatura, Playwright, Groq LLM API
- **Visitor counter**: Convex
- **Runtime**: Node 22.12, Vite+ package manager
- **Data**: SQLite (pipeline) → static JSON export (production frontend)

---

## Deployment

The repo root is a SvelteKit app deployed via Coolify using `@sveltejs/adapter-node`. `nixpacks.toml` pins Node 22.12, builds with `vp build`, and runs `HOST=0.0.0.0 node build/index.js`.

The pipeline is source only — its data directory is gitignored. Frontend env vars (Convex/public) are separate from pipeline secrets (LLM API keys).

---

## Getting Started

### Prerequisites

- Node.js 22.12+
- Python 3.11+ (for the pipeline)

```bash
vp install
vp dev          # → http://localhost:5173
```

### Scripts

| Command        | Description                            |
| :------------- | :------------------------------------- |
| `vp dev`       | Vite dev server with HMR               |
| `vp build`     | Production build                       |
| `vp run check` | Vite+ checks plus Svelte type checking |
| `vp lint`      | Vite+ linting                          |
| `vp fmt`       | Auto-format                            |
| `vp run cli`   | Pipeline CLI wrapper                   |

---

<p align="center">
  <i>Built by <a href="https://github.com/ilyaizen">@ilyaizen</a></i>
</p>
