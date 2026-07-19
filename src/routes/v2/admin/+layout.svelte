<script lang="ts">
  import { enhance } from "$app/forms";
  import type { Snippet } from "svelte";

  let { data, children }: { data: { authenticated: boolean }; children: Snippet } = $props();
</script>

<!--
  Persistent admin shell: brand + cross-admin nav + logout. Rendered only when
  authenticated, so the login gate stands alone. This pulls nav out of the
  observatory hero card, where it had been crammed into the same slot the
  methodology card uses for a version chip.
-->
{#if data.authenticated}
  <header class="v2-admin-bar">
    <div class="v2-admin-bar__inner">
      <a class="v2-admin-bar__brand" href="/v2/admin">
        <span class="v2-admin-bar__mark" aria-hidden="true">◢</span>
        <span class="v2-admin-bar__label">V2 operations</span>
      </a>
      <nav class="v2-admin-bar__nav">
        <a href="/v2">Public dashboard</a>
        <a href="/admin">V1 admin</a>
        <span class="v2-admin-bar__sep" aria-hidden="true"></span>
        <form method="post" action="?/logout" class="v2-admin-bar__logout" use:enhance>
          <button type="submit">Log out</button>
        </form>
      </nav>
    </div>
  </header>
{/if}

{@render children()}

<style>
  .v2-admin-bar {
    position: sticky;
    top: 0;
    z-index: 20;
    border-bottom: 1px solid var(--v2-separator);
    background: color-mix(in srgb, var(--v2-canvas) 88%, transparent);
    backdrop-filter: blur(8px);
  }
  .v2-admin-bar__inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    max-width: 96rem;
    margin: 0 auto;
    padding: 0.65rem 1rem;
  }
  @media (min-width: 640px) {
    .v2-admin-bar__inner {
      padding: 0.65rem 1.5rem;
    }
  }
  @media (min-width: 1024px) {
    .v2-admin-bar__inner {
      padding: 0.65rem 2rem;
    }
  }
  .v2-admin-bar__brand {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--v2-text);
    text-decoration: none;
  }
  .v2-admin-bar__mark {
    color: var(--v2-phosphor);
    font-size: 0.85rem;
    line-height: 1;
  }
  .v2-admin-bar__label {
    font:
      500 0.72rem ui-monospace,
      monospace;
    letter-spacing: 0.04em;
  }
  .v2-admin-bar__nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .v2-admin-bar__nav a,
  .v2-admin-bar__logout button {
    border: 1px solid var(--v2-separator);
    border-radius: 0.4rem;
    background: color-mix(in srgb, var(--v2-text) 3%, transparent);
    padding: 0.4rem 0.7rem;
    color: var(--v2-text-muted);
    font-size: 0.72rem;
    text-decoration: none;
    transition: 0.15s ease;
  }
  .v2-admin-bar__nav a:hover,
  .v2-admin-bar__logout button:hover {
    border-color: var(--v2-phosphor);
    color: var(--v2-text);
  }
  .v2-admin-bar__sep {
    width: 1px;
    height: 1.1rem;
    margin: 0 0.15rem;
    background: var(--v2-separator-quiet);
  }
  .v2-admin-bar__logout {
    margin: 0;
  }
</style>
