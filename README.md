# The Is AI “Good” Yet? Project

_**HN on AI-Assisted Development and "Vibe-Coding": The Sentiment Analysis**_

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![SvelteKit](https://img.shields.io/badge/sveltekit-v2-orange)
![License](https://img.shields.io/badge/license-MIT-green)

TLDR; This little project analyzes HN’s hivemind to answer which camp is currently louder, the “AI-Good” or “AI-Bad” one?

Using a pipeline to scrape and analyze the sentiment of 1000+ AI-related articles submitted to Hacker News over the past 3 years, it tries to objectively determine how developers actually feel about AI-assisted development and “vibe-coding” in 2026.

"Does Claude Code make you a worse programmer?" or "Is vibe-coding everything worth the technical debt?" I scraped, cleaned, and analyzed all AI-related articles posted on HN in the past three years (about 6,000 articles after filtering) using a multi-step Python pipeline for the scraping and analysis, and built a SvelteKit frontend dashboard to nicely display the results. The goal was to spot the overall trend in Hacker News discourse, whether practitioners genuinely see value in AI coding workflows today and if they think that value will grow. It's a meme site, and yes, I know sentiment analysis might seem pointless.

---

### 3. Run the Frontend

```bash
cd is-ai-good-yet
bun run dev
```

Open [http://localhost:5173](http://localhost:5173) to view the dashboard.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.
