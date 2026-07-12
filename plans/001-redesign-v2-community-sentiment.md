# Plan 001: Redesign v2 community sentiment and broad-capture prompts

> **Executor instructions**: Read this entire plan before editing. Implement the approved methodology
> exactly and keep changes surgical. Repository policy requires explicit user confirmation before any
> test, lint, type-check, or build command; after implementation, stop and ask before running checks.
> Committing requires a separate explicit confirmation. Do not connect `/v2` to v2 exports.
>
> **Drift check (run first, read-only)**:
> `git diff --stat 5e8af32..HEAD -- docs pipeline/src pipeline/tests cli.ts package.json docs_internal/architecture.md CHANGELOG.md`
> The listed v2 files are currently uncommitted, so also inspect `git status --short`. Preserve all
> unrelated user changes. If an in-scope file has materially changed from the current-state description
> below, stop and report the mismatch before editing.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: none
- **Category**: direction, correctness, tests, docs
- **Planned at**: commit `5e8af32`, 2026-07-12

## Why this matters

V2 must measure the AI-directed stance expressed in the visible HN discussion at a recorded collection
time. It must separately describe whether a comment supports or challenges the article and how a reply
relates to its parent. The current implementation cannot represent those distinctions, flattens HN's
ranked tree into a misleading global position, batches unrelated comments together, weights by author
karma, and reduces confidence when a thread is genuinely divided. This plan replaces those behaviors
with isolated context-aware annotation, adaptive rank-aware sampling, visibility and diversity views,
and explicit disagreement and polarization metrics.

## Approved product decisions

These decisions are fixed for this plan. Do not reopen or silently reinterpret them:

1. Community sentiment represents visible expressed HN discussion at collection time, not silent
   readers, all HN users, or public opinion.
2. Primary dimensions are present capability, expected trajectory, and societal impact. Their
   equal-dimension composite remains secondary.
3. Article stance and community reaction remain independent sources with 40% article / 60% community
   priors. Confidence changes influence only; it never changes sentiment direction or distance from
   neutral.
4. Absolute AI stance, article relation, and parent relation are separate annotations. Only absolute
   AI stance enters the community verdict.
5. Each voting comment is analyzed in an isolated model request. Unrelated selected comments must not
   appear in the same prompt.
6. Comment context consists of the structured article thesis, immediate parent, and root comment when
   distinct. Context informs interpretation but never contributes sentiment directly.
7. Public HN sibling order is an ordinal visibility signal. It does not reconstruct private scores.
8. The primary community estimate is visibility-weighted. A diversity-balanced estimate and the delta
   between the two are required diagnostics.
9. Sampling adapts from 12 to 32 accepted comments. Rejected/non-addressing candidates trigger
   deterministic refill.
10. Commenter karma is removed completely from selection, storage, prompts, and aggregation.
11. Disagreement and polarization are measured separately and never reduce measurement confidence.
12. Story comment volume may enlarge the sample but must not directly affect sentiment or global
    influence. Existing story-score/time-decay influence remains the global engagement signal.
13. V1 contracts, prompts, exports, data, and routes remain unchanged.
14. `/v2` remains disconnected from v2 exports until the contract and initial data are reviewed.

## Research basis

- Official HN API: every item's `kids` are in ranked display order:
  https://github.com/HackerNews/API
- HN FAQ: comment rank includes points/time and other moderation and anti-abuse factors; author karma
  does not make posts rank higher: https://news.ycombinator.com/newsfaq.html
- Target-dependent sentiment requires identifying the opinion target rather than transferring generic
  polarity: https://aclanthology.org/P11-1016.pdf
- Stance, sentiment, and target-of-opinion are distinct labels:
  https://aclanthology.org/L16-1623/
- Too little annotation context creates ambiguity while excessive context can overpower the target
  text: https://aclanthology.org/D17-1116/
- Kish-style effective sample size describes weight concentration but is not a claim of probability
  sampling or representativeness:
  https://www150.statcan.gc.ca/n1/pub/12-001-x/2015002/article/14236/02-eng.htm

## Current state

- `docs/v2-sentiment-prompt.md` documents article/comment v2.1 contracts, fixed 12-comment sampling,
  karma weighting, one community consensus label, and confidence penalized by disagreement.
- `pipeline/src/v2_models.py` defines strict article/comment contracts and aggregation. Its current
  comment contract contains only the three AI dimensions and a summary. `aggregate_comment_dimension`
  multiplies selection weight, karma, and confidence; then includes disagreement in confidence.
