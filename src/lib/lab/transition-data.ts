import { getStaticTopArticles } from "$lib/static-data"
import type { InfluentialArticle } from "$lib/server/db"

export type LabTransitionTone = "positive" | "negative" | "neutral"

export interface LabTransitionCard {
  id: string
  href: string
  poster: string
  title: string
  summary: string
  topic: string
  utility: string
  trajectory: string
  tone: LabTransitionTone
  accent: string
  score: number
  hnScore: number
  hnComments: number
  article: InfluentialArticle
}

const LAB_LIMIT = 8

const TONE_PALETTE: Record<LabTransitionTone, { accent: string; glow: string; backdrop: string }> = {
  positive: { accent: "#55d6a3", glow: "#0c7a63", backdrop: "#071b16" },
  negative: { accent: "#ff6b6b", glow: "#8f1f37", backdrop: "#240d14" },
  neutral: { accent: "#7dd3fc", glow: "#155e75", backdrop: "#091724" },
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function escapeXml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;")
}

function wrapText(value: string, maxChars: number, maxLines: number) {
  const words = value.trim().split(/\s+/).filter(Boolean)
  const lines: string[] = []
  let current = ""

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word
    if (candidate.length > maxChars && current) {
      lines.push(current)
      current = word
    } else {
      current = candidate
    }

    if (lines.length === maxLines - 1) {
      break
    }
  }

  if (current) lines.push(current)

  const remainder = words.join(" ")
  if (lines.length > maxLines) {
    return lines.slice(0, maxLines)
  }

  if (lines.length === maxLines && remainder.length > lines.join(" ").length) {
    lines[maxLines - 1] = `${lines[maxLines - 1].slice(0, Math.max(0, maxChars - 1))}…`
  }

  return lines.length > 0 ? lines : [value.slice(0, maxChars)]
}

function scoreTone(score: number): LabTransitionTone {
  if (score > 0.15) return "positive"
  if (score < -0.15) return "negative"
  return "neutral"
}

function hexToRgb(hex: string) {
  const normalized = hex.replace("#", "")
  const pairs = normalized.length === 3 ? normalized.split("").map((part) => part + part) : normalized.match(/.{2}/g) ?? ["00", "00", "00"]
  return pairs.map((part) => Number.parseInt(part, 16)) as [number, number, number]
}

function rgbToHex(rgb: [number, number, number]) {
  return `#${rgb
    .map((channel) => clamp(Math.round(channel), 0, 255).toString(16).padStart(2, "0"))
    .join("")}`
}

function mixHex(a: string, b: string, amount: number) {
  const [ar, ag, ab] = hexToRgb(a)
  const [br, bg, bb] = hexToRgb(b)
  return rgbToHex([
    ar + (br - ar) * amount,
    ag + (bg - ag) * amount,
    ab + (bb - ab) * amount,
  ])
}

function paletteForArticle(article: InfluentialArticle) {
  const tone = scoreTone(article.sentiment_score)
  const base = TONE_PALETTE[tone]
  const intensity = clamp(Math.abs(article.sentiment_score) / 0.8, 0, 1)
  const glow = mixHex(base.glow, base.accent, 0.45 + intensity * 0.35)
  const accent = mixHex(base.accent, "#ffffff", 0.12 * intensity)
  const highlight = mixHex(base.accent, "#d4d4d8", 0.22)
  return { tone, accent, glow, highlight, backdrop: base.backdrop }
}

function utilityForTone(tone: LabTransitionTone) {
  if (tone === "positive") return "tool"
  if (tone === "negative") return "hazard"
  return "mixed"
}

function trajectoryForTone(tone: LabTransitionTone) {
  if (tone === "positive") return "optimistic"
  if (tone === "negative") return "pessimistic"
  return "uncertain"
}

