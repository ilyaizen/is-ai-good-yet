<script lang="ts">
  import type { V2AggregateDimension } from "$lib/types/v2";

  interface Props { label: string; value: V2AggregateDimension | null; }
  let { label, value }: Props = $props();
  const direction = $derived(!value ? "N/A" : value.rawScore > 0.2 ? "POSITIVE" : value.rawScore < -0.2 ? "NEGATIVE" : "MIXED");
  const tone = $derived(!value ? "missing" : value.rawScore > 0.2 ? "positive" : value.rawScore < -0.2 ? "negative" : "neutral");
</script>

<div class="v2-dimension" data-tone={tone}>
  <span>{label}</span>
  <strong>{value ? `${value.rawScore >= 0 ? "+" : ""}${value.rawScore.toFixed(2)}` : "N/A"}</strong>
  <small>{direction} · CONF {value ? value.confidence.toFixed(2) : "N/A"}</small>
  <small>{value?.articleCount ?? 0} STORIES · {value ? `${value.score.toFixed(0)}/100` : "NO DATA"}</small>
</div>
