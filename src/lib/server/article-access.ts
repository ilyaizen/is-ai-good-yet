/**
 * Single shared loader for full scraped article bodies.
 *
 * SECURITY: the scraped articles-text store contains full bodies of
 * third-party (copyrighted) articles. Full bodies may only leave the server
 * to an authorized admin caller. Every surface that serves article text
 * (details page + article-details API) MUST load it through this module so
 * the access policy lives in exactly one place.
 */

import { getArticleText, type ArticleText } from "$lib/server/article-text"

export type ArticleBodyReader = (hnId: number) => ArticleText | null

/**
 * Load the full article body ONLY when the caller is authorized.
 *
 * Unauthenticated / unauthorized callers always receive null — no file system
 * access is even attempted. Authorized callers receive the parsed body, or
 * null if the article has not been scraped yet.
 */
export function getAuthorizedArticleText(
	hnId: number,
	isAuthorized: boolean,
	readArticleBody: ArticleBodyReader = getArticleText
): ArticleText | null {
	if (!isAuthorized) return null
	return readArticleBody(hnId)
}
