<script lang="ts">
  let {
    children,
    icon,
    showOnHover = false,
    className = "",
    href,
    ...restProps
  }: {
    children: import("svelte").Snippet
    icon: import("svelte").Snippet
    showOnHover?: boolean
    className?: string
    href?: string
    [key: string]: any
  } = $props()
</script>

{#if href}
  <a {href} class={className} {...restProps}>
    <span class="inline-flex items-center gap-1">
      {@render children()}
      <span
        class="shrink-0 flex items-center transition-all duration-250 ease-swift"
        class:opacity-0={showOnHover}
        class:-translate-x-2={showOnHover}
        class:group-hover:opacity-100={showOnHover}
        class:group-hover:translate-x-0={showOnHover}
      >
        {@render icon()}
      </span>
    </span>
  </a>
{:else}
  <button type="button" class={className} {...restProps}>
    <span class="inline-flex items-center gap-1">
      {@render children()}
      <span
        class="shrink-0 flex items-center transition-all duration-250 ease-swift"
        class:opacity-0={showOnHover}
        class:-translate-x-2={showOnHover}
        class:group-hover:opacity-100={showOnHover}
        class:group-hover:translate-x-0={showOnHover}
      >
        {@render icon()}
      </span>
    </span>
  </button>
{/if}
