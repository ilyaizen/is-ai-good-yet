<script lang="ts">
  let {
    href,
    children,
    icon,
    showOnHover = true,
    className = "",
    target = "_blank",
    rel = "noopener noreferrer",
    title,
    onclick,
    ...restProps
  }: {
    href: string
    children: import("svelte").Snippet
    icon?: import("svelte").Snippet
    showOnHover?: boolean
    className?: string
    target?: string
    rel?: string
    title?: string
    onclick?: (e: MouseEvent) => void
    [key: string]: any
  } = $props()

  let isHovered = $state(false)
</script>

<a
  {href}
  {target}
  {rel}
  {title}
  {onclick}
  class="inline-flex items-center gap-1 cursor-pointer {className}"
  onmouseenter={() => (isHovered = true)}
  onmouseleave={() => (isHovered = false)}
  {...restProps}
>
  <span class="overflow-hidden text-ellipsis whitespace-nowrap">
    {@render children()}
  </span>
  {#if icon}
    <span
      class="shrink-0 flex items-center overflow-hidden transition-all duration-250 ease-swift"
      class:w-0={showOnHover && !isHovered}
      class:w-auto={!showOnHover || isHovered}
      class:opacity-0={showOnHover && !isHovered}
      class:opacity-100={!showOnHover || isHovered}
      class:-translate-x-2={showOnHover && !isHovered}
      class:translate-x-0={!showOnHover || isHovered}
    >
      {@render icon()}
    </span>
  {/if}
</a>
