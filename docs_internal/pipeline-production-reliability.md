# Pipeline production preflight and residential HTML fallback

## Failure model

The admin runner now distinguishes source code, mutable storage, and runtime dependencies:

- `PIPELINE_SOURCE_DIR` — Python package directory, normally `/app/pipeline`.
- `PIPELINE_DATA_DIR` — mutable pipeline data volume.
- `PIPELINE_DB_PATH` — exact shared SQLite file used by Node and Python.
- `PIPELINE_PYTHON` — production interpreter, normally `/opt/pipeline-venv/bin/python`.

Do not derive source paths from storage mounts. Node passes the resolved data and DB paths into every Python subprocess.

`python -m src.preflight --json` checks actual imports, Chromium availability, writable storage, the Groq key, and optional residential configuration. Admin commands are disabled server-side and in the UI when their own prerequisites fail.

## V1/V2 command isolation

`/admin` exposes the legacy V1 catch-up and V1 analysis commands. `/v2/admin` does not expose them. Its shared commands stop at ingestion, HN resolution, and article scraping; V2 prefilter, comment collection, analysis, orchestration, and export remain isolated.

## Article text fallback chain

```text
curl_cffi Chrome impersonation
  -> local Playwright rendered HTML
  -> optional authenticated residential Playwright rendered HTML
  -> archive fallback
```

All successful HTML enters the existing Trafilatura/Newspaper/Simple extraction chain. Screenshots are not used for article text.

The direct HTTP layer enforces:

- public HTTP(S) targets only;
- redirect target validation;
- HTML/XHTML content types;
- streamed byte caps;
- bounded timeouts and redirects;
- query string and credential redaction in diagnostics.

The residential client is optional and degrades to archive fallback when unreachable. It never logs or returns its shared secret.

## Residential node

On the residential machine:

```bash
cd pipeline
python -m venv .venv
. .venv/bin/activate                    # Linux/macOS
# .venv\Scripts\activate               # Windows
pip install -r requirements-residential.txt
python -m playwright install chromium
export RESIDENTIAL_FETCHER_SECRET="replace-with-a-long-random-secret"
python residential_fetcher.py
```

Run the service only over a private Tailscale address or a firewall-restricted interface. The service still requires `X-Fetcher-Secret`; an unset secret makes `/fetch` unavailable.

Production application variables:

```bash
PIPELINE_RESIDENTIAL_FETCHER_URL=http://100.x.y.z:8765
PIPELINE_RESIDENTIAL_FETCHER_SECRET=replace-with-the-same-secret
PIPELINE_RESIDENTIAL_FETCHER_TIMEOUT=45
PIPELINE_MAX_HTML_BYTES=2097152
```

Health check:

```bash
curl http://100.x.y.z:8765/health
```

The service uses one persistent headful Chromium process, one fresh context per request, and a one-request semaphore. Initial URLs, navigations, redirects, and HTTP(S) subresources are checked against private/loopback/link-local/reserved address ranges.

## Coolify/Nixpacks

Python extension wheels such as `greenlet` require `libstdc++.so.6`. `nixpacks.toml` exposes `stdenv.cc.cc.lib` through `nixLibs`; merely installing `gcc-unwrapped` does not guarantee the runtime loader can find the library.

After redeploy, inspect the admin preflight or run:

```bash
cd /app/pipeline
/opt/pipeline-venv/bin/python -m src.preflight
```

The scraper check must report successful imports and a real Chromium executable before the Scrape command becomes runnable.
