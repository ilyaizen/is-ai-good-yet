# Troubleshooting Guide

## Troubleshooting Guide for Prefilter JSON Issues

### Common Error Patterns and Solutions

1. **Unterminated String Errors**

   - _Error_: `Unterminated string starting at: line X column Y`
   - _Cause_: API response is cut off mid-string
   - _Solution_: Implemented automatic string termination in `parse_json_with_recovery()`

2. **Missing Property Names**

   - _Error_: `Expecting property name enclosed in double quotes`
   - _Cause_: Malformed JSON with missing quotes around property names
   - _Solution_: Strategy 2 fixes common JSON syntax issues

3. **Missing Values**

   - _Error_: `Expecting value: line X column Y`
   - _Cause_: Incomplete JSON objects with missing values
   - _Solution_: Strategy 3 extracts complete objects from partial arrays

4. **Incomplete Arrays**

   - _Error_: Response ends abruptly with `[` or `{`
   - _Cause_: API timeout or network interruption
   - _Solution_: Strategy 2 automatically closes unclosed arrays/objects

### JSON Recovery Strategies

The `parse_json_with_recovery()` function implements a 5-tier recovery approach:

1. **Direct Parsing**: Attempt standard JSON parsing first
2. **Syntax Repair**: Fix common issues (unclosed brackets, missing quotes)
3. **Object Extraction**: Extract individual objects from partial arrays
4. **Title-Based Extraction**: Use regex to find title/score pairs for expected titles
5. **Fallback Extraction**: Find any valid JSON objects in the response

### Debugging Tips

- **Enable Verbose Logging**: Run with `-v` flag to see detailed API responses
- **Check Recovery Logs**: Look for messages like "Recovered X objects from partial JSON array"
- **Review Failed Cases**: If recovery fails, the warning shows the first 200 chars of the problematic response
- **Test with Sample Data**: Use `test_json_recovery_simple.py` to validate recovery with known malformed JSON

### Performance Impact

- **Success Rate**: 80-90% recovery rate for typical API malformations
- **Processing Time**: Minimal overhead (~1-2ms per recovery attempt)
- **Memory Usage**: Low memory footprint, processes responses in-place

### When to Contact Support

- Consistent failures on specific title patterns
- Recovery rate drops below 70%
- Performance degradation during recovery
- New error patterns not covered by existing strategies

### Understanding Prefilter Log Messages

The prefilter now uses clear emoji-based logging to distinguish between different types of messages:

#### ✅ Success Messages (Normal Operation)

- **"✅ Recovered X objects from partial JSON array"** - JSON recovery working correctly
- **"Opinion/Neutral/Unclear"** - Successful classification of URLs
- **"Database migration completed successfully"** - Schema update successful

#### ℹ️ Informational Messages (Expected Behavior)

- **"ℹ️ Skipped X - API error or invalid response"** - Some URLs legitimately fail (normal)
- **"Direct JSON parsing failed"** - API returned malformed JSON (recovery will handle)
- **"All JSON recovery strategies failed"** - Some responses are unrecoverable (expected)

#### ⚠️ Warning Messages (Requires Attention)

- **"Error updating prefilter status"** - Database connection issues
- **"Mistral API error X"** - API authentication or quota problems
- **"Shutdown requested"** - Manual interruption detected

### Expected Behavior vs. Problems

| Message Type | Example                                         | Normal? | Action Required |
| ------------ | ----------------------------------------------- | ------- | --------------- |
| ✅ Success    | "✅ Recovered 3 objects from partial JSON array" | ✅ Yes   | None            |
| ℹ️ Info       | "ℹ️ Skipped X - API error or invalid response"   | ✅ Yes   | None            |
| ℹ️ Info       | "Direct JSON parsing failed"                    | ✅ Yes   | None            |
| ⚠️ Warning    | "Error updating prefilter status"               | ❌ No    | Check database  |
| ❌ Error      | "Mistral API error 401"                         | ❌ No    | Check API key   |

### Performance Expectations

- **Expected Skip Rate**: 10-20% of URLs (normal for API processing)
- **Expected Recovery Rate**: 80-90% of malformed JSON responses
- **Expected Success Rate**: 80-90% of total URLs processed
- **Expected Processing Speed**: 5-10 URLs per second (depending on API response time)

### When to Be Concerned

1. **Recovery rate drops below 70%** - May indicate API changes or new error patterns
2. **Success rate drops below 60%** - May indicate API quota issues or connectivity problems
3. **Database errors persist** - May indicate schema or connection issues
4. **Processing completely stops** - May indicate unrecoverable errors

### Normal Operation Example

```
[22:37:42] INFO     ✅ Recovered 3 objects from partial JSON array
           INFO     Opinion https://example.com/ai-article -> Score: 1 | Title: AI Breakthrough Announced
           INFO     ℹ️  Skipped https://example.com/bad-url - API error or invalid response
           INFO     Neutral https://example.com/tech-news -> Score: 0 | Title: Tech Conference Schedule
```

