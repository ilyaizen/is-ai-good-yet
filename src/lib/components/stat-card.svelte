<script lang="ts">
  import { cn } from "$lib/utils"

  interface Props {
    value: string | number
    label: string
    class?: string
    valueClass?: string
  }

  let { value, label, class: className = "", valueClass = "" }: Props = $props()

  const displayValue = $derived(typeof value === "number" ? value.toLocaleString() : value)
</script>

<div class={cn("stat-card", className)}>
  <div class={cn("stat-value", valueClass)}>{displayValue}</div>
  <div class="stat-label">{label}</div>
</div>

<style>
  .stat-card {
    background: var(--card);
    padding: 1.25rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    transition:
      transform var(--transition-normal),
      border-color var(--transition-normal);
  }

  .stat-card:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
  }

  .stat-value {
    font-family: var(--font-mono);
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .stat-label {
    color: var(--muted-foreground);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: 0.75rem;
    font-weight: 600;
  }
</style>
