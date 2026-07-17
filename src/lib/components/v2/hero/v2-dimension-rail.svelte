<script lang="ts">
  import type { V2AggregateDimension } from "$lib/types/v2";
  import { direction } from "$lib/v2/derive";

  interface Props { label: string; value: V2AggregateDimension | null; }
  let { label, value }: Props = $props();
  const tone = $derived(
    !value ? "missing" : value.rawScore > 0.2 ? "positive" : value.rawScore < -0.2 ? "negative" : "neutral"
  );
  const adequacy = $derived(
    !value ? "N/A" : value.confidence >= 0.75 ? "HIGH" : value.confidence >= 0.45 ? "MED" : "LOW"
  );
</script>

<div class="v2-dimension" data-tone={tone}>
  <span>{label}</span>
  <strong>{value ? `${value.rawScore >= 0 ? "+" : ""}${value.rawScore.toFixed(2)}` : "N/A"}</strong>
  <small>{direction(value?.rawScore ?? null) ?? "N/A"} · {adequacy}</small>
</div>