- `pipeline/src/hn_comments_v2.py` flattens the tree depth-first into `display_order`, selects at most
  8 roots and 4 replies, excludes text below 40 characters, derives a global position weight, and
  fetches author karma.
- `pipeline/src/sentiment_v2.py` places all selected comments in one model request. Each reply receives
  only immediate-parent context; the model does not receive structured article thesis or root context.
- `pipeline/src/store/v2.py` stores comments, users/karma snapshots, selections, normalized runs,
  dimension rows, and comment annotations.
- `pipeline/src/export_v2.py` combines article/community sources and globally weights stories using HN
  story score and time decay.
- `pipeline/tests/test_hn_comments_v2.py` and `pipeline/tests/test_v2_models.py` characterize the current
  fixed selection, karma multiplier, contracts, and aggregation.
- `docs/prefilter_prompt.md` and `docs/sentiment_prompt.md` are v1 coding-specific contracts. They must
  not be rewritten or reinterpreted for v2.
- The working tree also contains unrelated frontend changes. They belong to the user and must not be
  modified, formatted, reverted, or included in a commit.

## Commands and execution gates

| Purpose | Command | Expected on success |
| --- | --- | --- |
| Inspect changes | `git diff -- <in-scope files>` | only intended v2/docs changes |
| Narrow tests | `.venv\\Scripts\\python.exe -m pytest pipeline/tests/test_hn_comments_v2.py pipeline/tests/test_v2_models.py -q` | all selected tests pass |
| Pipeline tests, only if separately approved | `.venv\\Scripts\\python.exe -m pytest pipeline/tests -q` | pass, except documented DB fixture limitation |

Do not run either pytest command, lint, type-check, or build until the user explicitly approves checks.
Do not install dependencies. Do not run the pipeline or call Groq/HN as verification unless separately
authorized.

## Scope

**Expected implementation files**:

- `docs/v2-sentiment-prompt.md`
- `docs/v2-prefilter-prompt.md` (create)
- `docs/v2-article-sentiment-prompt.md` (create, or use a comparably explicit approved name)
- `pipeline/src/v2_models.py`
- `pipeline/src/hn_comments_v2.py`
- `pipeline/src/sentiment_v2.py`
- `pipeline/src/store/v2.py`
- `pipeline/src/export_v2.py`
- `pipeline/tests/test_hn_comments_v2.py`
- `pipeline/tests/test_v2_models.py`
- Add narrowly necessary new v2 tests under `pipeline/tests/`
- `cli.ts` and `package.json` only if command arguments or entry points change
- `docs_internal/architecture.md`
- `CHANGELOG.md` under `[Unreleased]`

**Out of scope**:

- `docs/prefilter_prompt.md` and `docs/sentiment_prompt.md` except an optional one-line pointer to their
  separate v2 counterparts; do not change their contracts.
- V1 pipeline modules, tables, exports, JSON contracts, and routes.
- `src/routes/v2/+page.svelte` and all frontend data wiring.
- Existing static v2 fixture data used by `/v2`.
- Global influence redesign beyond exposing the approved community diagnostics.
- Generating the 20k-article rerun or any initial v2 export.
- Any unrelated working-tree change.

## Git workflow

- If the user asks for a new branch, use `feature/v2-community-methodology`; never commit to `main`.
- Do not switch branches when doing so could disturb uncommitted user changes; ask first.
- Do not stage or commit without explicit permission.
- If permission is granted, use a Conventional Commit such as:
  `feat(pipeline): redesign v2 community sentiment analysis`.
- Do not push or open a PR unless separately instructed.

## Target contracts and formulas

### Comment context packet

Every voting comment gets its own request containing:

1. Article title.
2. Structured article context: scopes, article summary, and for each dimension its applicability,
   score, short rationale, and exact supporting evidence excerpts.
3. Root comment when the voting comment is a descendant and the root differs from its parent.
4. Immediate parent when the voting comment is a reply.
5. The voting comment, clearly delimited as the only text to annotate.

Article, root, and parent are explicitly marked `CONTEXT ONLY`. The prompt must say they may resolve
references, agreement, disagreement, and sarcasm but supply no community sentiment by themselves.

### Comment result

Use a new immutable contract version. Each accepted result contains:

