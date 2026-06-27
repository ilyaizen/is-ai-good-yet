import { error } from "@sveltejs/kit"
import type { PageServerLoad } from "./$types"
import { getStaticArticleById } from "$lib/static-data"
import { getUrlWithAnalysis } from "$lib/server/db"
import { getArticleText } from "$lib/server/article-text"

export interface AnalysisPromptsSuccess {
  prefilter: {
    model: string
    prompt: string
    truncation_limit: number
    actual_length: number
  }
  classifier: {
    model: string
    system_prompt: string
    user_prompt: string
    truncation_limit: number
    actual_length: number
  }
  text_missing?: boolean
}

export interface AnalysisPromptsError {
  error: string
}

export type AnalysisPrompts = AnalysisPromptsSuccess | AnalysisPromptsError

export interface ContentFilterResult {
  category: string
  confidence: number
  reasoning: string
}

export const load: PageServerLoad = async ({
  params,
}): Promise<{
  article: {
    title: string
    url: string
    sentiment_score: number
    analysis: {
      utility: string
      trajectory: string
      topic: string
      summary: string
      quotes: string[]
    }
    hn_author: string | null
    hn_timestamp: number
    hn_score: number
    hn_comments: number
    hn_id: number
    content_category: string
    opinion: string | null
    is_opinion: boolean | null
    content_filter_json: ContentFilterResult | null
    text: string | null
    text_missing: boolean
  }
  prompts: AnalysisPrompts | null
  error?: string
}> => {
  const hnId = parseInt(params.id, 10)
  if (isNaN(hnId)) {
    throw error(400, "Invalid HN ID")
  }

  // Try live DB article first (covers all 24k URLs in the pipeline)
  const dbArticle = getUrlWithAnalysis(hnId)
  if (dbArticle) {
    const articleText = getArticleText(hnId)

    // Parse content_filter_json if present
    let contentFilter: ContentFilterResult | null = null
    if (dbArticle.content_filter_json) {
      try {
        contentFilter = JSON.parse(dbArticle.content_filter_json) as ContentFilterResult
      } catch {
        contentFilter = null
      }
    }

    return {
      article: {
        title: dbArticle.hn_title || "Untitled Article",
        url: dbArticle.url,
        sentiment_score: dbArticle.sentiment_score ?? 0,
        analysis: dbArticle.analysis ?? {
          utility: "unknown",
          trajectory: "uncertain",
          topic: "",
          summary: "",
          quotes: [],
        },
        hn_author: dbArticle.hn_author ?? null,
        hn_timestamp: dbArticle.hn_timestamp ?? 0,
        hn_score: dbArticle.hn_score ?? 0,
        hn_comments: dbArticle.hn_comments ?? 0,
        hn_id: hnId,
        content_category: dbArticle.content_category ?? "",
        opinion: dbArticle.opinion ?? null,
        is_opinion: dbArticle.is_opinion,
        content_filter_json: contentFilter,
        text: articleText?.text ?? null,
        text_missing: !articleText,
      },
      prompts: null,
    }
  }

  // Fall back to static data (pre-exported articles)
  const article = getStaticArticleById(hnId)

  if (!article) {
    throw error(404, "Article not found")
  }

  // Even for static articles, try the scraped text store
  const articleText = getArticleText(hnId)

  return {
    article: {
      title: article.hn_title,
      url: article.url,
      sentiment_score: article.sentiment_score,
      analysis: article.analysis,
      hn_author: null,
      hn_timestamp: article.hn_timestamp,
      hn_score: article.hn_score,
      hn_comments: article.hn_comments,
      hn_id: article.hn_id,
      content_category: article.content_category,
      opinion: null,
      is_opinion: null,
      content_filter_json: null,
      text: articleText?.text ?? null,
      text_missing: !articleText,
    },
    prompts: null,
  }
}