function buildPoster(article: InfluentialArticle) {
  const palette = paletteForArticle(article)
  const titleLines = wrapText(article.hn_title, 24, 4)
  const summaryLines = wrapText(article.summary, 34, 4)
  const scoreBadge = article.sentiment_score >= 0 ? "+" : ""
  const scoreLabel = `${scoreBadge}${article.sentiment_score.toFixed(2)}`
  const dateLabel = new Date(article.hn_timestamp * 1000).toISOString().split("T")[0]
  const topicLabel = article.topic ?? "uncategorized"
  const utilityLabel = utilityForTone(palette.tone)
  const trajectoryLabel = trajectoryForTone(palette.tone)

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 1280" role="img" aria-label="${escapeXml(article.hn_title)}">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${palette.glow}" />
          <stop offset="55%" stop-color="${palette.backdrop}" />
          <stop offset="100%" stop-color="#05070b" />
        </linearGradient>
        <linearGradient id="glow" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="${palette.accent}" stop-opacity="0.2" />
          <stop offset="100%" stop-color="${palette.highlight}" stop-opacity="0.02" />
        </linearGradient>
        <filter id="blur"><feGaussianBlur stdDeviation="24" /></filter>
      </defs>

      <rect width="960" height="1280" fill="url(#bg)" />
      <circle cx="180" cy="190" r="240" fill="${palette.accent}" fill-opacity="0.18" filter="url(#blur)" />
      <circle cx="820" cy="980" r="280" fill="${palette.glow}" fill-opacity="0.18" filter="url(#blur)" />
      <path d="M-50 180 C 180 40, 410 280, 640 140 S 1090 200, 1040 420" fill="none" stroke="${palette.accent}" stroke-opacity="0.34" stroke-width="3" />
      <path d="M-90 1120 C 180 960, 390 1260, 690 1070 S 1080 1000, 1040 1230" fill="none" stroke="${palette.glow}" stroke-opacity="0.3" stroke-width="2" />

      <text x="72" y="110" fill="${palette.accent}" font-family="Inter, Arial, sans-serif" font-size="26" letter-spacing="0.32em">LAB / THREEJS</text>
      <text x="72" y="156" fill="#f8fafc" font-family="Inter, Arial, sans-serif" font-size="18" letter-spacing="0.16em" opacity="0.72">PAGE TRANSITION PORT</text>

      <rect x="72" y="214" width="160" height="50" rx="25" fill="${palette.accent}" fill-opacity="0.16" stroke="${palette.accent}" stroke-opacity="0.35" />
      <text x="152" y="247" text-anchor="middle" fill="#f8fafc" font-family="IBM Plex Mono, monospace" font-size="19">HN ${article.hn_id}</text>

      <rect x="72" y="316" width="316" height="44" rx="22" fill="#ffffff" fill-opacity="0.06" stroke="#ffffff" stroke-opacity="0.08" />
      <text x="92" y="345" fill="#e2e8f0" font-family="IBM Plex Mono, monospace" font-size="18">${escapeXml(topicLabel)}</text>

      ${titleLines
        .map((line, index) => {
          const y = 452 + index * 72
          return `<text x="72" y="${y}" fill="#f8fafc" font-family="Inter, Arial, sans-serif" font-size="${index === 0 ? 64 : 58}" font-weight="700" letter-spacing="-0.04em">${escapeXml(line)}</text>`
        })
        .join("")}

      <text x="72" y="760" fill="#cbd5e1" font-family="Inter, Arial, sans-serif" font-size="26" letter-spacing="0.08em">${escapeXml(scoreLabel)} · ${article.hn_score} points · ${article.hn_comments} comments</text>

      ${summaryLines
        .map((line, index) => {
          const y = 830 + index * 42
          return `<text x="72" y="${y}" fill="#dbe4ef" font-family="Inter, Arial, sans-serif" font-size="28" opacity="0.82">${escapeXml(line)}</text>`
        })
        .join("")}

      <text x="72" y="1168" fill="#94a3b8" font-family="IBM Plex Mono, monospace" font-size="18" letter-spacing="0.16em">${escapeXml(dateLabel)} · ${escapeXml(utilityLabel.toUpperCase())} · ${escapeXml(trajectoryLabel.toUpperCase())}</text>
    </svg>
  `.replaceAll(/\s{2,}/g, " ")

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

export function buildLabTransitionCards(limit = LAB_LIMIT): LabTransitionCard[] {
  return getStaticTopArticles(limit).map((article) => {
    const tone = scoreTone(article.sentiment_score)
    const palette = paletteForArticle(article)

    return {
      id: String(article.hn_id),
      href: `/lab/threejs-page-transition/${article.hn_id}`,
      poster: buildPoster(article),
      title: article.hn_title,
      summary: article.summary,
      topic: article.topic ?? "uncategorized",
      utility: utilityForTone(tone),
      trajectory: trajectoryForTone(tone),
      tone,
      accent: palette.accent,
      score: article.sentiment_score,
      hnScore: article.hn_score,
      hnComments: article.hn_comments,
      article,
    }
  })
}

export function findLabTransitionCard(cards: LabTransitionCard[], id: string) {
  return cards.find((card) => card.id === id)
}

export function nextLabTransitionCard(cards: LabTransitionCard[], id: string) {
  if (cards.length === 0) return null
  const index = cards.findIndex((card) => card.id === id)
  if (index === -1) return cards[0] ?? null
  return cards[(index + 1) % cards.length] ?? null
}