```json
{
  "contract_version": "comment-v2.2.0",
  "comment_id": 123,
  "reject": false,
  "ai_dimensions": {
    "capability": {
      "applicability": "explicit",
      "score": -1,
      "confidence": 0.86,
      "stance_basis": "direct",
      "rationale": "The commenter says current systems create more correction work than they save."
    },
    "trajectory": {
      "applicability": "not_addressed",
      "score": null,
      "confidence": 0,
      "stance_basis": "none",
      "rationale": "No forecast is expressed or endorsed."
    },
    "impact": {
      "applicability": "not_addressed",
      "score": null,
      "confidence": 0,
      "stance_basis": "none",
      "rationale": "No societal effect is discussed."
    }
  },
  "article_relation": {
    "relation": "supports",
    "targets": ["capability"],
    "confidence": 0.91,
    "rationale": "The comment explicitly endorses the article's capability thesis."
  },
  "parent_relation": {
    "relation": "agrees",
    "confidence": 0.88,
    "rationale": "The reply endorses its parent's stated limitation."
  },
  "summary": "Current systems create more correction work than value."
}
```

Allowed `stance_basis`: `direct`, `endorsed_article_thesis`, `endorsed_parent_claim`,
`rejected_contextual_claim`, `inferred_from_sarcasm`, `none`.

Allowed article relations: `supports`, `challenges`, `qualifies`, `mixed`, `unclear`,
`not_applicable`. Allowed relation targets: the three dimensions plus `factual_detail`, `framing`,
`method`, and `article_quality`.

Allowed parent relations: `agrees`, `disagrees`, `clarifies`, `questions`, `corrects`, `other`,
`not_applicable`.

`not_addressed` requires score `null`, confidence `0`, and `stance_basis: none`. Relation confidence
must never be used in the AI community score.

### Adaptive sampling

Let `E` be all public, live, non-dead comments with non-empty cleaned text at the snapshot:

```text
accepted_target = min(E, clamp(12, 32, ceil(4 × sqrt(E))))
top_level_target = ceil(0.60 × accepted_target)
reply_target = accepted_target − top_level_target
branch_cap = max(3, ceil(0.15 × accepted_target))
author_cap = 2
```

Remove the 40-character selection cutoff. Select and annotate candidates in deterministic waves.
Rejected candidates or accepted comments with all three AI dimensions `not_addressed` do not consume
the accepted target; refill until the target is met or the candidate universe is exhausted.

Selection order:

1. One top-level candidate per author in official story-child rank.
2. One reply per root branch, round-robin by root rank and then the reply's actual sibling rank.
3. Remaining top-level candidates, respecting author cap.
4. Remaining replies, round-robin, respecting author and branch caps.
5. Transfer unused quota only when one stratum has no remaining eligible candidates.

Persist `root_rank`, `sibling_rank`, `depth`, ancestry needed for root/parent context, candidate rank,
selection pass/reason, accepted/rejected refill status, and collection timestamp. Do not derive a
story-global depth-first rank.

### Visibility and diversity weights

Use public rank as an ordinal visibility discount:

```text
branch_rank_weight = 1 / log2(root_rank + 1)
within_branch_weight = 1                                      # root
within_branch_weight = 0.85^depth / log2(sibling_rank + 1)   # reply
raw_visibility_weight = branch_rank_weight × within_branch_weight
```

For an applicable dimension, limit repeated-author and large-branch dominance:

```text
author_comment_base = 1 / applicable_comments_by_author
branch_authors = unique applicable authors in the root branch
concentration_factor = author_comment_base / sqrt(branch_authors)

visibility_influence =
  raw_visibility_weight × concentration_factor × annotation_confidence

diversity_influence =
  concentration_factor × annotation_confidence
```

Calculate both weighted means. The visibility-weighted score is primary. Export:

```text
visibility_weighted_score
diversity_balanced_score
ranking_sensitivity = abs(visibility_weighted_score - diversity_balanced_score)
```

Rank changes influence only. They never alter an individual annotation's score.

### Confidence and distribution metrics

For each dimension, calculate measurement confidence from the visibility weights:

```text
clarity = structurally/rank-weighted mean annotation confidence
ESS = (sum final_weights)^2 / sum(final_weights^2)
sample_adequacy = min(1, ESS / 12)
branch_adequacy = min(1, applicable_branch_count / 6)
dimension_coverage = applicable_selected / analyzed_selected

community_confidence =
  clarity × sqrt(sample_adequacy × branch_adequacy × dimension_coverage)
```

Do not include score, direction, disagreement, polarization, article stance, HN story score, comment
volume, or karma in this confidence formula.

Also calculate per dimension:

