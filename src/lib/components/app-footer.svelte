<script lang="ts">
  import { ExternalLink } from "@lucide/svelte"
  import VisitorCounter from "./visitor-counter.svelte"
  // import { Tooltip, TooltipContent, TooltipTrigger } from "$lib/components/ui/tooltip"
</script>

<footer class="site-footer">
  <div class="footer-inner max-w-5xl mx-auto w-full">
    <div class="footer-top">
      <div class="footer-about">
        <p class="footer-brand font-mono font-bold">Is AI <span class="highlight">“Good”</span> Yet?</p>
        <p class="footer-description">
          A survey tracking developer sentiment on AI-assisted coding through Hacker News posts.
        </p>
        <p class="footer-description pt-2">
          This page was visited <VisitorCounter /> times.
        </p>
      </div>

      <nav class="footer-links" aria-label="Footer navigation">
        <div class="footer-links-group">
          <span class="footer-links-label">Navigate</span>
          <a href="#home">Home</a>
          <a href="#details">Details</a>
          <a href="#articles-table">Articles</a>
        </div>
        <div class="footer-links-group">
          <span class="footer-links-label">links</span>
          <a href="https://github.com/ilyaizen/is-ai-good-yet" target="_blank" rel="noopener noreferrer">
            GitHub
            <ExternalLink size={12} />
          </a>
          <a href="https://hcker.news/" target="_blank" rel="noopener noreferrer">
            Hcker.news
            <ExternalLink size={12} />
          </a>
          <a href="https://news.ycombinator.com/item?id=46851589" target="_blank" rel="noopener noreferrer">
            Original post
            <ExternalLink size={12} />
          </a>
        </div>
      </nav>
    </div>
  </div>
  <div class="font-mono text-xs flex justify-center items-center">
    <span class="copyright">Is AI “Good” Yet? © {new Date().getFullYear()}</span>
  </div>
</footer>

<style>
  .site-footer {
    border-top: 1px solid oklch(from var(--primary) l c h / 0.3);
    background-color: var(--card);
    margin-top: 4rem;
    margin-left: calc(-50vw + 50%);
    margin-right: calc(-50vw + 50%);
    padding-left: calc(50vw - 50%);
    padding-right: calc(50vw - 50%);
    padding-bottom: 1.5rem;
  }

  .footer-inner {
    padding: 2.5rem 1.5rem 1.5rem;
    max-width: 64rem;
    margin-left: auto;
    margin-right: auto;
  }

  .footer-top {
    display: flex;
    justify-content: space-between;
    gap: 3rem;
  }

  .footer-about {
    max-width: 26rem;
  }

  .footer-brand {
    font-size: 1rem;
    color: var(--color-foreground);
    margin-bottom: 0.5rem;
  }

  .footer-description {
    font-size: 0.875rem;
    line-height: 1.5;
    color: var(--color-muted-foreground);
  }

  .footer-links {
    display: flex;
    gap: 3rem;
  }

  .footer-links-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .footer-links-label {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-foreground);
    margin-bottom: 0.25rem;
  }

  .footer-links-group a {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.875rem;
    color: var(--color-muted-foreground);
    text-decoration: none;
    transition: color 0.15s ease;
  }

  .footer-links-group a:hover {
    color: var(--color-primary);
  }

  /* Tablet */
  @media (max-width: 640px) {
    .footer-top {
      flex-direction: column;
      gap: 2rem;
    }

    .footer-about {
    }

    .footer-links {
      gap: 2rem;
    }
  }
</style>
