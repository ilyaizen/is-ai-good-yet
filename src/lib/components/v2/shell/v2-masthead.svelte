<script lang="ts">
  interface Props { settingsOpen: boolean; onSettings: () => void; }
  let { settingsOpen, onSettings }: Props = $props();
  let menuOpen = $state(false);
</script>

<header class="v2-masthead">
  <a class="v2-brand" href="/v2" aria-label="Is AI Good Yet home">is-ai-good-yet.com <span aria-hidden="true">█</span></a>
  <p>ALL AI DOMAINS</p>
  <button class="v2-menu" type="button" aria-expanded={menuOpen} aria-controls="v2-navigation" onclick={() => menuOpen = !menuOpen}>[ MENU ]</button>
  <nav id="v2-navigation" class:v2-nav--open={menuOpen} aria-label="V2 sections">
    <a href="#feed">FEED</a>
    <a href="#evidence">HN EVIDENCE</a>
    <a href="#history">HISTORY</a>
    <a href="#method">METHOD</a>
    <button type="button" aria-expanded={settingsOpen} aria-controls="v2-display-control" onclick={onSettings}>[ CTRL ]</button>
  </nav>
</header>
