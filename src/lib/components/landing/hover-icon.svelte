<script lang="ts">
  let {
    icon,
    showOnHover = true,
    className = "",
  }: {
    icon: import("svelte").Snippet
    showOnHover?: boolean
    className?: string
  } = $props()
</script>

<span
  class="shrink-0 flex items-center transition-all duration-250 ease-swift {className}"
  class:opacity-0={showOnHover}
  class:-translate-x-2={showOnHover}
  class:group-hover:opacity-100={showOnHover}
  class:group-hover:translate-x-0={showOnHover}
>
  {@render icon()}
</span>
