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
  <div class="w-full rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-sm sm:p-8">
    <p class="mb-3 text-xs uppercase tracking-[0.3em] text-white/45">Admin</p>
    <h1 class="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Unlock the pipeline</h1>
    <p class="mt-3 text-sm leading-6 text-white/65">
      One password. No accounts, no roles, no ceremony.
    </p>

    {#if !data.configured}
      <div class="mt-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
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
        <span class="mb-2 block text-sm font-medium text-white/80">Password</span>
        <input
          bind:value={password}
          name="password"
          type="password"
          autocomplete="current-password"
          class="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none ring-0 transition focus:border-white/25 focus:bg-black/40"
          placeholder="Enter admin password"
        />
      </label>

      {#if page.form?.message}
        <p class="text-sm text-red-300">{page.form.message}</p>
      {/if}

      <button
        type="submit"
        class="inline-flex items-center justify-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={!data.configured}
      >
        Enter
      </button>
    </form>
  </div>
</div>
