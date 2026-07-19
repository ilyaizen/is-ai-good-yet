<script lang="ts">
  import { enhance } from "$app/forms";
  import { page } from "$app/state";

  let { data }: { data: { configured: boolean; next: string } } = $props();
  let password = $state("");
</script>

<svelte:head>
  <title>V2 admin login · Is AI Good Yet?</title>
</svelte:head>

<!-- Same .v2-card object as the rest of the admin — one design language, not a
     separate "gate" panel. The shell bar (in +layout.svelte) is hidden until
     authenticated, so this stands alone as a centered card. -->
<div class="v2-login">
  <section class="v2-card v2-login__card">
    <header class="v2-card__head">
      <p class="v2-card__kicker">Admin</p>
      <div class="v2-card__head-row">
        <div>
          <h1 class="v2-card__title v2-card__title--hero">Unlock the pipeline</h1>
          <p class="v2-card__lede">One password. No accounts, no roles, no ceremony.</p>
        </div>
      </div>
    </header>

    <div class="v2-login__body">
      {#if !data.configured}
        <p class="v2-login__warn">
          <code>PIPELINE_ADMIN_PASSWORD</code> is missing. Set it before using the admin page.
        </p>
      {/if}

      <form method="post" class="v2-login__form" use:enhance>
        <input type="hidden" name="next" value={data.next} />
        <label class="v2-login__field">
          <span class="v2-login__label">Password</span>
          <input
            bind:value={password}
            name="password"
            type="password"
            autocomplete="current-password"
            class="v2-login__input"
            placeholder="Enter admin password"
          />
        </label>

        {#if page.form?.message}
          <p class="v2-login__error">{page.form.message}</p>
        {/if}

        <button type="submit" class="v2-login__submit" disabled={!data.configured}>
          Enter
        </button>
      </form>

      <nav class="v2-login__nav">
        <a href="/v2">← /v2</a>
        <a href="/v2/admin">← /v2/admin</a>
      </nav>
    </div>
  </section>
</div>

<style>
  .v2-login {
    min-height: 70vh;
    display: grid;
    place-items: center;
    padding: 2rem 1rem;
  }
  .v2-login__card {
    width: 100%;
    max-width: 28rem;
  }
  .v2-login__body {
    padding: clamp(1.5rem, 4vw, 2.5rem);
  }
  .v2-login__warn {
    margin: 0 0 1.25rem;
    padding: 0.75rem 1rem;
    border: 1px solid color-mix(in oklch, var(--v2-amber) 45%, transparent);
    border-radius: 0.4rem;
    color: var(--v2-amber);
    font-size: 0.8rem;
    line-height: 1.5;
  }
  .v2-login__warn code {
    font-family: ui-monospace, monospace;
  }
  .v2-login__form {
    display: grid;
    gap: 1rem;
  }
  .v2-login__field {
    display: grid;
    gap: 0.5rem;
  }
  .v2-login__label {
    color: var(--v2-text);
    font-size: 0.8rem;
  }
  .v2-login__input {
    width: 100%;
    padding: 0.7rem 1rem;
    border: 1px solid var(--v2-separator);
    border-radius: 0.4rem;
    background: var(--v2-recess);
    color: var(--v2-text);
    font:
      0.85rem ui-monospace,
      monospace;
    outline: none;
    transition:
      border-color 0.15s ease,
      box-shadow 0.15s ease;
  }
  .v2-login__input::placeholder {
    color: var(--v2-text-faint);
  }
  .v2-login__input:focus {
    border-color: var(--v2-phosphor);
    box-shadow: 0 0 0 2px color-mix(in oklch, var(--v2-phosphor) 35%, transparent);
  }
  .v2-login__error {
    color: var(--v2-red);
    font-size: 0.8rem;
  }
  .v2-login__submit {
    justify-self: start;
    padding: 0.65rem 1.5rem;
    border: 0;
    border-radius: 0.4rem;
    background: var(--v2-phosphor);
    color: var(--v2-canvas);
    font:
      500 0.82rem ui-monospace,
      monospace;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .v2-login__submit:hover:not(:disabled) {
    background: color-mix(in oklch, var(--v2-phosphor) 85%, var(--v2-canvas));
  }
  .v2-login__submit:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .v2-login__nav {
    display: flex;
    gap: 1rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--v2-separator-quiet);
    color: var(--v2-text-faint);
    font-size: 0.72rem;
  }
  .v2-login__nav a:hover {
    color: var(--v2-phosphor);
  }
</style>
