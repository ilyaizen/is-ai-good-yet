<script lang="ts">
  import { enhance } from "$app/forms"
  import { page } from "$app/state"

  let { data }: { data: { configured: boolean; next: string } } = $props()
  let password = $state("")
</script>

<svelte:head>
  <title>Admin login - Is AI Good Yet?</title>
</svelte:head>

<div class="mx-auto flex min-h-[70vh] max-w-xl items-center px-4 py-12 sm:px-6">
  <div class="terminal-panel w-full p-6 sm:p-8">
    <p class="mb-3 text-xs uppercase tracking-[0.3em] text-terminal-text-faint">Admin</p>
    <h1 class="text-3xl font-semibold tracking-tight text-terminal-text sm:text-4xl">Unlock the pipeline</h1>
    <p class="mt-3 text-sm leading-6 text-terminal-text-muted">
      One password. No accounts, no roles, no ceremony.
    </p>

    {#if !data.configured}
      <div class="mt-6 border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-800 dark:text-amber-100">
        `PIPELINE_ADMIN_PASSWORD` is missing. Set it before using the admin page.
      </div>
    {/if}

    <form
      method="post"
      class="mt-6 space-y-4"
      use:enhance
    >
      <input type="hidden" name="next" value={data.next} />
      <label class="block">
        <span class="mb-2 block text-sm font-medium text-terminal-text">Password</span>
        <input
          bind:value={password}
          name="password"
          type="password"
          autocomplete="current-password"
          class="terminal-input"
          placeholder="Enter admin password"
        />
      </label>

      {#if page.form?.message}
        <p class="text-sm text-rose-700 dark:text-rose-300">{page.form.message}</p>
      {/if}

      <button
        type="submit"
        class="terminal-action px-5 py-3 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={!data.configured}
      >
        Enter
      </button>
    </form>
  </div>
</div>
