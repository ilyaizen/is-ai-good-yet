import { error } from "@sveltejs/kit"
import type { PageServerLoad } from "./$types"
import { getStaticArticleById } from "$lib/static-data"

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

  // Try to get article from static data
  const article = getStaticArticleById(hnId)

  if (!article) {
    throw error(404, "Article not found")
  }

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
      // Static mode: no full article text available
      text: null,
      text_missing: true,
    },
    prompts: null,
  }
}
