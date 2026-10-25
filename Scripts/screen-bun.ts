// screen-bun.ts
// Fill lines 58-65 with your defaults, like cinema-bun.ts lines 334-338
//   58: DEFAULT_URL        — website to shoot when you run with no args
//   59: DEFAULT_OUT_DIR    — where shots go, e.g. './shots' or '/Volumes/X-Drive/shots'
//   60: CACHE_PATH         — sqlite cache, or ':memory:' to disable disk cache
//   61: DEFAULT_FORMAT      — always 'jpeg' unless you override with --format
//   62: DEFAULT_WAIT_MS     — 2000 = first shot 2s after load completes
//   63: DEFAULT_CADENCE_MS  — cadence between batch shots (override with --cadence)
//   64: DEFAULT_LIMIT       — max shots, null = unlimited (override with --limit)
// Fill lines 340-350 in import.meta.main with your test cases, like cinema lines 334-345
// NOTE: This bun script captures a website with Bun.WebView and resizes with
// native Bun.Image (replaces sharp / Puppeteer / Playwright). No deps.
// BEWARE: The old API — Bun.WebView.launch() + newPage() — does not exist
// in Bun 1.3+. It is `new Bun.WebView({ width, height })`.
//
// FIX 2026-10-25 (2): --full-page used to throw if document.body was null
// (Tumblr/Cloudflare challenge pages have no body yet) and kill the whole
// shot. Now it is null-safe + waits for body, and detects
// "Checking your browser" and waits for it to clear before shooting.
// © 2026 – you own this code.
import { Database } from 'bun:sqlite';
import { mkdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';

export interface DevicePreset { name: string; width: number; height: number; label: string; }

export interface ShotOptions {
  device?: DevicePreset | string;
  width?: number; height?: number;
  format?: 'png' | 'jpeg' | 'webp';
  quality?: number;
  thumbWidth?: number | null;
  fullPage?: boolean;
  waitMs?: number;
  cadenceMs?: number;
  limit?: number | null;
  challengeWaitMs?: number; // extra wait if Cloudflare/Tumblr challenge detected
  waitForSelector?: string | null;
  timeoutMs?: number;
  name?: string | null;
  subpages?: boolean;
  paths?: string[];
}

export interface ShotResult {
  url: string; device: string; format: string; filePath: string;
  sizeBytes: number; width: number; height: number; fromCache: boolean; index?: number; warning?: string;
}

export const DEVICES: Record<string, DevicePreset> = {
  desktop: { name: 'desktop', width: 1920, height: 1080, label: 'desktop-1920x1080' },
  laptop: { name: 'laptop', width: 1440, height: 900, label: 'laptop-1440x900' },
  tablet: { name: 'tablet', width: 768, height: 1024, label: 'tablet-768x1024' },
  mobile: { name: 'mobile', width: 390, height: 844, label: 'mobile-390x844' },
  'mobile-landscape': { name: 'mobile-landscape', width: 844, height: 390, label: 'mobile-ls-844x390' },
};

const DEFAULT_URL = 'https://google.com';
const DEFAULT_OUT_DIR = './shots';
const CACHE_PATH = './shots-cache.sqlite';
const DEFAULT_FORMAT: 'png' | 'jpeg' | 'webp' = 'jpeg';
const DEFAULT_WAIT_MS = 2000;
const DEFAULT_CADENCE_MS = 5000;
const DEFAULT_LIMIT: number | null = null;
const DEFAULT_CHALLENGE_WAIT_MS = 12000;
const CACHE_TTL_SECONDS = 3600;
const RATE_LIMIT_MS = 1200;

function decodeSlug(str: string): string {
  return str.replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase();
}

export class BunSiteShooter {
  private outDir: string;
  private rateLimitMs: number;
  private lastRequestTime = 0;
  private db: Database;
  private cacheTtlMs: number;

  constructor(options?: { outDir?: string; cachePath?: string; cacheTtlSeconds?: number; rateLimitMs?: number }) {
    this.outDir = options?.outDir ?? DEFAULT_OUT_DIR;
    const dbPath = options?.cachePath ?? CACHE_PATH;
    this.cacheTtlMs = (options?.cacheTtlSeconds ?? CACHE_TTL_SECONDS) * 1000;
    this.rateLimitMs = options?.rateLimitMs ?? RATE_LIMIT_MS;
    this.db = new Database(dbPath);
    this.db.run(`CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, timestamp INTEGER NOT NULL)`);
  }

  private getCache<T>(key: string): T | null {
    const row = this.db.query<{ value: string; timestamp: number }, [string]>('SELECT value, timestamp FROM cache WHERE key = ?').get(key);
    if (!row) return null;
    if (Date.now() - row.timestamp > this.cacheTtlMs) { this.db.run('DELETE FROM cache WHERE key = ?', [key]); return null; }
    return JSON.parse(row.value) as T;
  }
  private setCache(key: string, value: unknown): void {
    this.db.run('INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)', [key, JSON.stringify(value), Date.now()]);
  }
  private async withRateLimit(): Promise<void> {
    const now = Date.now(); const waitTime = this.lastRequestTime + this.rateLimitMs - now;
    if (waitTime > 0) await Bun.sleep(waitTime); this.lastRequestTime = Date.now();
  }
  private normalizeUrl(input: string): string {
    let raw = input.trim(); if (!raw) throw new Error('Empty URL');
    if (!/^https?:\/\//i.test(raw)) raw = `https://${raw}`;
    const url = new URL(raw);
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error(`Unsupported protocol: ${url.protocol}`);
    return url.toString();
  }
  private safeSlug(urlStr: string): string {
    const u = new URL(urlStr);
    const host = decodeSlug(u.hostname.replace(/^www\./, ''));
    const path = decodeSlug(u.pathname);
    const base = path ? `${host}-${path}` : host;
    return base.slice(0, 80) || 'site';
  }
  private timestamp(): string { return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19); }
  private resolveDevice(opts: ShotOptions): DevicePreset {
    if (opts.width) return { name: 'custom', width: opts.width, height: opts.height ?? 1080, label: `custom-${opts.width}x${opts.height ?? 1080}` };
    if (typeof opts.device === 'string') return DEVICES[opts.device] ?? DEVICES.desktop;
    return opts.device ?? DEVICES.desktop;
  }
  private effectiveLimit(opts: ShotOptions): number | null { return opts.limit ?? DEFAULT_LIMIT; }
  private effectiveCadence(opts: ShotOptions): number { return opts.cadenceMs ?? DEFAULT_CADENCE_MS; }
  private applyLimit<T>(items: T[], opts: ShotOptions): T[] {
    const limit = this.effectiveLimit(opts); if (limit == null) return items; if (limit <= 0) return []; return items.slice(0, limit);
  }
  private resolvePath(base: string, p: string): string {
    if (p.startsWith('http')) return p;
    const path = p.startsWith('/') ? p : `/${p}`;
    return new URL(path, base).toString();
  }

  // [STRIPPED 77 bytes] Helpers that make --full-page not crash
  // [STRIPPED 75 bytes]
  private async waitForBody(view: any, timeoutMs: number): Promise<boolean> {
    const t0 = Date.now();
    while (Date.now() - t0 < timeoutMs) {
      try {
        const has = await view.evaluate(`!!(document && document.body)`);
        if (has) return true;
      } catch {}
      await Bun.sleep(250);
    }
    return false;
  }
  private async safeScrollHeight(view: any): Promise<number> {
    try {
      // Null-safe: document.body may be null on challenge pages
      const h = await view.evaluate(`(() => { try { const b = document?.body; const d = document?.documentElement; return Math.max(b?.scrollHeight || 0, d?.scrollHeight || 0, window.innerHeight || 0); } catch { return window.innerHeight || 0; } })()`);
      return typeof h === 'number' && h > 0 ? h : 0;
    } catch { return 0; }
  }
  private async isChallengePage(view: any): Promise<boolean> {
    try {
      const txt = await view.evaluate(`(() => { try { return (document?.title || '') + ' ' + (document?.body?.innerText || '').slice(0, 500); } catch { return ''; } })()`);
      const s = String(txt || '').toLowerCase();
      return s.includes('checking your browser') || s.includes('cloudflare') || s.includes('verify you are human') || s.includes('just a moment');
    } catch { return false; }
  }

  private async discoverSubpages(baseUrl: string, opts: ShotOptions = {}): Promise<string[]> {
    const url = this.normalizeUrl(baseUrl);
    const device = this.resolveDevice(opts);
    const view = new Bun.WebView({ width: device.width, height: device.height });
    try {
      await Promise.race([view.navigate(url), Bun.sleep(opts.timeoutMs ?? 30_000).then(() => { throw new Error('Discover timeout'); })]);
      await Bun.sleep(500);
      const hrefs = await view.evaluate(`[...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(Boolean)`) as string[];
      const origin = new URL(url).origin; const seen = new Set<string>([url]); const out: string[] = [];
      for (const h of hrefs) {
        try { const resolved = new URL(h, url).toString(); if (!resolved.startsWith(origin)) continue; if (resolved.includes('#')) continue; if (/\.(pdf|zip|png|jpg|jpeg|webp|svg|mp4)$/i.test(resolved)) continue; if (!seen.has(resolved)) { seen.add(resolved); out.push(resolved); } } catch {}
      }
      return out;
    } finally { view.close(); }
  }

  /** 1. One URL × one device */
  async shoot(urlInput: string, opts: ShotOptions = {}): Promise<ShotResult> {
    const url = this.normalizeUrl(urlInput);
    const device = this.resolveDevice(opts);
    const format = opts.format ?? DEFAULT_FORMAT;
    const quality = opts.quality ?? 85;
    const thumbWidth = opts.thumbWidth ?? null;
    const fullPage = opts.fullPage ?? false;
    const waitMs = opts.waitMs ?? DEFAULT_WAIT_MS;
    const timeoutMs = opts.timeoutMs ?? 30_000;
    const challengeWaitMs = opts.challengeWaitMs ?? DEFAULT_CHALLENGE_WAIT_MS;
    const cacheKey = `shot:${url}:${device.label}:${format}:${thumbWidth ?? 'full'}:${fullPage}`;
    const cached = this.getCache<ShotResult>(cacheKey);
    if (cached && await Bun.file(cached.filePath).exists()) { console.log(`⏭️  cached ${url} [${device.label}] → ${cached.filePath}`); return { ...cached, fromCache: true }; }

    await this.withRateLimit();
    await mkdir(resolve(this.outDir), { recursive: true });
    const start = Date.now();
    const view = new Bun.WebView({ width: device.width, height: device.height, ...(format === 'webp' ? { backend: 'chrome' as const } : {}) });
    let warning: string | undefined;

    try {
      await Promise.race([view.navigate(url), Bun.sleep(timeoutMs).then(() => { throw new Error(`Navigation timeout after ${timeoutMs}ms`); })]);
      if (opts.waitForSelector) {
        const sel = opts.waitForSelector; const t0 = Date.now();
        while (Date.now() - t0 < timeoutMs) { const found = await view.evaluate(`!!document.querySelector(${JSON.stringify(sel)})`); if (found) break; await Bun.sleep(250); }
      }
      if (waitMs > 0) await Bun.sleep(waitMs);

      // Wait for body before touching it — fixes document.body null crash
      const hasBody = await this.waitForBody(view, 5000);
      if (!hasBody) console.log(`⚠️  ${url}: document.body not ready after 5s, continuing with viewport`);

      // Cloudflare / Tumblr challenge: if we see it, wait for it to clear
      if (await this.isChallengePage(view)) {
        console.log(`⏳ ${url}: challenge page detected ("Checking your browser") — waiting up to ${challengeWaitMs}ms for real content...`);
        const t0 = Date.now();
        while (Date.now() - t0 < challengeWaitMs) {
          await Bun.sleep(1000);
          if (!(await this.isChallengePage(view))) { console.log(`   ✅ Challenge cleared after ${Date.now() - t0}ms`); break; }
        }
        if (await this.isChallengePage(view)) { warning = 'challenge-page-still-present'; console.log(`⚠️  ${url}: still on challenge page after ${challengeWaitMs}ms — shot will be of the challenge, not content. Try --challenge-wait 30000 or --wait 8000`); }
      }

      let shotHeight = device.height;
      if (fullPage) {
        // Safe: never throws, falls back to viewport
        for (let attempt = 0; attempt < 2; attempt++) {
          const fullH = await this.safeScrollHeight(view);
          if (fullH > shotHeight) { const target = Math.min(fullH, 16384); await view.resize(device.width, target); shotHeight = target; await Bun.sleep(600); } else break;
        }
      }

      const screenshot = await view.screenshot({ format, quality: format === 'png' ? undefined : quality, encoding: 'buffer' }) as Buffer;
      let finalBuffer: Buffer = screenshot;
      if (thumbWidth) { const image = Bun.Image.fromBuffer(screenshot); finalBuffer = await image.resize(thumbWidth).toFormat(format).toBuffer(); }
      const slug = opts.name ? decodeSlug(opts.name) : this.safeSlug(url);
      const ext = format === 'jpeg' ? 'jpg' : format;
      const fileName = `${slug}-${device.label}-${this.timestamp()}.${ext}`;
      const filePath = join(resolve(this.outDir), fileName);
      await Bun.write(filePath, finalBuffer);
      const result: ShotResult = { url, device: device.label, format, filePath, sizeBytes: finalBuffer.length, width: device.width, height: shotHeight, fromCache: false, warning };
      this.setCache(cacheKey, result);
      console.log(`✅ ${url} [${device.label}] → ${filePath} (${(finalBuffer.length / 1024).toFixed(1)} KB, ${device.width}x${shotHeight}, ${Date.now() - start}ms)${warning ? ' ⚠️ ' + warning : ''}`);
      return result;
    } finally { view.close(); }
  }

  /** 2. Batch many URLs */
  async shootMany(urls: string[], opts: ShotOptions = {}): Promise<ShotResult[]> {
    const limited = this.applyLimit(urls, opts); const cadence = this.effectiveCadence(opts); const results: ShotResult[] = [];
    for (let i = 0; i < limited.length; i++) {
      if (i > 0 && cadence > 0) { console.log(`⏱️  cadence: waiting ${cadence}ms before shot ${i + 1}/${limited.length}...`); await Bun.sleep(cadence); }
      try { results.push({ ...(await this.shoot(limited[i], opts)), index: i }); }
      catch (e: any) { console.error(`❌ Skipping "${limited[i]}": ${e.message}`); }
    }
    return results;
  }
  /** 3. All devices */
  async shootAllDevices(url: string, opts: Omit<ShotOptions, 'device'> = {}): Promise<ShotResult[]> {
    const devices = this.applyLimit([DEVICES.desktop, DEVICES.tablet, DEVICES.mobile], opts as ShotOptions);
    const cadence = this.effectiveCadence(opts as ShotOptions); const results: ShotResult[] = [];
    for (let i = 0; i < devices.length; i++) {
      if (i > 0 && cadence > 0) await Bun.sleep(cadence);
      try { results.push({ ...(await this.shoot(url, { ...opts, device: devices[i] })), index: i }); }
      catch (e: any) { console.error(`❌ ${url} [${devices[i].label}]: ${e.message}`); }
    }
    return results;
  }
  /** 4. Sub-pages */
  async shootSubpages(baseUrl: string, opts: ShotOptions = {}): Promise<ShotResult[]> {
    const base = this.normalizeUrl(baseUrl); let subUrls: string[] = [];
    if (opts.paths?.length) subUrls = opts.paths.map(p => this.resolvePath(base, p));
    else if (opts.subpages) { console.log(`🔍 Discovering sub-pages on ${base}...`); subUrls = await this.discoverSubpages(base, opts); console.log(`   Found ${subUrls.length} same-origin links`); }
    const all = this.applyLimit([base, ...subUrls], opts); const cadence = this.effectiveCadence(opts); const results: ShotResult[] = [];
    for (let i = 0; i < all.length; i++) {
      if (i > 0 && cadence > 0) { console.log(`⏱️  cadence: waiting ${cadence}ms before navigating to ${all[i]}...`); await Bun.sleep(cadence); }
      try { results.push({ ...(await this.shoot(all[i], opts)), index: i }); }
      catch (e: any) { console.error(`❌ ${all[i]}: ${e.message}`); }
    }
    return results;
  }
  async shootFromFile(filePath: string, opts: ShotOptions = {}): Promise<ShotResult[]> {
    const text = await Bun.file(filePath).text(); const urls = text.split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith('#')); return this.shootMany(urls, opts);
  }
  async planSubpages(baseUrl: string, opts: ShotOptions = {}): Promise<string[]> {
    const base = this.normalizeUrl(baseUrl); let subUrls: string[] = [];
    if (opts.paths?.length) subUrls = opts.paths.map(p => this.resolvePath(base, p)); return this.applyLimit([base, ...subUrls], opts);
  }
}

