import type { PageServerLoad } from "./$types"
import { getStaticTopArticles } from "$lib/static-data"

export const load: PageServerLoad = async () => {
  // Convert static articles to summaries format
  const articles = getStaticTopArticles(10000)
  const summaries = articles
    .filter((a) => a.summary && a.summary.length > 0)
    .map((a) => ({
      hn_id: a.hn_id,
      hn_title: a.hn_title,
      sentiment_score: a.sentiment_score,
      topic: a.topic || "",
      summary: a.summary,
    }))

  return { summaries }
}
