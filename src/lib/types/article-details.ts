// Shared types for article details API responses

export interface SentimentAnalysis {
  summary: string
  utility: string
  trajectory: string
  topic: string
  quotes?: string[]
}

export interface ArticleDetails {
  id: number
  hn_id: number
  title: string
  url: string
  text: string
  sentiment_score: number | null
  analysis: SentimentAnalysis | null
  hn_author: string | null
  hn_timestamp: number | null
  hn_score: number | null
  hn_comments: number | null
  content_category: string | null
}

export interface ArticleDetailsResponse {
  article: ArticleDetails | null
  error?: string
}
