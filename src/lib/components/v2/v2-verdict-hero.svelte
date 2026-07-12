<script lang="ts">
  interface VerdictData {
    verdict: "YES" | "NO" | "NOT_YET";
    finalScore: number;
    verdictConfidence: "high" | "medium" | "low";
    totalAnalyzed: number;
    oldestArticleDate: string;
    newestArticleDate: string;
  }

  let { verdict }: { verdict: VerdictData } = $props();
  const answer = $derived(verdict.verdict === "NOT_YET" ? "NOT YET" : verdict.verdict);
  const summary = $derived(
    verdict.verdict === "YES"
      ? "Developer sentiment currently clears the positive threshold."
      : verdict.verdict === "NO"
        ? "Developer sentiment currently resolves negative."
        : "Developer sentiment has not cleared the positive threshold."
  );
</script>

<section class="v2-panel v2-hero" aria-labelledby="v2-verdict-heading">
  <div class="v2-dot-field" aria-hidden="true"></div>
  <div class="v2-radar" aria-hidden="true"><i></i><i></i><i></i><span></span></div>
  <header>
    <p><b>$</b> ./analyze --source hn --topic "ai coding tools"</p>
    <span class="v2-badge"><i></i> ANALYSIS COMPLETE</span>
  </header>
  <div class="v2-hero__body">
    <p id="v2-verdict-heading" class="v2-hero__question">Is AI good yet?</p>
    <p class="v2-hero__answer" data-text={answer}>{answer}</p>
    <p class="v2-hero__summary"><span>&gt;</span> {summary}</p>
    <div class="v2-hero__readout">
      <span>SCORE <strong>{verdict.finalScore.toFixed(1)}</strong>/100</span>
      <span>CONFIDENCE <strong>{verdict.verdictConfidence.toUpperCase()}</strong></span>
      <span>WINDOW <strong>{verdict.totalAnalyzed.toLocaleString("en-US")}</strong> ARTICLES</span>
    </div>
  </div>
  <footer>Rolling static analysis · {verdict.oldestArticleDate.slice(0, 10)} → {verdict.newestArticleDate.slice(0, 10)}</footer>
</section>
