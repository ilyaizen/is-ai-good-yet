<script lang="ts">
  import SunIcon from "@lucide/svelte/icons/sun"
  import MoonIcon from "@lucide/svelte/icons/moon"
  import { toggleMode } from "mode-watcher"
  import { Button } from "$lib/components/ui/button"
</script>

<Button onclick={toggleMode} variant="outline" size="icon" aria-label="Toggle theme" class="theme-toggle">
  <SunIcon class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all! dark:scale-0 dark:-rotate-90" />
  <MoonIcon class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all! dark:scale-100 dark:rotate-0" />
  <span class="sr-only">Toggle theme</span>
</Button>

<style>
  :global(.theme-toggle) {
    background: transparent;
    border: 1px solid var(--color-border);
    color: var(--color-text-primary);
  }

  :global(.theme-toggle:hover) {
    background: var(--color-surface-hover);
  }
</style>
