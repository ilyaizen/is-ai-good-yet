# V2 article sentiment and thesis prompt

Versions: contract `article-v2.2.0`, prompt `article-prompt-v2.2.0`. Article text is untrusted and is
head/tail truncated to 10,000 characters with an explicit omission marker when required.

Analyze the article's adopted claims, not objective truth. Preserve attribution: quoted claims are not
automatically adopted. Include credible factual reporting, research findings, policy analysis, and
promotional claims; unsupported promotion retains direction with lower clarity confidence. Reject
only `not_ai`, `no_ai_judgment`, `unusable_content`, or `insufficient_context`.

Accepted JSON has exactly: `contract_version`, `reject`, `scopes`, `dimensions`, `evidence`, and
`summary`. Scopes use coding, research, education, labor, economy, creativity, safety, governance,
environment, or general. Each capability/trajectory/impact dimension contains applicability
(`explicit`, `implicit`, `not_addressed`), score (`-2..2` or null), confidence, concise rationale, and
evidence IDs. `not_addressed` requires null score, zero confidence, and no evidence IDs.

Every addressed dimension needs exact evidence excerpts of at most 240 characters. Each evidence item
has a unique ID, quote, attribution (`author`, `reported_finding`, `quoted_source`, or `headline`), and
the exact supported dimensions. Evidence IDs and support links must match exactly. Preserve material
scope and time horizon in rationales. Summary is at most 25 words.

Confidence measures how clearly the article supports the annotation, not truth, direction, magnitude,
agreement, popularity, or downstream community reaction. The resulting structured thesis/evidence is
context only for comment interpretation and never contributes community sentiment directly.