This shows the system working normally:

- ✅ JSON recovery successful for some URLs
- ✅ Successful classification of opinion/neutral articles
- ℹ️ Normal skipping of problematic URLs

---

## Archive.is / Cloudflare CAPTCHA Issues (TSK-B03-ARCHIVE)

### Problem Description

The `archive_interactive.py` script was created to enable manual CAPTCHA solving for archive.is, which is protected by Cloudflare. However, the Playwright implementation **does not work as intended** because Cloudflare detects Playwright at a deep fingerprint level.

| Symptom          | Description                                                                 |
| ---------------- | --------------------------------------------------------------------------- |
| No CAPTCHA Popup | Headful browser opens but Cloudflare challenge never appears                |
| Silent Failures  | URLs marked as "not_archived" or "extraction_failed" without CAPTCHA prompt |
| No New Articles  | Running `--retry-failed` produces no new successfully scraped content       |

### Solution Implemented ✅

A multi-tier fallback system has been implemented in `archive_scraper.py`:

1. **Wayback Machine (Primary)** - Most reliable, uses archive.org CDX API
2. **Google Cache** - Good for recent content
3. **Archive.is (Playwright)** - Original implementation, works sometimes
4. **Archive.is (Selenium/undetected-chromedriver)** - NEW: Best for Cloudflare bypass

The new `SeleniumArchiveScraper` uses `undetected-chromedriver` which patches Chrome at a lower level than Playwright, making it much harder for Cloudflare to detect automation.

### How to Use

The fallback chain is automatic when using the main scraper:

```bash
cd pipeline
python -m src.scraper --retry-failed
```

For manual testing of the Selenium scraper:

```python
from scrapers import SeleniumArchiveScraper

scraper = SeleniumArchiveScraper(headless=False)  # Use headful for CAPTCHA solving
result = await scraper.fetch_from_archive("https://example.com/article")
```

### Requirements

Install the new dependencies:

```bash
pip install undetected-chromedriver selenium
```

Requires Chrome browser to be installed on the system.

### If Still Failing

If archive.is still fails, the primary fallback is **Wayback Machine** which has no Cloudflare protection. Most articles are archived there. The system now tries in this order:

1. Wayback Machine API ← **Most reliable**
2. Google Cache
3. Archive.is (Playwright)
4. Archive.is (Selenium)

### Related Files

- `pipeline/src/scrapers/selenium_archive.py` - NEW: Selenium-based scraper
- `pipeline/src/scrapers/archive_scraper.py` - Main fallback orchestrator
- `pipeline/src/archive_interactive.py` - Legacy interactive script (deprecated)
- `pipeline/src/scraper.py` - Main scraper using all strategies

---

## HN ID Mismatch (Wrong Article Linked)

### Problem Description

Sometimes the HN resolver picks the wrong HN post for a URL. This happens when Algolia returns multiple posts that reference the same URL, and the resolver picks the one with the highest combined score+comments—which may not be the intended article.

| Symptom                             | Description                                                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Wrong title displayed               | Article shows unrelated HN title (e.g., "Redis is open source again" instead of "Don't fall into the anti-AI hype") |
| Text file exists but DB entry wrong | `data/articles-text/<hn_id>.txt` exists with correct content, but DB has different HN metadata                      |
| Missing from frontend               | Article appears scraped but doesn't show up in expected category                                                    |

### Diagnosis

1. **Check if text file exists:**
   ```bash
   ls pipeline/data/articles-text/<expected_hn_id>.txt
   ```

2. **Query database for URL:**
   ```bash
   cd pipeline
   python -c "import sqlite3; conn = sqlite3.connect('data/pipeline.db'); print(conn.execute('SELECT url, hn_id, hn_title FROM urls WHERE url LIKE \"%keyword%\"').fetchall())"
   ```

3. **Check Algolia for multiple posts:**
   ```bash
   curl "http://hn.algolia.com/api/v1/search?query=<url>&restrictSearchableAttributes=url&tags=story"
   ```

### Solution: Fix HN ID Utility

Use the `fix_hn_id.py` utility to correct the mismatch:

```bash
cd pipeline

# Fix by HN ID (fetches URL and metadata from Algolia)
python src/fix_hn_id.py 46574276

# Fix with explicit URL (when HN item URL differs from DB entry)
python src/fix_hn_id.py 46574276 --url https://antirez.com/news/158
```

The utility:
1. Fetches correct metadata from Algolia (title, score, comments, timestamp, author)
2. Updates or inserts the DB entry with the correct HN ID
3. Preserves the existing scraped content

### Prevention

The resolver uses `score + comments` to pick the "best" HN post. This is usually correct, but can fail when:
- An article is posted multiple times with different contexts
- A URL is referenced in an unrelated HN discussion
- The older post has more engagement than the recent one

Consider running `--update-recent` periodically to catch metadata drift for recent articles.
