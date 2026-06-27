/**
 * Read full scraped article text from the pipeline's articles-text store.
 *
 * The Python pipeline writes articles as plain-text files at:
 *   pipeline/data/articles-text/<hn_id>.txt
 *
 * Format:
 *   Title: <title>
 *   URL: <url>
 *
 *   <article body>
 *
 * This module mirrors the parsing logic from pipeline/src/store/text_store.py
 * but reads directly from Node — no Python side-car spawn needed.
 */

import { existsSync, readFileSync, statSync } from "node:fs"
import path from "node:path"
import { getPipelineStoragePaths } from "$lib/server/pipeline-storage"

export type ArticleText = {
  hn_id: number
  title: string | null
  url: string | null
  text: string
  wordCount: number
}

/**
 * Resolve the articles-text directory from pipeline storage paths.
 */
function getArticlesTextDir(): string {
  const { dataDir } = getPipelineStoragePaths()
  return path.join(dataDir, "articles-text")
}

/**
 * Read full article text for a given HN ID.
 *
 * Returns null if the text file doesn't exist (article not scraped yet).
 * Returns the parsed article (title, url, body text) on success.
 */
export function getArticleText(hnId: number): ArticleText | null {
  const filePath = path.join(getArticlesTextDir(), `${hnId}.txt`)

  if (!existsSync(filePath)) {
    return null
  }

  try {
    const raw = readFileSync(filePath, "utf8")

    // Normalize CRLF → LF so the header/body split works regardless
    // of whether the file was written on Windows or Linux
    const content = raw.replace(/\r\n/g, "\n")

    // Split header block from body on the first blank line
    const blankIdx = content.indexOf("\n\n")
    const headerBlock = blankIdx >= 0 ? content.slice(0, blankIdx) : content
    const bodyText = blankIdx >= 0 ? content.slice(blankIdx + 2).trim() : ""

    // Parse "Key: Value" lines from the header
    const metadata: Record<string, string> = {}
    for (const line of headerBlock.split("\n")) {
      const idx = line.indexOf(": ")
      if (idx > 0) {
        const key = line.slice(0, idx).toLowerCase().trim()
        const val = line.slice(idx + 2).trim()
        metadata[key] = val
      }
    }

    const wordCount = bodyText ? bodyText.split(/\s+/).filter(Boolean).length : 0

    return {
      hn_id: hnId,
      title: metadata.title ?? null,
      url: metadata.url ?? null,
      text: bodyText,
      wordCount,
    }
  } catch {
    return null
  }
}

/**
 * Check whether a text file exists for the given HN ID.
 * Cheaper than getArticleText when you only need existence.
 */
export function hasArticleText(hnId: number): boolean {
  const filePath = path.join(getArticlesTextDir(), `${hnId}.txt`)
  return existsSync(filePath)
}

/**
 * Get the file size in bytes for an article's text file.
 * Returns 0 if the file doesn't exist.
 */
export function getArticleTextSize(hnId: number): number {
  const filePath = path.join(getArticlesTextDir(), `${hnId}.txt`)
  try {
    return statSync(filePath).size
  } catch {
    return 0
  }
}
