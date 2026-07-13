export type PipelineCommandName =
  | "catch_up"
  | "backfill"
  | "resolve"
  | "scrape"
  | "clean_articles"
  | "prefilter_content"
  | "sentiment_analyzer"
  | "v2_prefilter"
  | "v2_comments"
  | "v2_analyze"
  | "v2_run"
  | "export"
  | "v2_export"

export interface PipelineCommandSpec {
  name: PipelineCommandName
  label: string
  description: string
  args: string[]
}

export interface PipelinePreflightCheck {
  ok: boolean
  reason: string
}

export interface PipelinePreflightSnapshot {
  python: PipelinePreflightCheck
  storage: PipelinePreflightCheck
  scraper: PipelinePreflightCheck
  groq: PipelinePreflightCheck
  residential: PipelinePreflightCheck
}

export interface PipelineCommandReadiness {
  ready: boolean
  reasons: string[]
}

const COMMANDS: Record<PipelineCommandName, PipelineCommandSpec> = {
  catch_up: {
    name: "catch_up",
    label: "Catch-up v1",
    description: "Run shared ingestion and scraping followed by the legacy V1 analysis and export.",
    args: ["-m", "src.catch_up", "-v"],
  },
  backfill: {
    name: "backfill",
    label: "Ingest recent stories",
    description: "Load recent candidate URLs from Histre without running either analysis pipeline.",
    args: ["-m", "src.backfill_histre", "--end", "5"],
  },
  resolve: {
    name: "resolve",
    label: "Resolve HN metadata",
    description: "Resolve shared URLs to Hacker News stories and refresh recent metadata.",
    args: ["-m", "src.hn_resolver", "--update-recent", "-v"],
  },
  scrape: {
    name: "scrape",
    label: "Scrape shared article text",
    description: "Fetch shared article HTML and extract text without touching V1 or V2 analysis fields.",
    args: [
      "-m",
      "src.scraper",
      "-v",
      "--lean",
      "--stealth-mode=seleniumbase",
      "--no-headful-switch",
      "-b",
      "50",
      "-c",
      "2",
    ],
  },
  clean_articles: {
    name: "clean_articles",
    label: "Clean shared articles",
    description: "Normalize shared extracted article text without running analysis.",
    args: ["src/clean_articles.py"],
  },
  prefilter_content: {
    name: "prefilter_content",
    label: "Prefilter v1",
    description: "Run the legacy AI-coding relevance classifier against V1 fields.",
    args: ["-m", "src.prefilter_content", "-v"],
  },
  sentiment_analyzer: {
    name: "sentiment_analyzer",
    label: "Analyze v1 sentiment",
    description: "Run the legacy V1 utility and trajectory analyzer.",
    args: ["-m", "src.sentiment_analyzer", "-v"],
  },
  v2_prefilter: {
    name: "v2_prefilter",
    label: "Prefilter v2",
    description: "Classify broad AI eligibility and scopes using only the isolated V2 contract.",
    args: ["-m", "src.v2_prefilter"],
  },
  v2_comments: {
    name: "v2_comments",
    label: "Collect v2 comments",
    description: "Fetch and deterministically rank Hacker News comment candidates for V2.",
    args: ["-m", "src.hn_comments_v2", "-v"],
  },
  v2_analyze: {
    name: "v2_analyze",
    label: "Analyze v2 sentiment",
    description: "Run versioned V2 article and isolated-comment analysis.",
    args: ["-m", "src.sentiment_v2", "-v"],
  },
  v2_run: {
    name: "v2_run",
    label: "Run isolated v2 pipeline",
    description: "Run V2 prefilter, comments, analysis, and atomic V2 export under one run identity.",
    args: ["-m", "src.v2_orchestrator"],
  },
  export: {
    name: "export",
    label: "Export v1",
    description: "Rebuild only the legacy V1 static JSON exports.",
    args: ["-m", "src.export", "-v"],
  },
  v2_export: {
    name: "v2_export",
    label: "Export v2",
    description: "Publish only the manifest-validated atomic V2 generation.",
    args: ["-m", "src.export_v2"],
  },
}

const COMMAND_REQUIREMENTS: Record<PipelineCommandName, Array<keyof PipelinePreflightSnapshot>> = {
  catch_up: ["python", "storage", "scraper", "groq"],
  backfill: ["python", "storage"],
  resolve: ["python", "storage"],
  scrape: ["python", "storage", "scraper"],
  clean_articles: ["python", "storage"],
  prefilter_content: ["python", "storage", "groq"],
  sentiment_analyzer: ["python", "storage", "groq"],
  v2_prefilter: ["python", "storage", "groq"],
  v2_comments: ["python", "storage"],
  v2_analyze: ["python", "storage", "groq"],
  v2_run: ["python", "storage", "groq"],
  export: ["python", "storage"],
  v2_export: ["python", "storage"],
}

export function getPipelineCommandList(scope: "v1" | "v2" = "v1"): PipelineCommandSpec[] {
  const names: PipelineCommandName[] =
    scope === "v2"
      ? [
          "backfill",
          "resolve",
          "scrape",
          "clean_articles",
          "v2_prefilter",
          "v2_comments",
          "v2_analyze",
          "v2_export",
          "v2_run",
        ]
      : [
          "catch_up",
          "backfill",
          "resolve",
          "scrape",
          "clean_articles",
          "prefilter_content",
          "sentiment_analyzer",
          "export",
        ]
  return names.map((name) => COMMANDS[name])
}

export function getPipelineCommand(name: PipelineCommandName): PipelineCommandSpec {
  return COMMANDS[name]
}

export function evaluateCommandReadiness(
  command: PipelineCommandName,
  snapshot: PipelinePreflightSnapshot
): PipelineCommandReadiness {
  const reasons = COMMAND_REQUIREMENTS[command]
    .map((requirement) => snapshot[requirement])
    .filter((check) => !check.ok)
    .map((check) => check.reason)
  return { ready: reasons.length === 0, reasons }
}