```text
positive_share = normalized influence with score > 0
neutral_share = normalized influence with score = 0
negative_share = normalized influence with score < 0
disagreement = weighted mean(abs(score - community_score)) / 2
balance = 4 × positive_share × negative_share
separation = (mean_positive - mean_negative) / 4
polarization = balance × separation
```

Clamp normalized metrics to `[0, 1]` only for floating-point safety. When one directional side is
absent, polarization is zero. Store applicable comment, author, and branch counts plus ESS.

Consensus is per dimension, never one label averaged across dimensions. If labels are retained, derive
them deterministically from direction shares and polarization and document exact thresholds. Prefer
exporting raw metrics as normative and treating labels as display summaries.

Preserve the highest-influence opposing comment per dimension whenever one exists, together with its
opposing influence share. Remove the current 15% single-comment cutoff and cross-dimension denominator.

## Steps

### Step 1: Update the normative methodology and version map

Revise `docs/v2-sentiment-prompt.md` first so it becomes the normative contract for the code change.
Document the measurement definition, isolated annotation, context-only rule, adaptive selection,
visibility/diversity estimates, formulas, invariants, confidence semantics, distribution metrics,
popular-story behavior, and karma removal. Assign new immutable selection, comment contract, prompt,
aggregation, and parser versions wherever behavior or shape changes.

Create separate v2 prefilter and article-sentiment prompt documents. Keep v1 prompt documents intact.

**Verify after permission**: use `rg` to confirm the normative v2 document contains no statement that
karma affects selection or aggregation, no fixed 8/4 allocation, and no confidence penalty based on
disagreement.

### Step 2: Define the broad-capture v2 prefilter prompt

Create `docs/v2-prefilter-prompt.md`. Optimize recall over the existing approximately 20k scraped
articles. Eligibility means at least one attributable judgment, forecast, or substantive finding about
present AI capability, expected trajectory, or societal impact.

Include broad scopes: coding, research, education, labor, economy, creativity, safety, governance,
environment, and general. Include empirical research, credible factual reporting, policy analysis, and
promotional claims with substantive dimension claims. Exclude only not-AI content, no dimension
judgment/finding, unusable extraction, claim-free lists/changelogs, and tutorials without evaluation.

Use a strict versioned JSON contract containing at least:

```text
contract_version
eligible
reason_code
dimension_candidates
scopes
content_quality
confidence
reason
```

Prefilter confidence must never enter sentiment. Document truncation and the prompt-injection boundary.
Do not wire the prompt into v1 storage or overwrite v1 category fields; if implementation storage is
needed, use isolated versioned v2 runs.

**Verify after permission**: contract examples validate against the documented allowed values, and
coding is not required for eligibility.

### Step 3: Define the v2 article sentiment/thesis prompt

Create `docs/v2-article-sentiment-prompt.md` and align the executable article prompt with it. Preserve
the approved three dimensions, `not_addressed`, confidence semantics, evidence attribution, and strict
rejections. Add or formalize a structured thesis package sufficient for comment interpretation:

- article scopes and summary;
- each dimension's applicability, score, confidence, concise rationale, and evidence IDs;
- exact evidence and attribution;
- scope/time horizon when material.

Avoid duplicating the full article into community prompts. The structured thesis and evidence are
context only. Version the article contract if its JSON shape changes.

**Verify after permission**: article contract tests cover factual reporting, promotional claims,
research findings, missing dimensions, quoted-but-unadopted claims, and rejection.

### Step 4: Replace flattened selection with ranked-tree sampling

In `pipeline/src/hn_comments_v2.py` and storage helpers:

- preserve local ranked positions while walking each parent's `kids`;
- store sufficient ancestry to retrieve immediate parent and root;
- remove karma API calls and cache dependencies from this path;
- remove `MIN_COMMENT_CHARS` as an eligibility rule;
- implement the adaptive target, quotas, passes, caps, transfer, and deterministic candidate stream;
- separate candidate selection from accepted-target refill so model rejection can request the next
  deterministic candidate without refetching or changing prior choices;
- persist exact selection/refill reasons and snapshot metadata.

Do not use article content, model sentiment, karma, comment length beyond non-empty text, or story score
to choose between eligible candidates.

**Verify after permission**: narrow selection tests pass and explicitly prove every invariant listed in
the Test plan.

### Step 5: Implement isolated context-aware comment annotation

In `pipeline/src/sentiment_v2.py`:

