<script lang="ts">
  import type { PageData } from "./$types"
  import ContentTable from "$lib/components/content-table.svelte"
  import StatCard from "$lib/components/stat-card.svelte"
  import TerminalCard from "$lib/components/terminal-card.svelte"
  import { ArrowLeft, FileText } from "lucide-svelte"
  import { Button } from "$lib/components/ui/button"

  let { data }: { data: PageData } = $props()
</script>

<svelte:head>
  <title>Pipeline Control - Is AI Good Yet?</title>
</svelte:head>

<div class="page-container">
  <div class="page-padding">
    <section class="stats-section">
      <div class="section-header">
        <h2>Pipeline Statistics</h2>
        <p>Real-time metrics across all processing stages</p>
      </div>
      <div class="stats-grid">
        <StatCard value={data.stats.totalUrls} label="Total URLs" valueClass="text-muted-foreground" />
        <StatCard value={data.stats.resolved} label="Resolved" valueClass="text-blue-500" />
        <StatCard value={data.stats.scraped} label="Scraped" valueClass="text-primary" />
        <StatCard value={data.stats.relevant} label="Relevant" valueClass="text-fuchsia-500" />
        <StatCard value={data.stats.analyzed} label="Analyzed" valueClass="text-orange-500" />
        <StatCard value={data.stats.failed} label="Failed" valueClass="text-red-500" />
      </div>
    </section>

    <section class="table-section">
      <div class="section-header">
        <h2>Data Registry</h2>
        <p>Browse and manage all processed entries</p>
      </div>
      <ContentTable data={data.tableData} enableDetailLinks={true} title="Data Registry" syncWithUrl={true} />
    </section>

    <section class="links-section">
      <Button href="/summaries" variant="outline" size="lg" class="btn-secondary-glow">
        <FileText size={18} />
        View All Article Summaries
      </Button>
    </section>
  </div>
</div>

<style>
  .page-padding {
    padding-top: 2rem;
    padding-bottom: 4rem;
  }

  .stats-section {
    padding-top: var(--spacing-section);
    padding-bottom: var(--spacing-section);
  }

  .section-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .section-header h2 {
    font-family: var(--font-mono);
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: var(--table-text);
  }

  .section-header p {
    color: var(--table-secondary-text);
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.75rem;
  }

  .table-section {
    padding-bottom: 2rem;
  }

  .links-section {
    display: flex;
    justify-content: center;
    padding-bottom: var(--spacing-section);
  }

  :global(.btn-secondary-glow) {
    background: transparent !important;
    color: var(--color-accent) !important;
    border: 1px solid var(--color-accent) !important;
    font-family: var(--font-mono);
  }

  :global(.btn-secondary-glow:hover) {
    background: color-mix(in srgb, var(--color-accent) 10%, transparent) !important;
    transform: translateY(-2px);
  }
</style>
