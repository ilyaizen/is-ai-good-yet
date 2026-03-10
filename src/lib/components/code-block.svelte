<script lang="ts">
  import { Copy, Check } from "@lucide/svelte"
  import type { Snippet } from "svelte"

  interface Props {
    code: string
    class?: string
    children?: Snippet
  }

  let { code, class: className = "", children }: Props = $props()

  let copied = $state(false)

  async function copyCode() {
    await navigator.clipboard.writeText(code)
    copied = true
    setTimeout(() => {
      copied = false
    }, 2000)
  }
</script>

<div class="code-block {className}">
  <button class="code-copy-btn" class:copied onclick={copyCode} aria-label="Copy code">
    {#if copied}
      <Check size={14} />
      Copied
    {:else}
      <Copy size={14} />
      Copy
    {/if}
  </button>
  <pre><code
      >{#if children}{@render children()}{:else}{code}{/if}</code
    ></pre>
</div>

<style>
  .code-block {
    background: #0d0d0d;
    border-radius: var(--radius-md);
    padding: 1rem;
    border: 1px solid var(--color-border);
    position: relative;
    margin: 1.5rem 0;
    overflow: hidden;
    transition: border-color var(--transition-fast);
  }

  .code-block:focus-within {
    border-color: var(--color-primary);
    box-shadow: 0 0 15px color-mix(in srgb, var(--color-primary), transparent 90%);
  }

  pre {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 0.9rem;
    color: #d4d4d8;
    white-space: pre-wrap;
  }

  .code-copy-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: var(--color-text-muted);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: 4px;
    transition: all var(--transition-fast);
  }

  .code-copy-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: var(--color-text-primary);
  }

  .code-copy-btn.copied {
    color: var(--color-primary);
    background: color-mix(in srgb, var(--color-primary), transparent 90%);
  }
</style>
