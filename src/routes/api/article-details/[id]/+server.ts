import { json, error } from "@sveltejs/kit"
import type { RequestHandler } from "./$types"
import { getStaticArticleById } from "$lib/static-data"
import type { ArticleDetailsResponse } from "$lib/types/article-details"

export const GET: RequestHandler = async ({ params }) => {
  const hnId = parseInt(params.id, 10)
  if (isNaN(hnId)) {
    throw error(400, "Invalid HN ID")
  }

  const article = getStaticArticleById(hnId)
  if (!article) {
    throw error(404, "Article not found")
  }

  const response: ArticleDetailsResponse = {
    article: {
      id: article.hn_id,
      title: article.hn_title,
      url: article.url,
      sentiment_score: article.sentiment_score,
      analysis: article.analysis,
      hn_author: article.hn_author || null,
      hn_timestamp: article.hn_timestamp,
      hn_score: article.hn_score,
      hn_comments: article.hn_comments,
      hn_id: article.hn_id,
      content_category: article.content_category,
      text: article.excerpt || "",
    },
  }

  return json(response)
}
