<script lang="ts">
  let {
    onReveal,
    articleCount,
    lastUpdateTimestamp,
    resetTrigger = 0
  }: {
    onReveal: () => void;
    articleCount: number;
    lastUpdateTimestamp: number | null;
    resetTrigger?: number;
  } = $props();

  let leaving = $state(false);
  let previousResetTrigger = $state(0);

  const updated = $derived(
    lastUpdateTimestamp
      ? new Date(lastUpdateTimestamp * 1000).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric"
        })
      : "static export"
  );

  function reveal() {
    leaving = true;
    window.setTimeout(onReveal, 220);
  }

  $effect(() => {
    if (resetTrigger > previousResetTrigger) {
      leaving = false;
      previousResetTrigger = resetTrigger;
    }
  });
</script>

<div class="v2-veil" class:v2-veil--leaving={leaving}>
  <div class="v2-veil__noise" aria-hidden="true"></div>
  <section class="v2-veil__terminal" aria-labelledby="v2-veil-title">
    <div class="v2-veil__bar">
      <span>VERDICT TERMINAL / V2</span>
      <span class="v2-veil__status"><i></i> DATA READY</span>
    </div>
    <div class="v2-veil__body">
      <p class="v2-veil__prompt"><span>$</span> ./analyze --source hn --topic "ai coding tools"</p>
      <h1 id="v2-veil-title">IS AI <em>GOOD</em> YET?<span class="v2-cursor"></span></h1>
      <p class="v2-veil__copy">
        An instrument panel for developer sentiment across {articleCount.toLocaleString("en-US")} analyzed Hacker News articles.
        No prophecy. Just the current record.
      </p>
      <dl class="v2-veil__meta">
        <div><dt>SOURCE</dt><dd>HACKER NEWS</dd></div>
        <div><dt>EXPORT</dt><dd>{updated}</dd></div>
        <div><dt>MODE</dt><dd>STATIC / VERIFIED</dd></div>
      </dl>
      <button type="button" onclick={reveal}>RUN ANALYSIS <span aria-hidden="true">↵</span></button>
    </div>
  </section>
</div>