- analyze the article first or load its accepted versioned result;
- build one bounded context packet per candidate;
- call the model once per voting comment with bounded concurrency;
- validate the new strict single-comment contract;
- feed rejection/all-not-addressed results back to the deterministic refill loop;
- never annotate or aggregate context-only parent/root/article text;
- persist the exact isolated input snapshot, prompt hash, input hash, model parameters, article-run
  dependency, and context IDs;
- make community-run reproducibility include every considered candidate, not only accepted comments.

If the article analysis is rejected or unavailable, do not silently provide a fabricated thesis. Either
annotate comments with title/thread context while marking article context unavailable, if the approved
contract supports it, or stop that community run with a versioned reason. Choose and document one
behavior before coding; recommended behavior is to allow community annotation without article thesis
when comments remain independently interpretable.

**Verify after permission**: mocked tests prove one model call contains exactly one voting comment and
that a model cannot observe unrelated selected comments.

### Step 6: Implement hierarchical visibility and diversity aggregation

In `pipeline/src/v2_models.py`:

- remove karma parameters and multipliers;
- implement the approved visibility and diversity influences;
- aggregate per dimension only across applicable AI stances;
- compute confidence without disagreement;
- compute sign shares, disagreement, polarization, ESS, coverage, and applicable counts;
- compute per-dimension dissent exemplar/share;
- remove the single cross-dimension consensus calculation;
- preserve `not_addressed` when no applicable dimension evidence exists;
- ensure score zero remains genuine neutral/balance, never missingness.

Use small named pure functions for formulas that need direct unit tests. Do not introduce a generic
scoring framework or unnecessary configuration system; constants plus immutable version identifiers are
sufficient.

**Verify after permission**: formula tests pass with exact hand-calculated fixtures.

### Step 7: Migrate normalized v2 storage additively

In `pipeline/src/store/v2.py`, update only isolated v2 tables. Preserve existing uncommitted v2.1 data
where practical, but never reinterpret it as v2.2. New versions must coexist with old runs.

Store or make queryable:

- local ranks, depth, root, parent, and ancestry/context IDs;
- candidate pass/reason and accepted/refill outcome;
- comment `ai_dimensions`, article relation, parent relation, and stance basis;
- article-run/context dependency;
- both community estimates and all per-dimension diagnostics;
- exact input snapshots and immutable versions/hashes.

Remove new-run dependence on karma. Dropping an existing v2-only karma column/table is optional and not
worth destructive migration risk; it may remain unused if removing it would complicate migration.

**Verify after permission**: storage tests prove v2.1 and v2.2 runs do not collide and independent
article/community reruns remain possible.

### Step 8: Update export without connecting `/v2`

In `pipeline/src/export_v2.py`:

- export the primary visibility-weighted community score;
- export the diversity-balanced score, ranking sensitivity, distribution metrics, confidence
  components, counts, ESS, per-dimension consensus/display label if retained, dissent, and source
  divergence;
- retain 40/60 confidence-aware source combination;
- retain story score/time decay as global influence;
- do not multiply influence by comment count or sample size;
- keep three dimension verdicts primary and composite secondary.

Do not generate files and do not modify frontend imports or `/v2` data sources during this plan.

**Verify after permission**: pure export aggregation tests show comment volume cannot change a fixed
story's sentiment or global base influence.

### Step 9: Update CLI/docs/changelog narrowly

Expose any new Python arguments in `cli.ts` and package scripts only when needed. Update
`docs_internal/architecture.md` to match the actual implementation, including the explicit estimand and
limitations. Update `CHANGELOG.md` under `[Unreleased]` with the community methodology and broad v2
capture prompts.

Do not claim the methodology is statistically representative. Use “visible expressed discussion at
collection time” consistently.

**Verify after permission**: `rg` confirms v1 contracts/routes remain referenced unchanged and `/v2`
has no new import from generated v2 exports.

### Step 10: Stop and request verification permission

Summarize changed files and unresolved calibration choices. Ask the user whether to run the narrow v2
pytest files. Do not run them before receiving explicit confirmation. After approved checks complete,
report results and separately ask whether to commit. Do not combine check permission with assumed commit
permission.

## Test plan

Extend existing v2 tests using their current plain pytest style. Required cases:

### Selection

- Adaptive target boundaries: fewer than 12, exactly 12, medium thread, and 32 cap.
- Determinism for identical ranked-tree snapshots.
- `root_rank` and `sibling_rank` come from the correct parent `kids`, not DFS order.
- No author exceeds two accepted comments; first diversity pass uses at most one.
- Branch cap follows `max(3, ceil(0.15 × target))`.
- A branch cannot receive a second reply while an earlier eligible branch has none.
- Quota transfer occurs only when one stratum is exhausted.
- Short non-empty contextual comments remain eligible.
- Deleted, dead, and empty comments are excluded.
- Rejected/all-not-addressed candidates trigger deterministic refill.
- Karma and article sentiment cannot affect selection.

