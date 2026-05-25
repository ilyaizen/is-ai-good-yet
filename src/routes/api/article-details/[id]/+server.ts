import { json, error } from "@sveltejs/kit"
import type { RequestHandler } from "./$types"
import { getStaticArticleById } from "$lib/static-data"
import { getUrlWithAnalysis } from "$lib/server/db"
import type { ArticleDetails, ArticleDetailsResponse } from "$lib/types/article-details"

export const GET: RequestHandler = async ({ params }) => {
  const hnId = parseInt(params.id, 10)
  if (isNaN(hnId)) {
    throw error(400, "Invalid HN ID")
  }

  const dbArticle = getUrlWithAnalysis(hnId)
  if (dbArticle) {
    const response: { article: ArticleDetails } = {
      article: {
        id: Number(dbArticle.id ?? hnId),
        hn_id: Number(dbArticle.hn_id ?? hnId),
        title: dbArticle.hn_title || "Untitled Article",
        url: dbArticle.url,
        text: "",
        sentiment_score: dbArticle.sentiment_score,
        analysis: dbArticle.analysis,
        hn_author: dbArticle.hn_author ?? null,
        hn_timestamp: dbArticle.hn_timestamp ?? null,
        hn_score: dbArticle.hn_score ?? null,
        hn_comments: dbArticle.hn_comments ?? null,
        content_category: dbArticle.content_category ?? null,
      },
    }

    return json(response)
  }

  const staticArticle = getStaticArticleById(hnId)
  if (staticArticle) {
    const response: { article: ArticleDetails } = {
      article: {
        id: staticArticle.hn_id,
        hn_id: staticArticle.hn_id,
        title: staticArticle.hn_title,
        url: staticArticle.url,
        text: staticArticle.excerpt || "",
        sentiment_score: staticArticle.sentiment_score,
        analysis: staticArticle.analysis,
        hn_author: staticArticle.hn_author || null,
        hn_timestamp: staticArticle.hn_timestamp,
        hn_score: staticArticle.hn_score,
        hn_comments: staticArticle.hn_comments,
        content_category: staticArticle.content_category,
      },
    }

    return json(response)
  }

  throw error(404, "Article not found")
}
