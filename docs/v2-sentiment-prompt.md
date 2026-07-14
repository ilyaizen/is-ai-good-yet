# V2 sentiment methodology

This is the normative contract for v2.2. V1 prompt, storage, export, data, and route contracts remain
unchanged. V2 measures **visible expressed Hacker News discussion at collection time**. It is not a
probability sample of readers, HN users, or public opinion.

## Immutable versions

| Concern               | Version                        |
| --------------------- | ------------------------------ |
| Analysis              | `v2.2.0`                       |
| Parser                | `v2.2.1`                       |
| Article contract      | `article-v2.2.0`               |
| Article prompt        | `article-prompt-v2.2.1`        |
| Selection             | `ranked-tree-v2.2.0`           |
| Comment contract      | `comment-v2.2.0`               |
| Comment prompt        | `comment-prompt-v2.2.1`        |
| Community aggregation | `community-aggregation-v2.2.0` |

## Dimensions and source combination

Capability is present performance/usefulness, trajectory is expected change from today's baseline,
and impact is net effect on people, institutions, or society. Scores are `-2..2`; `0` is genuine
expressed balance, while `not_addressed` is missing evidence and requires a null score and zero
confidence. The equal-dimension composite is secondary.

Article stance and community stance are independent. Applicable sources combine as
`sum(score × prior × confidence) / sum(prior × confidence)` with article/community priors 0.4/0.6.
Confidence changes influence only; it never changes a source's direction or distance from neutral.

## Article thesis and isolated comment annotation

The article contract contains scopes, a short summary, three dimension results, exact evidence,
attribution, and evidence links. See `v2-article-sentiment-prompt.md`.
Article summaries are capped at 50 words; individual comment summaries are capped at 30 words.

Every considered voting comment receives its own model request. No unrelated selected comment may
appear in that request. Its packet contains:

1. article title, marked `CONTEXT ONLY`;
2. the structured article thesis/evidence, marked `CONTEXT ONLY`, or explicit `unavailable` status;
3. root text for a descendant when distinct from its parent, marked `CONTEXT ONLY`;
4. immediate parent for a reply, marked `CONTEXT ONLY`;
5. one clearly delimited voting comment, the only text annotated.

Context may resolve references, endorsement, rejection, and sarcasm but supplies no community
sentiment. If article analysis is rejected or unavailable, annotation may continue using title/thread
context; independently uninterpretable comments are rejected and refilled.

The strict `comment-v2.2.0` accepted result has exactly `contract_version`, `comment_id`, `reject`,
`ai_dimensions`, `article_relation`, `parent_relation`, and `summary`. Each AI dimension has
`applicability`, `score`, `confidence`, `stance_basis`, and `rationale`. Allowed stance bases are
`direct`, `endorsed_article_thesis`, `endorsed_parent_claim`, `rejected_contextual_claim`,
`inferred_from_sarcasm`, and `none`. `not_addressed` requires null/zero/`none`.

Article relation is independently one of `supports`, `challenges`, `qualifies`, `mixed`, `unclear`,
or `not_applicable`, targeting dimensions or `factual_detail`, `framing`, `method`, and
`article_quality`. Parent relation is independently `agrees`, `disagrees`, `clarifies`, `questions`,
`corrects`, `other`, or `not_applicable`. Relation confidence never enters AI aggregation.

## Ranked-tree selection and deterministic refill

Eligible comments are public, live, non-dead items with non-empty cleaned text. Each parent's public
`kids` order supplies a snapshot-dependent ordinal sibling rank; it does not reveal private scores.
Persist collection time, root rank, local sibling rank, depth, ancestry/context IDs, candidate rank,
selection pass/reason, and refill outcome. Never derive a story-global DFS rank.

For eligible count `E`:

```text
accepted_target = min(E, clamp(12, 32, ceil(4 × sqrt(E))))
top_level_target = ceil(0.60 × accepted_target)
reply_target = accepted_target − top_level_target
branch_cap = max(3, ceil(0.15 × accepted_target))
author_cap = 2
```

Candidate waves are: one top-level per author in story-child rank; one reply per root branch in
root-rank/local-sibling round-robin; remaining top-level; remaining replies in branch round-robin.
Unused quota transfers only after its stratum is exhausted. Model rejection, invalid response, or an
accepted result with all dimensions `not_addressed` does not consume the accepted target. Refill uses
the next deterministic candidate, bounded to at most `2T` attempted candidates per story. This gives
each target slot one deterministic replacement without allowing malformed model output to trigger an
unbounded API loop. Author and branch caps apply to accepted comments.

Comment length beyond non-empty text, article stance, model sentiment, story score, and account
reputation never affect candidate ordering or acceptance capacity.

## Aggregation

Public local rank is an ordinal visibility discount:

```text
branch_rank_weight = 1 / log2(root_rank + 1)
within_branch_weight = 1                                      # root
within_branch_weight = 0.85^depth / log2(sibling_rank + 1)   # reply
raw_visibility_weight = branch_rank_weight × within_branch_weight

author_comment_base = 1 / applicable_comments_by_author
branch_authors = unique applicable authors in root branch
concentration_factor = author_comment_base / sqrt(branch_authors)
visibility_influence = raw_visibility_weight × concentration_factor × annotation_confidence
diversity_influence = concentration_factor × annotation_confidence
```

Only applicable absolute AI stances enter either mean. Export `visibility_weighted_score` as primary,
`diversity_balanced_score` as a diagnostic, and their absolute difference as `ranking_sensitivity`.
Rank changes influence, never an annotation's score.

Measurement confidence uses structural/rank weights and annotation clarity:

```text
clarity = structural/rank-weighted mean annotation confidence
ESS = (sum visibility_influence)^2 / sum(visibility_influence^2)
sample_adequacy = min(1, ESS / 12)
branch_adequacy = min(1, applicable_branch_count / 6)
dimension_coverage = applicable_selected / analyzed_selected
community_confidence = clarity × sqrt(sample_adequacy × branch_adequacy × dimension_coverage)
```

Confidence must not depend on score direction/magnitude, disagreement, polarization, article stance,
story score, raw comment volume, or account reputation.

For each dimension, visibility influence also yields positive/neutral/negative shares,
`disagreement = weighted_mean(abs(score - community_score)) / 2`, and:

```text
balance = 4 × positive_share × negative_share
separation = (mean_positive - mean_negative) / 4
polarization = balance × separation
```

Polarization is zero when either directional side is absent. Clamp normalized metrics to `[0,1]`
only for floating-point safety. Persist applicable comment/author/branch counts, ESS, coverage,
clarity, and the highest-influence opposing comment/share per dimension whenever one exists. Raw
metrics are normative; no cross-dimension consensus label exists.

Story comment volume can enlarge adaptive sample capacity but never directly changes sentiment,
confidence after saturation, or global influence. Existing story-score/time-decay remains the global
engagement signal. `/v2` remains disconnected from generated v2 exports pending separate review.
