import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

export interface V2Methodology {
  versions: {
    analysis: string
    articlePrompt: string
    commentPrompt: string
    selection: string
    aggregation: string
  }
  model: string
  modelParameters: string
  limits: {
    articleCharacters: number
    commentCharacters: number
    contextCharacters: number
    minimumArticleCharacters: number
  }
  selection: {
    minimumStoryScore: number
    minimumCommentCount: number
    authorCap: number
    target: string
    branchCap: string
  }
  aggregation: {
    articleWeight: number
    communityWeight: number
    verdictMonths: number
    dimensions: string[]
    scoreScale: string
  }
  articlePrompt: string
  commentPrompt: string
}

function findPipelineSource(): string {
  const modulePath = fileURLToPath(import.meta.url)
  const candidates = [
    process.env.PIPELINE_SOURCE_DIR?.trim(),
    path.join(process.cwd(), "pipeline", "src"),
    path.resolve(path.dirname(modulePath), "..", "..", "..", "pipeline", "src"),
  ]

  const sourceDir = candidates.find((candidate) => candidate && existsSync(path.join(candidate, "sentiment_v2.py")))
  if (!sourceDir) throw new Error("Could not locate pipeline/src for the v2 methodology.")
  return sourceDir
}

function extractString(source: string, name: string): string {
  const tripleQuoted = source.match(new RegExp(`${name}\\s*=\\s*f?"\""([\\s\\S]*?)"\""`))
  if (tripleQuoted) return tripleQuoted[1]

  const quoted = source.match(new RegExp(`${name}\\s*=\\s*"([^"]*)"`))
  if (quoted) return quoted[1]

  throw new Error(`Could not read ${name} from the v2 pipeline source.`)
}

function extractNumber(source: string, name: string): number {
  const match = source.match(new RegExp(`${name}\\s*=\\s*([0-9_]+(?:\\.[0-9]+)?)`))
  if (!match) throw new Error(`Could not read ${name} from the v2 pipeline source.`)
  return Number(match[1].replaceAll("_", ""))
}

function extractArgumentDefault(source: string, argument: string): number {
  const escapedArgument = argument.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const match = source.match(new RegExp(`add_argument\\("${escapedArgument}"[^)]*default=([0-9_]+)`))
  if (!match) throw new Error(`Could not read the ${argument} default from the v2 pipeline source.`)
  return Number(match[1].replaceAll("_", ""))
}

function renderPrompt(template: string, values: Record<string, string>): string {
  return Object.entries(values).reduce((result, [key, value]) => result.replaceAll(`{${key}}`, value), template)
}

export function getV2Methodology(): V2Methodology {
  const sourceDir = findPipelineSource()
  const sentimentSource = readFileSync(path.join(sourceDir, "sentiment_v2.py"), "utf8")
  const modelSource = readFileSync(path.join(sourceDir, "v2_models.py"), "utf8")
  const commentsSource = readFileSync(path.join(sourceDir, "hn_comments_v2.py"), "utf8")
  const exportSource = readFileSync(path.join(sourceDir, "export_v2.py"), "utf8")

  const articleContractVersion = extractString(modelSource, "ARTICLE_CONTRACT_VERSION")
  const commentContractVersion = extractString(modelSource, "COMMENT_CONTRACT_VERSION")
  const dimensionRubric = extractString(sentimentSource, "DIMENSION_RUBRIC")
  const values = {
    ARTICLE_CONTRACT_VERSION: articleContractVersion,
    COMMENT_CONTRACT_VERSION: commentContractVersion,
    DIMENSION_RUBRIC: dimensionRubric,
  }

  return {
    versions: {
      analysis: extractString(modelSource, "ANALYSIS_VERSION"),
      articlePrompt: extractString(sentimentSource, "ARTICLE_PROMPT_VERSION"),
      commentPrompt: extractString(sentimentSource, "COMMENT_PROMPT_VERSION"),
      selection: extractString(commentsSource, "SELECTION_VERSION"),
      aggregation: extractString(modelSource, "AGGREGATION_VERSION"),
    },
    model: extractString(sentimentSource, "MODEL"),
    modelParameters: sentimentSource.match(/MODEL_PARAMETERS\s*=\s*(\{[^\n]+\})/)?.[1] ?? "Unavailable",
    limits: {
      articleCharacters: extractNumber(sentimentSource, "MAX_ARTICLE_CHARS"),
      commentCharacters: extractNumber(sentimentSource, "MAX_COMMENT_CHARS"),
      contextCharacters: extractNumber(sentimentSource, "MAX_CONTEXT_CHARS"),
      minimumArticleCharacters: extractNumber(sentimentSource, "MIN_ARTICLE_CHARS"),
    },
    selection: {
      minimumStoryScore: extractArgumentDefault(commentsSource, "--min-score"),
      minimumCommentCount: extractArgumentDefault(commentsSource, "--min-comments"),
      authorCap: extractNumber(commentsSource, "AUTHOR_CAP"),
      target: "min(eligible, max(12, min(32, ceil(4 × √eligible))))",
      branchCap: "max(3, ceil(15% × target))",
    },
    aggregation: {
      articleWeight: extractNumber(exportSource, "ARTICLE_WEIGHT"),
      communityWeight: extractNumber(exportSource, "COMMUNITY_WEIGHT"),
      verdictMonths: extractNumber(exportSource, "VERDICT_MONTHS"),
      dimensions: ["capability", "trajectory", "impact"],
      scoreScale: "Source scores −2…+2; displayed score = (clamped score + 2) × 25",
    },
    articlePrompt: renderPrompt(extractString(sentimentSource, "ARTICLE_PROMPT"), values).trim(),
    commentPrompt: renderPrompt(extractString(sentimentSource, "COMMENT_PROMPT"), values).trim(),
  }
}
