<script lang="ts">
  import { onMount } from "svelte";
  import type { V2Verdict } from "$lib/types/v2";
  import { verdictDecode } from "$lib/actions/verdict-decode";
  import DimensionRail from "./v2-dimension-rail.svelte";

  interface Props { verdict: V2Verdict; pipelineState: string; thinSample: boolean; }
  let { verdict, pipelineState, thinSample }: Props = $props();
  // eslint-disable-next-line no-unassigned-vars -- assigned via bind:this
  let answerNode: HTMLElement;
  let beam = $state(false);
  const answer = $derived(verdict.composite?.verdict.replace("_", " ") ?? "NO DATA");
  const explanation = $derived(verdict.composite
    ? `${verdict.articleCount} analyzed ${verdict.articleCount === 1 ? "story" : "stories"} resolve to ${verdict.composite.rawScore >= 0 ? "+" : ""}${verdict.composite.rawScore.toFixed(2)} across addressed dimensions${thinSample ? ". Thin sample — read as provisional." : "."}`
    : "The V2 analysis contract is wired. No accepted V2 generation has been published yet.");

  onMount(() => verdictDecode(answerNode, answer, { delay: 180, onDone: () => beam = true }));
</script>

<section id="verdict" class="v2-section v2-hero" aria-labelledby="v2-question">
  <header class="v2-section__header">
    <div>
      <p>AGGREGATE VERDICT</p>
      <h2 id="v2-question">Is AI good yet?</h2>
    </div>
    <span>{pipelineState}</span>
  </header>
  <div class="v2-hero__content">
    <p class="v2-hero__answer" class:v2-hero__answer--beam={beam} class:v2-hero__answer--thin={thinSample} bind:this={answerNode} aria-label={`Aggregate verdict: ${answer}${thinSample ? " (thin sample)" : ""}`}>{answer}</p>
    {#if thinSample}<p class="v2-hero__thin" aria-hidden="true">— THIN SAMPLE</p>{/if}
    <p class="v2-hero__summary">{explanation}</p>
    <div class="v2-dimension-rail" aria-label="Aggregate dimension scores">
      <DimensionRail label="CAPABILITY" value={verdict.dimensions.capability} />
      <DimensionRail label="TRAJECTORY" value={verdict.dimensions.trajectory} />
      <DimensionRail label="IMPACT" value={verdict.dimensions.impact} />
    </div>
    <p class="v2-hero__window">WINDOW {verdict.windowMonths} MONTHS · {verdict.articleCount} ANALYZED STORIES · INFLUENCE {verdict.influenceVersion}</p>
  </div>
</section>
