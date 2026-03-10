<script lang="ts">
  import { ChevronRight } from "@lucide/svelte"

  let {
    onclick,
    label,
    icon: Icon = ChevronRight,
    iconProps = {},
    iconClass = "",
    class: className = "",
    ref = $bindable(),
    type = "button" as "button" | "submit" | "reset",
    hovered = $bindable(false),
    focused = $bindable(false),
  }: {
    onclick?: (e?: MouseEvent | KeyboardEvent) => void
    label: string
    icon?: any
    iconProps?: Record<string, any>
    iconClass?: string
    class?: string
    ref?: HTMLButtonElement | null
    type?: "button" | "submit" | "reset"
    hovered?: boolean
    focused?: boolean
  } = $props()

  function handleWindowKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && (hovered || focused) && onclick) {
      // Prevent default to avoid double-submission or scroll
      e.preventDefault()
      onclick(e)
    }
  }
</script>

<svelte:window onkeydown={handleWindowKeydown} />

<button
  {type}
  bind:this={ref}
  class="reveal-btn relative justify-center sm:justify-start {className}"
  class:focused
  class:hovered
  {onclick}
  onmouseenter={() => {
    focused = false
    hovered = true
  }}
  onmouseleave={() => (hovered = false)}
  onfocus={() => (focused = true)}
  onblur={() => (focused = false)}>
  <span>{label}</span>
  {#if hovered || focused}
    <Icon size={16} class="reveal-arrow {iconClass || ''}" {...iconProps} style={iconProps.style || ""} />
  {/if}
</button>