### Context and contracts

- One request contains one voting comment only.
- Parent and distinct root are context-only and never annotated.
- Structured article thesis/evidence is present when available.
- Direct AI stance, article praise, article disagreement, factual correction, terse agreement, sarcasm,
  and insufficient context produce distinct valid shapes.
- `not_addressed` requires null/zero/none.
- Relation confidence never enters AI aggregation.
- Extra keys, invalid enums, missing IDs, and wrong versions fail validation.

### Aggregation

- Visibility rank changes influence but never an annotation's score.
- Local sibling ranks produce expected hand-calculated weights.
- Repeated comments from one author cannot create extra author mass.
- Branch influence grows sublinearly.
- Visibility and diversity scores match hand calculations.
- Ranking sensitivity is their absolute difference.
- Equal positive/negative extremes yield score zero, high disagreement, and maximum polarization.
- Unanimous positive comments yield zero polarization.
- Neutral plus one extreme yields disagreement without false two-sided polarization.
- High disagreement does not lower confidence when clarity/coverage/ESS are fixed.
- No applicable comments yields `not_addressed`.
- Dissent is per dimension and does not require a 15% single-comment threshold.
- More story comments alone cannot alter sentiment, confidence after saturation, or global influence.
- Source combination still implements
  `sum(score × prior × confidence) / sum(prior × confidence)`.

### Storage/export compatibility

- V2.1 and new-version runs coexist and are selected by exact versions.
- Article and community runs persist independently.
- Input snapshots include all context and considered candidates.
- Export includes diagnostics without changing v1 JSON.
- `/v2` remains disconnected from generated v2 data.

## Done criteria

- [ ] Normative docs define the approved estimand, contracts, sampling, context, weights, confidence,
      disagreement, polarization, and limitations without contradicting code.
- [ ] Separate broad-capture v2 prefilter and article-sentiment prompt docs exist; v1 prompt contracts
      are unchanged.
- [ ] Karma has no effect on new v2 selection, annotation, aggregation, confidence, or export.
- [ ] Comment annotation requests are isolated and context-aware.
- [ ] Adaptive accepted sampling and deterministic refill satisfy every listed invariant.
- [ ] Primary visibility and diagnostic diversity scores are both persisted and exported.
- [ ] Confidence excludes sentiment direction and disagreement.
- [ ] Popularity affects sample capacity and existing global story influence only.
- [ ] V1 code/data/routes and `/v2` wiring remain unchanged.
- [ ] Only in-scope files are modified.
- [ ] After explicit approval, narrow v2 tests pass.
- [ ] No test, lint, type-check, build, pipeline run, export generation, commit, push, or PR occurs
      without its required user authorization.

## STOP conditions

Stop and report instead of improvising if:

- Implementing isolated comment requests would require breaking v1 code or changing `/v2` wiring.
- The current uncommitted v2 schema cannot coexist with a new immutable version without destructive
  migration.
- HN data available to the collector does not preserve each parent's ranked `kids` order.
- Article context cannot be tied to an exact accepted article run/version/hash.
- Adaptive refill would require sentiment-dependent candidate selection.
- A proposed confidence calculation includes disagreement, sentiment magnitude/direction, article
  score, karma, or unsaturated raw comment volume.
- An in-scope file materially differs from this plan's current-state description.
- Work overlaps unrelated uncommitted frontend changes.
- A check fails twice after permission and a reasonable focused correction.
- Completion requires running the 20k rerun, generating exports, or connecting frontend data.

## Maintenance notes

- Rank is a snapshot-dependent ordinal visibility signal, not a private vote total. Persist collection
  time and exact local ranks so reruns are interpretable.
- All constants and formulas are provisional until reviewed against a manually annotated calibration
  set. Changing them later requires new immutable selection/aggregation versions.
- Reviewers should scrutinize contextual stance inheritance. Article or parent scores must never be
  copied automatically into a comment.
- Before the 20k rerun, manually review a stratified set containing highly positive/negative articles,
  factual reporting, promotional material, research, sarcasm, short replies, and polarized large
  threads.
- Initial export generation, calibration review, frontend contract design, and `/v2` connection are
  intentionally deferred to later approved tasks.
