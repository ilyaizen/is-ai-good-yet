/**
 * NEUTRAL_MULTIPLIER: Controls how neutral articles (-0.2 to +0.2 sentiment) contribute to the verdict.
 *
 * Neutral articles always have sentiment = 0 (only mixed+uncertain combination gives this),
 * so their contribution is based on influence alone, not sentiment × influence.
 *
 * Formula: neutral_contribution = influenceScore × NEUTRAL_MULTIPLIER
 *
 * Examples with a 200-influence article:
 * - NEUTRAL_MULTIPLIER = 0.5  → contributes +100 (half strength toward "GOOD")
 * - NEUTRAL_MULTIPLIER = -0.5 → contributes -100 (half strength toward "BAD")
 * - NEUTRAL_MULTIPLIER = 0    → contributes 0 (excluded from verdict, original behavior)
 * - NEUTRAL_MULTIPLIER = 1.0  → contributes +200 (full strength toward "GOOD")
 */
export const NEUTRAL_MULTIPLIER = -0.5

/**
 * Swift easing curve for snappy, premium animations.
 * Matches --ease-swift in app.css
 */
export const EASE_SWIFT = "cubic-bezier(0, 0.7, 0.1, 1)"
