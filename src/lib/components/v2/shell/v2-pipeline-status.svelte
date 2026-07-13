<script lang="ts">
  import type { V2PipelineStatus } from "$lib/types/v2";

  interface Props { status: V2PipelineStatus; }
  let { status }: Props = $props();
  const now = Date.now();
  const delayed = $derived.by(() => {
    const next = new Date(status.schedule.nextRunAt).getTime();
    return Number.isFinite(next) && now > next + status.schedule.graceMinutes * 60_000;
  });
  const state = $derived(status.currentRun ? "RUNNING" : status.lastRun?.status === "failed" ? "FAILED" : delayed ? "DELAYED" : !status.lastRun ? "AWAITING FIRST RUN" : status.lastRun.status === "partial" ? "DEGRADED" : "CURRENT");
  const relative = $derived(status.lastRun ? new Intl.RelativeTimeFormat("en", { numeric: "auto" }).format(Math.round((new Date(status.lastRun.finishedAt).getTime() - Date.now()) / 3_600_000), "hour") : "never");
</script>

<section class="v2-pipeline" data-state={state} aria-label="Pipeline status">
  <div class="v2-pipeline__state"><i aria-hidden="true"></i><strong>{state}</strong></div>
  <dl>
    <div><dt>LAST RUN</dt><dd>{relative}</dd></div>
    <div><dt>DURATION</dt><dd>{status.lastRun ? `${status.lastRun.durationSeconds}s` : "N/A"}</dd></div>
    <div><dt>PROCESSED</dt><dd>{status.lastRun?.articlesProcessed ?? 0} stories / {status.lastRun?.commentsAnalyzed ?? 0} comments</dd></div>
    <div><dt>NEXT</dt><dd>{new Date(status.schedule.nextRunAt).getTime() > 0 ? new Date(status.schedule.nextRunAt).toLocaleString("en", { timeZone: "UTC", hour: "2-digit", minute: "2-digit" }) + " UTC" : "UNSCHEDULED"}</dd></div>
    <div><dt>COVERAGE</dt><dd>A {status.coverage.articlePercent.toFixed(0)}% · HN {status.coverage.communityPercent.toFixed(0)}% · PREVIEW {status.coverage.botPreviewPercent.toFixed(0)}%</dd></div>
    <div><dt>SCHEDULE</dt><dd>{status.schedule.human}</dd></div>
  </dl>
</section>
