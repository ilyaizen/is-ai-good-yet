import { intro, outro, select, multiselect, text, confirm, isCancel } from '@clack/prompts';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';

const PROJECT_ROOT = process.cwd();
const PIPELINE_DIR = path.join(PROJECT_ROOT, 'pipeline');

// Python: check root venv → pipeline venv → system fallback
const candidates = [
  path.join(PROJECT_ROOT, '.venv', 'bin', 'python'),           // root Linux
  path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe'),   // root Windows
  path.join(PIPELINE_DIR, '.venv', 'bin', 'python'),           // pipeline Linux
  path.join(PIPELINE_DIR, '.venv', 'Scripts', 'python.exe'),   // pipeline Windows
  path.join(PIPELINE_DIR, 'venv', 'bin', 'python'),            // pipeline legacy Linux
  path.join(PIPELINE_DIR, 'venv', 'Scripts', 'python.exe'),    // pipeline legacy Windows
];
const pythonCmd = candidates.find(p => fs.existsSync(p)) ?? 'python3';
const venvReady = candidates.some(p => fs.existsSync(p));

async function runScript(command: string, args: string[], cwd: string = PROJECT_ROOT): Promise<boolean> {
  return new Promise<boolean>((resolve) => {
    console.log(`\n> Executing: ${command} ${args.join(' ')}\n`);

    const child = spawn(command, args, {
      cwd,
      stdio: 'inherit',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
    });

    let interrupted = false;
    const sigintHandler = () => {
      if (!interrupted) {
        interrupted = true;
        console.log('\n> Interrupting...');
        if (process.platform === 'win32') {
          spawn('taskkill', ['/pid', String(child.pid), '/t', '/f'], { shell: true });
        } else {
          child.kill('SIGINT');
        }
      }
    };

    process.on('SIGINT', sigintHandler);
    child.on('close', (code) => {
      process.removeListener('SIGINT', sigintHandler);
      if (interrupted) console.log('> Process interrupted.');
      resolve(!interrupted && code === 0);
    });
    child.on('error', (err) => {
      process.removeListener('SIGINT', sigintHandler);
      console.error(`> Error: ${err.message}`);
      resolve(false);
    });
  });
}

async function bumpVersion(defaultType: 'patch' | 'minor' | 'major' = 'patch'): Promise<void> {
  const bumpType = await select({
    message: 'Version bump type:',
    options: [
      { value: 'patch', label: 'Patch (0.0.x)', hint: defaultType === 'patch' ? 'Recommended' : 'Data update' },
      { value: 'minor', label: 'Minor (0.x.0)', hint: defaultType === 'minor' ? 'Recommended' : 'New features' },
      { value: 'major', label: 'Major (x.0.0)', hint: defaultType === 'major' ? 'Recommended' : 'Breaking changes' }
    ]
  });
  if (!isCancel(bumpType)) {
    await runScript('node', ['scripts/bump-version.mjs', bumpType as string]);
  }
}

