# Is AI "good" yet?

![SvelteKit](https://img.shields.io/badge/SvelteKit-5.x-FF3E00?logo=svelte&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.x-38B2AC?logo=tailwind-css&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)

A **premium, terminal-themed dashboard** that visualizes Hacker News sentiment toward AI coding tools. Built with **Svelte 5**, **SvelteKit 2**, and **Tailwind CSS 4**, featuring rich animations, dynamic theming, and a unique "verdict reveal" experience.

---

## 🤔 What is this?

**Is AI “good” yet?** tracks Hacker News to see what developers *actually* think about AI coding tools.

It runs a multi-stage Python pipeline that:
1. Collects AI-tagged submissions via [Histre](https://histre.com/hn/?tags=+ai)
2. Resolves them using [Algolia's HN API](https://hn.algolia.com)
3. Scrapes all possible article links
4. Uses an LLM to filter out noise, then performs sentiment analysis
5. Ranks articles based on **utility** and **trajectory** scores, weighted by engagement and recency

The frontend you're looking at is the pretty face that makes all that data digestible.

---

## 💡 Why does this exist?

> *"I kept seeing waves of AI-hate that just didn't match my experience, and as I don't jive with vibes or tribes, I built this to find out if HN's hivemind shares similar sentiments."*

---

## 📁 Project Structure

```
is-ai-good-yet/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── landing/           # Landing page components
│   │   │   │   ├── verdict-veil.svelte      # Initial "question" overlay
│   │   │   │   ├── verdict-display.svelte   # Main answer reveal
│   │   │   │   ├── details-section.svelte   # Themes, methodology, stats
│   │   │   │   ├── articles-table.svelte    # Sortable article explorer
│   │   │   │   ├── history-chart.svelte     # Sentiment over time
│   │   │   │   └── ...
│   │   │   ├── ui/                # Reusable UI primitives (bits-ui based)
│   │   │   ├── app-header.svelte  # Global header with nav
│   │   │   ├── app-footer.svelte  # Global footer with links
│   │   │   └── ...
│   │   ├── composables/           # Svelte 5 composables (e.g., useTokenStream)
│   │   ├── data/                  # Static JSON data (from pipeline export)
│   │   │   ├── articles.json
│   │   │   ├── themes.json
│   │   │   └── verdict.json
│   │   ├── server/                # Server-side utilities
│   │   └── types/                 # TypeScript type definitions
│   ├── routes/
│   │   ├── +page.svelte           # Landing page
│   │   ├── +layout.svelte         # Root layout (fonts, analytics)
│   │   └── details/               # Article detail routes
│   └── styles/                    # Global CSS & design tokens
├── static/                        # Static assets (favicon, OG images)
├── convex/                        # Convex backend (visitor counter)
└── package.json
```

---

## 🚀 Getting Started

### Prerequisites

- **Bun** v1.3+ (or npm/pnpm)
- Node.js 20+ (for SvelteKit)

### Installation

```bash
# Clone the repo (if standalone)
cd is-ai-good-yet

# Install dependencies
bun install

# Start development server
bun run dev
```

The app will be available at **http://localhost:5173** (or port 3050 if configured).

### Available Scripts

| Command           | Description                       |
| ----------------- | --------------------------------- |
| `bun run dev`     | Start Vite dev server with HMR    |
| `bun run build`   | Production build                  |
| `bun run preview` | Preview production build locally  |
| `bun run check`   | TypeScript + Svelte type checking |
| `bun run lint`    | Run Prettier + ESLint             |
| `bun run format`  | Auto-format with Prettier         |

---

<p align="center">
  <i>Built with ☕ and curiosity — <a href="https://github.com/ilyaizen">@ilyaizen</a></i>
</p>