function printHelp() {
  console.log(`
screen-bun.ts — Website screenshots, cinema-bun.ts style

  bun run screen-bun.ts                              # uses CONFIG (lines 58-65)
  bun run screen-bun.ts https://google.com --out ./shots
  bun run screen-bun.ts https://havingapoemwithyou.tumblr.com --paths /archive /search/Hanif+Abdurraqib search/anne+carson --limit 65 --device mobile --out ./shots --full-page
  bun run screen-bun.ts https://havingapoemwithyou.tumblr.com --paths=/archive,/search/x --limit 5 --out ./shots

  Flags:
    --out <dir>      Output directory
    --device <name>  desktop | laptop | tablet | mobile | mobile-landscape
    --all-devices    desktop + tablet + mobile
    --width <n> --height <n>   Custom viewport
    --format <fmt>   png | jpeg | webp (default: jpeg)
    --quality <n>    0-100 (default 85)
    --thumb <w>      Resize to width w via Bun.Image
    --full-page      Capture full document height — now null-safe, waits for body
    --wait <ms>      Wait after load for FIRST shot (default 2000)
    --cadence <ms>   Gap between batch shots (default 5000) — aliases: --interval, --every
    --challenge-wait <ms> Extra wait if "Checking your browser" detected (default 12000)
    --subpages       Auto-discover same-origin links
    --paths <a b c>  Space- OR comma-separated: --paths /archive /search/x  |  --paths /archive,/search/x
    --limit <n>      Max shots (default unlimited) — aliases: --max-shots, --max
    --wait-for <sel> Wait for CSS selector
    --timeout <ms>   Navigation timeout (default 30000)
    --name <name>    Custom file base name
    --file <path>    One URL per line
    --dry-run        Print planned URLs, don't shoot
    --verbose        Show parsed args
    --help           Show this help
`);
}