async function configureBackfillArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Backfill mode?',
    options: [
      { value: 'default', label: 'Recent pages (1-10)', hint: 'Most recent HN posts' },
      { value: 'resume', label: 'Resume from last state', hint: 'Continue where left off' },
      { value: 'custom', label: 'Configure', hint: 'Set start/end pages' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['--end', '10'];
  if (mode === 'resume') return ['--resume'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [{ value: '--resume', label: 'Resume (--resume)', hint: 'Continue from last saved page' }],
    initialValues: [] as string[],
    required: false
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  const startPage = await text({ message: 'Start page:', defaultValue: '1', placeholder: '1' });
  if (isCancel(startPage)) throw new Error('Operation cancelled');
  if (startPage && String(startPage).trim()) args.push('--start', String(startPage));

  const endPage = await text({ message: 'End page:', defaultValue: '10', placeholder: '10' });
  if (isCancel(endPage)) throw new Error('Operation cancelled');
  if (endPage && String(endPage).trim()) args.push('--end', String(endPage));

  const output = await text({ message: 'Output file:', defaultValue: 'data/histre_feed.json', placeholder: 'data/histre_feed.json' });
  if (isCancel(output)) throw new Error('Operation cancelled');
  if (output && String(output).trim()) args.push('--output', String(output));

  const recent = await text({ message: 'Recent output file (optional):', defaultValue: '', placeholder: 'data/recent_links.json' });
  if (isCancel(recent)) throw new Error('Operation cancelled');
  if (recent && String(recent).trim()) args.push('--recent', String(recent));

  return args;
}

async function configureResolverArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Resolver mode?',
    options: [
      { value: 'default', label: 'Default', hint: 'Standard run for new URLs' },
      { value: 'update-recent', label: 'Update Recent', hint: 'Refresh score/comments (30 days)' },
      { value: 'custom', label: 'Configure', hint: 'Flags, limits, etc.' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return [];
  if (mode === 'update-recent') return ['-v', '--update-recent'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '-f', label: 'Force (-f)', hint: 'Reprocess all URLs' },
      { value: '-r', label: 'Retry (-r)', hint: 'Retry failed/no-match URLs' },
      { value: '-m', label: 'Missing (-m)', hint: 'Reprocess missing metadata' },
      { value: '-u', label: 'Update Recent (-u)', hint: 'Refresh score/comments' }
    ],
    initialValues: [] as string[]
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  if (Array.isArray(flags) && (flags as string[]).includes('-u')) {
    const recentDays = await text({ message: 'Recent days:', defaultValue: '30', placeholder: '30' });
    if (isCancel(recentDays)) throw new Error('Operation cancelled');
    if (recentDays && String(recentDays).trim() !== '30') args.push('--recent-days', String(recentDays));
  }

  const limit = await text({ message: 'Limit (0 = all):', defaultValue: '0', placeholder: '0' });
  if (isCancel(limit)) throw new Error('Operation cancelled');
  if (limit && String(limit).trim()) args.push('-l', String(limit));

  const batchSize = await text({ message: 'Batch size:', defaultValue: '50', placeholder: '50' });
  if (isCancel(batchSize)) throw new Error('Operation cancelled');
  if (batchSize && String(batchSize).trim()) args.push('-b', String(batchSize));

  const rateLimit = await text({ message: 'Rate limit (req/s):', defaultValue: '5.0', placeholder: '5.0' });
  if (isCancel(rateLimit)) throw new Error('Operation cancelled');
  if (rateLimit && String(rateLimit).trim()) args.push('--rate-limit', String(rateLimit));

  return args;
}

async function configureScraperArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Scraper mode?',
    options: [
      { value: 'default', label: 'Smart Retry Failed (Recommended)', hint: 'HTTP → browser → archives' },
      { value: 'scrape-new', label: 'Scrape New URLs Only', hint: 'Lean, newest first, Wayback fallback' },
      { value: 'retry-light', label: 'Retry Failed (Light)', hint: 'No Selenium, faster' },
      { value: 'captcha', label: 'CAPTCHA Ready Mode', hint: 'Headful, interactive' },
      { value: 'fast', label: 'Fast Mode', hint: 'High concurrency' },
      { value: 'custom', label: 'Configure', hint: 'Custom flags' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['--lean', '--stealth-mode=seleniumbase', '--retry-failed', '--no-headful-switch', '-b', '80', '-c', '6', '-r', '2.5', '--max-retries', '2'];
  if (mode === 'scrape-new') return ['--lean', '--stealth-mode=seleniumbase', '--no-headful-switch', '-b', '80', '-c', '6', '-r', '2.5'];
  if (mode === 'retry-light') return ['--lean', '--retry-failed', '--stealth-mode=seleniumbase', '--no-headful-switch', '-b', '50', '-c', '4', '-r', '2'];
  if (mode === 'captcha') return ['-v', '--interactive', '--headful', '--stealth-mode=seleniumbase', '--use-selenium'];
  if (mode === 'fast') return ['--lean', '--stealth-mode=seleniumbase', '--no-headful-switch', '-b', '100', '-c', '10', '-r', '5'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--lean', label: 'Lean Mode' },
      { value: '--no-headful-switch', label: 'No Headful Switch', hint: 'Stay headless (recommended)' },
      { value: '--retry-failed', label: 'Retry Failed' },
      { value: '--use-selenium', label: 'Use Selenium', hint: 'Heavy fallback' },
      { value: '--interactive', label: 'Interactive', hint: 'CAPTCHA solving' },
      { value: '--headful', label: 'Headful', hint: 'Visible browser' },
      { value: '--stealth-mode=seleniumbase', label: 'SeleniumBase Stealth', hint: 'Best Cloudflare bypass' },
      { value: '--prioritize-opinion', label: 'Prioritize Opinions' },
      { value: '--use-proxy', label: 'Use Proxy' }
    ],
    initialValues: ['--lean', '--stealth-mode=seleniumbase', '--no-headful-switch'] as string[]
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  const batchSize = await text({ message: 'Batch size:', defaultValue: '100', placeholder: '100' });
  if (isCancel(batchSize)) throw new Error('Operation cancelled');
  if (batchSize && String(batchSize).trim()) args.push('-b', String(batchSize));

  const concurrency = await text({ message: 'Concurrency (tabs):', defaultValue: '10', placeholder: '10' });
  if (isCancel(concurrency)) throw new Error('Operation cancelled');
  if (concurrency && String(concurrency).trim()) args.push('-c', String(concurrency));

  const rateLimit = await text({ message: 'Rate limit (req/s, 0 = unlimited):', defaultValue: '0', placeholder: '0' });
  if (isCancel(rateLimit)) throw new Error('Operation cancelled');
  if (rateLimit && String(rateLimit).trim()) args.push('-r', String(rateLimit));

  const maxRetries = await text({ message: 'Max retries per URL:', defaultValue: '2', placeholder: '2' });
  if (isCancel(maxRetries)) throw new Error('Operation cancelled');
  if (maxRetries && String(maxRetries).trim()) args.push('--max-retries', String(maxRetries));

  return args;
}

async function configureContentFilterArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Content filter mode?',
    options: [
      { value: 'default', label: 'Default (Recommended)', hint: 'Verbose, score≥20, comments≥5' },
      { value: 'reset-and-run', label: 'Reset & Re-run', hint: 'Clear + re-filter all' },
      { value: 'reset-only', label: 'Reset only', hint: 'Clear data and exit' },
      { value: 'all-domains', label: 'All domains', hint: 'Include GitHub/ArXiv/etc' },
      { value: 'stats', label: 'Stats only' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['-v'];
  if (mode === 'reset-and-run') return ['-v', '--reset'];
  if (mode === 'reset-only') return ['--reset-only'];
  if (mode === 'all-domains') return ['-v', '--all-domains'];
  if (mode === 'stats') return ['--stats'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--reset', label: 'Reset', hint: 'Clear before filtering' },
      { value: '--all-domains', label: 'All Domains', hint: 'Include GitHub, ArXiv, Twitter, etc.' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  const minScore = await text({ message: 'Min HN score:', defaultValue: '20', placeholder: '20' });
  if (isCancel(minScore)) throw new Error('Operation cancelled');
  if (minScore && String(minScore).trim() !== '20') args.push('--min-score', String(minScore));

  const minComments = await text({ message: 'Min HN comments:', defaultValue: '5', placeholder: '5' });
  if (isCancel(minComments)) throw new Error('Operation cancelled');
  if (minComments && String(minComments).trim() !== '5') args.push('--min-comments', String(minComments));

  const batchSize = await text({ message: 'Batch size:', defaultValue: '20', placeholder: '20' });
  if (isCancel(batchSize)) throw new Error('Operation cancelled');
  if (batchSize && String(batchSize).trim()) args.push('-b', String(batchSize));

  const limit = await text({ message: 'Limit (0 = unlimited):', defaultValue: '0', placeholder: '0' });
  if (isCancel(limit)) throw new Error('Operation cancelled');
  if (limit && String(limit).trim() !== '0') args.push('-l', String(limit));

  return args;
}

async function configureSentimentAnalyzerArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Sentiment mode?',
    options: [
      { value: 'default', label: 'Default (Recommended)', hint: 'Verbose, pending articles' },
      { value: 'reset-and-run', label: 'Reset & Re-run', hint: 'Clear + analyze all' },
      { value: 'reset-only', label: 'Reset only', hint: 'Clear scores and exit' },
      { value: 'stats', label: 'Stats only' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['-v'];
  if (mode === 'reset-and-run') return ['-v', '--reset'];
  if (mode === 'reset-only') return ['--reset-only'];
  if (mode === 'stats') return ['--stats'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--reset', label: 'Reset', hint: 'Clear then analyze' },
      { value: '--reanalyze', label: 'Re-analyze', hint: 'Include already-analyzed' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  const minScore = await text({ message: 'Min HN score:', defaultValue: '20', placeholder: '20' });
  if (isCancel(minScore)) throw new Error('Operation cancelled');
  if (minScore && String(minScore).trim() !== '20') args.push('--min-score', String(minScore));

  const minComments = await text({ message: 'Min HN comments:', defaultValue: '5', placeholder: '5' });
  if (isCancel(minComments)) throw new Error('Operation cancelled');
  if (minComments && String(minComments).trim() !== '5') args.push('--min-comments', String(minComments));

  const batchSize = await text({ message: 'Batch size:', defaultValue: '20', placeholder: '20' });
  if (isCancel(batchSize)) throw new Error('Operation cancelled');
  if (batchSize && String(batchSize).trim()) args.push('-b', String(batchSize));

  const limit = await text({ message: 'Limit (0 = unlimited):', defaultValue: '0', placeholder: '0' });
  if (isCancel(limit)) throw new Error('Operation cancelled');
  if (limit && String(limit).trim() !== '0') args.push('-l', String(limit));

  return args;
}

async function configureSummarySummarizerArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Theme synthesizer mode?',
    options: [
      { value: 'default', label: 'Default', hint: 'Process exported summaries' },
      { value: 'reset', label: 'Reset & Re-run', hint: 'Clear themes then process' },
      { value: 'stats', label: 'Stats only' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['-v'];
  if (mode === 'reset') return ['-v', '--reset'];
  if (mode === 'stats') return ['--stats'];

  const args: string[] = [];

  const flags = await multiselect({
    message: 'Flags:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--reset', label: 'Reset', hint: 'Clear themes before processing' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) throw new Error('Operation cancelled');
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  const inputDir = await text({ message: 'Input directory:', defaultValue: '', placeholder: 'data/exports' });
  if (isCancel(inputDir)) throw new Error('Operation cancelled');
  if (inputDir && String(inputDir).trim()) args.push('--input-dir', String(inputDir));

  return args;
}

async function configureExportArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Export mode?',
    options: [
      { value: 'default', label: 'Default', hint: 'Generate JSON for src/lib/data/' },
      { value: 'custom', label: 'Custom output path' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'default') return ['-v'];

  const outputPath = await text({
    message: 'Output directory:',
    defaultValue: '../src/lib/data',
    placeholder: '../src/lib/data'
  });
  if (isCancel(outputPath)) return null;

  return ['-v', '-o', String(outputPath)];
}

async function configureCatchUpArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Catch-up mode?',
    options: [
      { value: 'quick', label: 'Quick (5 pages)', hint: 'Fast daily update — recommended' },
      { value: 'standard', label: 'Standard (10 pages)', hint: 'Weekly catch-up' },
      { value: 'deep', label: 'Deep (25 pages)', hint: 'Comprehensive backfill' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'quick') return ['-v', '--pages', '5'];
  if (mode === 'standard') return ['-v', '--pages', '10'];
  if (mode === 'deep') return ['-v', '--pages', '25'];

  const args: string[] = [];

  const pages = await text({ message: 'Pages to backfill:', defaultValue: '5', placeholder: '5' });
  if (isCancel(pages)) return null;
  args.push('--pages', String(pages));

  const flags = await multiselect({
    message: 'Options:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--skip-scrape', label: 'Skip Scraping', hint: 'Use existing content' },
      { value: '--skip-analyze', label: 'Skip Analysis', hint: 'Skip prefilter + sentiment' },
      { value: '--dry-run', label: 'Dry Run', hint: 'Show plan without executing' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) return null;
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  return args;
}

async function configureInitialE2EArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Initial E2E mode?',
    options: [
      { value: 'balanced', label: 'Balanced (100 tabs)', hint: 'Recommended for most systems' },
      { value: 'aggressive', label: 'Aggressive (200 tabs)', hint: 'High-end systems with proxy' },
      { value: 'conservative', label: 'Conservative (50 tabs)', hint: 'Lower resource usage' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'balanced') return ['-v', '-c', '100'];
  if (mode === 'aggressive') return ['-v', '-c', '200', '--use-proxy'];
  if (mode === 'conservative') return ['-v', '-c', '50'];

  const args: string[] = [];

  const concurrency = await text({ message: 'Concurrency (tabs):', defaultValue: '100', placeholder: '100' });
  if (isCancel(concurrency)) return null;
  args.push('--concurrency', String(concurrency));

  const flags = await multiselect({
    message: 'Options:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--use-proxy', label: 'Use Proxy', hint: 'Enable proxy rotation' },
      { value: '--no-headful', label: 'No Headful Retry', hint: 'Skip headful retry pass' },
      { value: '--dry-run', label: 'Dry Run' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) return null;
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  return args;
}

async function configureHeadfulRetryArgs(): Promise<string[] | null> {
  const mode = await select({
    message: 'Headful retry mode?',
    options: [
      { value: 'standard', label: 'Standard (20 tabs)', hint: 'Recommended' },
      { value: 'aggressive', label: 'Aggressive (40 tabs)', hint: 'High-end systems' },
      { value: 'conservative', label: 'Conservative (10 tabs)', hint: 'Lower resource usage' },
      { value: 'scrape-only', label: 'Scrape Only', hint: 'Skip prefilter + sentiment' },
      { value: 'custom', label: 'Configure' },
      { value: 'back', label: '← Back' }
    ]
  });

  if (isCancel(mode) || mode === 'back') return null;
  if (mode === 'standard') return ['-v', '-c', '20'];
  if (mode === 'aggressive') return ['-v', '-c', '40', '--use-proxy'];
  if (mode === 'conservative') return ['-v', '-c', '10'];
  if (mode === 'scrape-only') return ['-v', '-c', '20', '--skip-analyze'];

  const args: string[] = [];

  const concurrency = await text({ message: 'Concurrency (tabs):', defaultValue: '20', placeholder: '20' });
  if (isCancel(concurrency)) return null;
  args.push('--concurrency', String(concurrency));

  const batchSize = await text({ message: 'Batch size:', defaultValue: '200', placeholder: '200' });
  if (isCancel(batchSize)) return null;
  args.push('--batch-size', String(batchSize));

  const maxRetries = await text({ message: 'Max retries per URL:', defaultValue: '3', placeholder: '3' });
  if (isCancel(maxRetries)) return null;
  args.push('--max-retries', String(maxRetries));

  const flags = await multiselect({
    message: 'Options:',
    options: [
      { value: '-v', label: 'Verbose (-v)' },
      { value: '--use-proxy', label: 'Use Proxy' },
      { value: '--skip-analyze', label: 'Skip Analysis', hint: 'Skip prefilter + sentiment' },
      { value: '--skip-export', label: 'Skip Export', hint: 'Do not export after scraping' },
      { value: '--dry-run', label: 'Dry Run' }
    ],
    initialValues: ['-v'] as string[]
  });
  if (isCancel(flags)) return null;
  if (Array.isArray(flags)) args.push(...(flags as string[]));

  return args;
}

async function main() {
  console.clear();
  intro('🤖 "Is AI Good Yet?" Project CLI');

  while (true) {
    const action = await select({
      message: 'What would you like to do?',
      options: [
        { value: 'dev', label: 'Start Frontend (Dev)', hint: 'SvelteKit dev server' },
        { value: 'build', label: 'Build Frontend', hint: 'Production build' },
        { value: 'start', label: 'Start Server', hint: 'Run production build' },
        { value: 'separator-e2e', label: '────── E2E Pipelines ──────', hint: '' },
        { value: 'pipeline-initial', label: 'Initial E2E (Full Scrape)', hint: 'High concurrency, fresh database' },
        { value: 'pipeline-catchup', label: 'Catch-Up E2E (Incremental)', hint: 'Update recent articles' },
        { value: 'pipeline-headful-retry', label: 'Headful Retry E2E', hint: 'Aggressive retry for missing articles' },
        { value: 'separator-phases', label: '────── Pipeline Phases ──────', hint: '' },
        { value: 'pipeline-backfill', label: 'Phase 1: Backfill/Ingest', hint: 'Scrape URLs from Histre.com' },
        { value: 'pipeline-resolve', label: 'Phase 2: Resolve HN Links', hint: 'Query Algolia for HN metadata' },
        { value: 'pipeline-scrape', label: 'Phase 3: Scrape Content', hint: 'Fetch article text with fallbacks' },
        { value: 'pipeline-clean', label: 'Phase 3.5a: Clean Article Text', hint: 'Normalize and sanitize content' },
        { value: 'pipeline-uptake', label: 'Phase 3.5b: Ground-Truth Uptake', hint: 'Sync text files to DB' },
        { value: 'pipeline-consistency', label: 'Phase 3.7: Consistency Check', hint: 'Verify data alignment' },
        { value: 'pipeline-content-filter', label: 'Phase 4: Content Prefilter', hint: 'Classify article relevance' },
        { value: 'pipeline-analyze', label: 'Phase 5: Analyze Sentiment', hint: 'Score articles with LLM' },
        { value: 'pipeline-export', label: 'Phase 6: Export Data', hint: 'Generate static JSON' },
        { value: 'separator-v2', label: '────── V2 Sentiment ──────', hint: '' },
        { value: 'pipeline-v2-prefilter', label: 'V2: Broad Prefilter', hint: 'Classify all AI domains without changing V1' },
        { value: 'pipeline-v2-comments', label: 'V2: Collect HN Comments', hint: 'Fetch and select representative discussion' },
        { value: 'pipeline-v2-analyze', label: 'V2: Analyze Two Tiers', hint: 'Score articles and HN response' },
        { value: 'pipeline-v2-export', label: 'V2: Export Data', hint: 'Generate isolated v2 JSON' },
        { value: 'separator-utils', label: '────── Utilities ──────', hint: '' },
        { value: 'pipeline-themes', label: 'Synthesize Themes', hint: 'Extract themes from summaries' },
        { value: 'pipeline-reclassify', label: 'Reclassify Sterile Articles', hint: 'Re-run classification' },
        { value: 'pipeline-bootstrap', label: 'Bootstrap DB', hint: 'Initialize database' },
        { value: 'pipeline-stats', label: 'Stats', hint: 'Check pipeline progress' },
        { value: 'python-setup', label: `Setup Python Env${venvReady ? ' ✓' : ' ⚠ venv missing'}`, hint: 'Create venv + install deps' },
        { value: 'bump-version', label: 'Bump Version', hint: 'patch / minor / major' },
        { value: 'exit', label: 'Exit' }
      ]
    });

    if (isCancel(action) || action === 'exit') {
      outro('Bye! 👋');
      process.exit(0);
    }

    if (String(action).startsWith('separator')) continue;

    try {
      if (action === 'dev') {
        await runScript('bun', ['run', 'dev']);
      }
      else if (action === 'build') {
        await runScript('bun', ['run', 'build']);
      }
      else if (action === 'start') {
        await runScript('bun', ['run', 'start']);
      }
      else if (action === 'pipeline-initial') {
        const args = await configureInitialE2EArgs();
        if (args === null) continue;
        const success = await runScript(pythonCmd, ['-m', 'src.initial_e2e', ...args], PIPELINE_DIR);
        if (success) {
          const bump = await confirm({ message: 'Initial E2E complete! Bump version?', initialValue: true });
          if (!isCancel(bump) && bump) await bumpVersion('major');
        }
      }
      else if (action === 'pipeline-catchup') {
        const args = await configureCatchUpArgs();
        if (args === null) continue;
        const success = await runScript(pythonCmd, ['-m', 'src.catch_up', ...args], PIPELINE_DIR);
        if (success) {
          const bump = await confirm({ message: 'Catch-up complete! Bump version?', initialValue: true });
          if (!isCancel(bump) && bump) await bumpVersion('patch');
        }
      }
      else if (action === 'pipeline-headful-retry') {
        const args = await configureHeadfulRetryArgs();
        if (args === null) continue;
        const success = await runScript(pythonCmd, ['-m', 'src.headful_retry', ...args], PIPELINE_DIR);
        if (success && !args.includes('--skip-export')) {
          const bump = await confirm({ message: 'Headful retry complete! Bump version?', initialValue: true });
          if (!isCancel(bump) && bump) await bumpVersion('patch');
        }
      }
      else if (action === 'pipeline-backfill') {
        const args = await configureBackfillArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.backfill_histre', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-resolve') {
        const args = await configureResolverArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.hn_resolver', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-scrape') {
        const args = await configureScraperArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.scraper', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-clean') {
        const cleanMode = await select({
          message: 'Clean mode?',
          options: [
            { value: 'new-only', label: 'New files only (fast)', hint: 'Files added since last run' },
            { value: 'all', label: 'Clean all files', hint: 'Full clean' },
            { value: 'back', label: '← Back' }
          ]
        });
        if (isCancel(cleanMode) || cleanMode === 'back') continue;

        const doBackup = await confirm({ message: 'Create backup before cleaning?', initialValue: cleanMode === 'all' });
        if (isCancel(doBackup)) continue;

        const args: string[] = [];
        if (!doBackup) args.push('--no-backup');
        if (cleanMode === 'new-only') args.push('--new-only');
        if (cleanMode === 'all') args.push('--clean-all');

        await runScript(pythonCmd, ['src/clean_articles.py', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-uptake') {
        await runScript(pythonCmd, ['src/uptake_ground_truth.py'], PIPELINE_DIR);
      }
      else if (action === 'pipeline-consistency') {
        const doFix = await confirm({ message: 'Auto-fix phantom articles?', initialValue: false });
        if (isCancel(doFix)) continue;
        await runScript(pythonCmd, ['src/check_consistency.py', ...(doFix ? ['--fix'] : [])], PIPELINE_DIR);
      }
      else if (action === 'pipeline-content-filter') {
        const args = await configureContentFilterArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.prefilter_content', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-analyze') {
        const args = await configureSentimentAnalyzerArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.sentiment_analyzer', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-v2-prefilter') {
        await runScript(pythonCmd, ['-m', 'src.v2_prefilter'], PIPELINE_DIR);
      }
      else if (action === 'pipeline-v2-comments') {
        await runScript(pythonCmd, ['-m', 'src.hn_comments_v2', '-v'], PIPELINE_DIR);
      }
      else if (action === 'pipeline-v2-analyze') {
        await runScript(pythonCmd, ['-m', 'src.sentiment_v2', '-v'], PIPELINE_DIR);
      }
      else if (action === 'pipeline-v2-export') {
        await runScript(pythonCmd, ['-m', 'src.export_v2'], PIPELINE_DIR);
      }
      else if (action === 'pipeline-export') {
        const args = await configureExportArgs();
        if (args === null) continue;
        const success = await runScript(pythonCmd, ['-m', 'src.export', ...args], PIPELINE_DIR);
        if (success) {
          const bump = await confirm({ message: 'Export complete! Bump version?', initialValue: true });
          if (!isCancel(bump) && bump) await bumpVersion('patch');
        }
      }
      else if (action === 'pipeline-themes') {
        const args = await configureSummarySummarizerArgs();
        if (args === null) continue;
        await runScript(pythonCmd, ['-m', 'src.summary_summarizer', ...args], PIPELINE_DIR);
      }
      else if (action === 'pipeline-reclassify') {
        const dryRun = await confirm({ message: 'Dry-run first?', initialValue: true });
        if (isCancel(dryRun)) continue;
        await runScript(pythonCmd, ['src/reclassify_sterile.py', ...(dryRun ? ['--dry-run', '-v'] : ['-v'])], PIPELINE_DIR);
      }
      else if (action === 'pipeline-bootstrap') {
        await runScript('bun', ['run', 'pipeline:bootstrap']);
      }
      else if (action === 'pipeline-stats') {
        await runScript('bun', ['run', 'pipeline:stats']);
      }
      else if (action === 'python-setup') {
        const venvDir = path.join(PIPELINE_DIR, '.venv');
        const isWin = process.platform === 'win32';
        const sysPython = isWin ? 'py' : 'python3';
        const venvPython = path.join(venvDir, isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');

        console.log(`\nTarget venv: ${venvDir}`);

        if (!fs.existsSync(venvDir)) {
          console.log('Creating venv...');
          const ok = await runScript(sysPython, ['-m', 'venv', venvDir]);
          if (!ok) { console.error('venv creation failed.'); continue; }
        } else {
          console.log('venv exists, skipping creation.');
        }

        // On Windows, pip can't replace itself mid-execution (pip ≥ 23).
        // Use subprocess workaround: spawn a detached pip upgrade.
        console.log('\nUpgrading pip...');
        await runScript(venvPython, ['-m', 'pip', 'install', 'pip', 'setuptools', 'wheel',
          '--upgrade', '--no-deps', '--disable-pip-version-check', '--quiet']);

        console.log('\nInstalling requirements...');
        const reqOk = await runScript(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt',
          '--upgrade-strategy', 'only-if-needed', '--disable-pip-version-check'], PIPELINE_DIR);
        if (!reqOk) { console.error('pip install failed.'); continue; }

        const installPlaywright = await confirm({
          message: 'Install Playwright browsers? (needed for scraper)',
          initialValue: true
        });
        if (!isCancel(installPlaywright) && installPlaywright) {
          await runScript(venvPython, ['-m', 'playwright', 'install', 'chromium']);
        }

        console.log('\n✓ Python environment ready.');
        console.log(`  Interpreter: ${venvPython}`);
        console.log('  Restart CLI to pick up new venv.\n');
      }
      else if (action === 'bump-version') {
        await bumpVersion();
      }
    } catch (error) {
      console.error(error);
    }
  }
}

main().catch(console.error);
