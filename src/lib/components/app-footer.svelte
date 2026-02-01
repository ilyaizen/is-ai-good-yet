<script lang="ts">
  import { ExternalLink } from "lucide-svelte"
  import VisitorCounter from "./visitor-counter.svelte"
  import { Tooltip, TooltipContent, TooltipTrigger } from "$lib/components/ui/tooltip"
</script>

<footer class="site-footer">
  <div class="footer-inner max-w-5xl mx-auto w-full">
    <div class="footer-top">
      <div class="footer-about">
        <p class="footer-brand font-mono font-bold">is AI <span class="highlight">“good”</span> yet?</p>
        <p class="footer-description">
          a survey tracking developer sentiment on AI-assisted coding through hacker news posts.
        </p>
        <p class="footer-description pt-2">
          made with ❤️ and a single prompt that one-shot this entirely in 25 minutes using
          <Tooltip>
            <TooltipTrigger>
              <a
                href="https://www.molty.me/"
                target="_blank"
                rel="noopener noreferrer"
                class="hover:underline hover:text-primary">
                molty
              </a>.
            </TooltipTrigger>
            <TooltipContent>
              <p>unbelieve huh? lol..</p>
            </TooltipContent>
          </Tooltip> 🦞
        </p>
        <p class="footer-description pt-2">
          thanks for visiting! (#<VisitorCounter />)
        </p>
      </div>

      <nav class="footer-links" aria-label="Footer navigation">
        <div class="footer-links-group">
          <span class="footer-links-label">navigate</span>
          <a href="#home">home</a>
          <a href="#details">details</a>
          <a href="#articles">articles</a>
        </div>
        <div class="footer-links-group">
          <span class="footer-links-label">project</span>
          <a href="https://github.com/ilyaizen/is-ai-good-yet" target="_blank" rel="noopener noreferrer">
            github
            <ExternalLink size={12} />
          </a>
        </div>
      </nav>
    </div>
  </div>
  <div class="font-mono text-xs flex justify-center items-center">
    <span class="copyright">“is AI good yet?” © {new Date().getFullYear()}</span>
  </div>
</footer>

<style>
  .site-footer {
    border-top: 1px solid var(--color);
    background-color: var(--color-background);
    margin-top: 4rem;
  }

  .footer-inner {
    padding: 2.5rem 1.5rem 1.5rem;
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