if (import.meta.main) {
  const rawArgs = process.argv.slice(2);
  if (rawArgs.includes('--help') || rawArgs.includes('-h')) { printHelp(); process.exit(0); }
  const positional: string[] = [];
  let outDir = DEFAULT_OUT_DIR; let device: string | undefined; let allDevices = false;
  let width: number | undefined; let height: number | undefined;
  let format: ShotOptions['format'] = DEFAULT_FORMAT; let thumbWidth: number | null = null;
  let fullPage = false; let waitMs: number | undefined; let cadenceMs: number | undefined; let limit: number | undefined;
  let challengeWaitMs: number | undefined; let waitForSelector: string | undefined; let name: string | undefined; let filePath: string | undefined;
  let subpages = false; let paths: string[] | undefined; let dryRun = false; let verbose = false;
  const isFlag = (s: string) => s.startsWith('-');
  for (let i = 0; i < rawArgs.length; i++) {
    let a = rawArgs[i]; let inlineValue: string | undefined;
    if (a.includes('=') && a.startsWith('--')) { const [k, v] = a.split('=', 2); a = k; inlineValue = v; }
    const next = () => { if (inlineValue !== undefined) { const v = inlineValue; inlineValue = undefined; return v; } if (i + 1 >= rawArgs.length) { console.error(`❌ Flag ${a} needs a value`); process.exit(1); } return rawArgs[++i]; };
    if (a === '--out' || a === '-o') outDir = next();
    else if (a === '--device') device = next();
    else if (a === '--all-devices') allDevices = true;
    else if (a === '--width') width = Number(next());
    else if (a === '--height') height = Number(next());
    else if (a === '--format') format = next() as ShotOptions['format'];
    else if (a === '--thumb') thumbWidth = Number(next());
    else if (a === '--full-page') fullPage = true;
    else if (a === '--wait') waitMs = Number(next());
    else if (a === '--cadence' || a === '--interval' || a === '--every') cadenceMs = Number(next());
    else if (a === '--challenge-wait') challengeWaitMs = Number(next());
    else if (a === '--limit' || a === '--max-shots' || a === '--max') { const v = Number(next()); if (!Number.isFinite(v) || v <= 0) { console.error(`❌ --limit must be positive, got "${v}"`); process.exit(1); } limit = v; }
    else if (a === '--subpages' || a === '--batch-subpages') subpages = true;
    else if (a === '--paths' || a === '--subpage' || a === '--subpages-list') {
      const collected: string[] = []; if (inlineValue !== undefined) collected.push(inlineValue);
      while (i + 1 < rawArgs.length && !isFlag(rawArgs[i + 1])) { const token = rawArgs[++i]; for (const part of token.split(',')) { const t = part.trim(); if (t) collected.push(t); } }
      const expanded: string[] = []; for (const c of collected) for (const part of c.split(',')) { const t = part.trim(); if (t) expanded.push(t); }
      paths = expanded; if (!paths.length) { console.error('❌ --paths needs at least one path'); process.exit(1); }
    }
    else if (a === '--wait-for') waitForSelector = next();
    else if (a === '--name') name = next();
    else if (a === '--file') filePath = next();
    else if (a === '--dry-run') dryRun = true;
    else if (a === '--verbose' || a === '-v') verbose = true;
    else if (a.startsWith('-')) { console.error(`❌ Unknown flag: ${a}`); printHelp(); process.exit(1); }
    else positional.push(a);
  }
  let urls = [...positional];
  const looksLikeDir = (s: string) => s.startsWith('./') || s.startsWith('../') || s.startsWith('/') || s.startsWith('~');
  if (positional.length === 2 && looksLikeDir(positional[1]) && !positional[1].includes('://')) { urls = [positional[0]]; outDir = positional[1]; }
  const shooter = new BunSiteShooter({ outDir, cachePath: CACHE_PATH, cacheTtlSeconds: CACHE_TTL_SECONDS });
  const opts: ShotOptions = { format, thumbWidth, fullPage, waitMs, cadenceMs, challengeWaitMs, limit, waitForSelector, name, width, height, device, subpages, paths };
  if (verbose || dryRun) console.log('🔍 Parsed:', JSON.stringify({ urls, outDir, format, device, limit, paths, subpages, cadenceMs: cadenceMs ?? DEFAULT_CADENCE_MS, waitMs: waitMs ?? DEFAULT_WAIT_MS, fullPage, challengeWaitMs: challengeWaitMs ?? DEFAULT_CHALLENGE_WAIT_MS }, null, 2));
  console.log(`📸 Output: ${resolve(outDir)} | Format: ${format} | Cache: ${CACHE_PATH} (TTL ${CACHE_TTL_SECONDS}s) | Rate-limit: ${RATE_LIMIT_MS}ms`);
  console.log(`   First shot: ${waitMs ?? DEFAULT_WAIT_MS}ms after load | Batch cadence: ${cadenceMs ?? DEFAULT_CADENCE_MS}ms | Limit: ${limit ?? DEFAULT_LIMIT ?? 'unlimited'} | Challenge wait: ${challengeWaitMs ?? DEFAULT_CHALLENGE_WAIT_MS}ms`);
  if (dryRun) {
    if (subpages || paths) { for (const u of urls.length ? urls : [DEFAULT_URL]) { const planned = await shooter.planSubpages(u, opts); console.log(`📋 Would shoot ${planned.length}:`); planned.forEach((p, idx) => console.log(`   ${idx}: ${p}`)); } }
    else console.log(`📋 Would shoot ${urls.length ? urls.length : 1}:`, urls.length ? urls : [DEFAULT_URL]);
    process.exit(0);
  }
  if (filePath) { console.log(await shooter.shootFromFile(filePath, opts)); }
  else if (urls.length === 0) {
    console.log(`1. Testing shoot("${DEFAULT_URL}") — edit lines 58-65 to change default...`);
    if (subpages || paths) console.log(await shooter.shootSubpages(DEFAULT_URL, opts));
    else if (allDevices) console.log(await shooter.shootAllDevices(DEFAULT_URL, opts));
    else console.log(await shooter.shoot(DEFAULT_URL, opts));
  } else if (subpages || paths) { for (const u of urls) console.log(await shooter.shootSubpages(u, opts)); }
  else if (allDevices) { for (const u of urls) console.log(await shooter.shootAllDevices(u, opts)); }
  else { console.log(await shooter.shootMany(urls, opts)); }
}
