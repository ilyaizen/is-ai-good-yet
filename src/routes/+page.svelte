<script lang="ts">
  import type { PageData } from "./$types"
  import { page } from "$app/state"
  import BootVeil from "$lib/components/landing/boot-veil.svelte"
  import PhosphorCrt from "$lib/components/landing/phosphor-crt.svelte"
  import PhosphorScope from "$lib/components/landing/phosphor-scope.svelte"
  import { unlockSound } from "$lib/audio/v12-sound"
  import { useVeil } from "$lib/composables/use-veil.svelte"
  import { v12Effects } from "$lib/state/v12-effects.svelte"

  let { data }: { data: PageData } = $props()

  let dialogOpen = $state(false)
  const stamp = $derived(data.lastCatchUpTimestamp)
  const exportedAt = $derived(stamp !== null && Number.isFinite(stamp) ? new Date(stamp * 1000).toISOString() : null)

  const veil = useVeil()

  function onWindowKeydown(event: KeyboardEvent): void {
    if (event.isTrusted && !event.repeat && !event.ctrlKey && !event.altKey && !event.metaKey) {
      unlockSound()
    }
    if (
      page.url.searchParams.get("controls") !== "1" ||
      veil.showIntro ||
      !v12Effects.fx ||
      dialogOpen ||
      event.defaultPrevented ||
      event.ctrlKey ||
      event.altKey ||
      event.metaKey ||
      event.repeat ||
      event.key.toLowerCase() !== "r"
    ) {
      return
    }
    if (event.target instanceof HTMLElement && event.target.closest("input, textarea, select, [contenteditable], dialog")) {
      return
    }
    event.preventDefault()
    veil.handleReplay()
  }

  function onPointerActivation(event: PointerEvent): void {
    if (!event.isTrusted || !event.isPrimary || event.button !== 0) return
    if ((event.pointerType === "mouse") === (event.type === "pointerdown")) unlockSound()
  }
</script>

<svelte:head>
  <title>Is AI &ldquo;Good&rdquo; Yet?</title>
  <meta
    name="description"
    content="A survey tracking developer sentiment on AI-assisted coding through Hacker News posts."
  />
</svelte:head>

<svelte:window onkeydown={onWindowKeydown} onpointerdown={onPointerActivation} onpointerup={onPointerActivation} />

{#if !veil.isLoading && veil.showIntro}
  {#key veil.replayKey}
    <BootVeil onReveal={veil.handleReveal} onComplete={veil.handleComplete} />
  {/key}
{/if}

<div inert={veil.showIntro || undefined}>
  <PhosphorScope
    {data}
    {exportedAt}
    onReplay={veil.handleReplay}
    replayDisabled={veil.showIntro || dialogOpen}
    onDialogChange={(open) => {
      dialogOpen = open
    }}
  />
</div>

<PhosphorCrt />
