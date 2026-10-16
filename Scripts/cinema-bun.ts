// cinema-letterboxd-bun-scraper.ts
// Fill lines 330 with the file caching path, 334-335 with the film to search and 202, 337-338 with your own user profile username
// NOTE: This bun script fetches public film metadata and user’s watch history.
// BEWARE: Scraping another user’s activity may reveal personal data (PII) and 
// * so keep `getUserRecentActivity` limited to your own account or obtain explicit consent.
// *
// * © 2025 – you own this code. Feel free to publish, but do not embed real
// * usernames or email addresses that could identify private individuals.
import { Database } from 'bun:sqlite';

export interface FilmData {
  name: string;
  year: number | null;
  slug: string;
  url: string;
  description: string;
  posterUrl: string;
  directors: { name: string; url?: string }[];
  genres: string[];
  rating: {
    average: number | null;
    count: number | null;
  };
}

export interface SearchResult {
  name: string;
  year: string;
  slug: string;
  url: string;
  director: string;
}

export interface UserActivity {
  title: string;
  filmTitle: string;
  filmYear: number | null;
  slug: string;
  userRating: number | null;
  watchedDate: string;
  posterUrl: string;
  link: string;
}

function decodeHtmlEntities(str: string): string {
  return str
    .replace(/&#039;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

export class BunLetterboxdScraper {
  private baseUrl = 'https://letterboxd.com';
  private rateLimitMs = 1200;
  private lastRequestTime = 0;
  private db: Database;
  private cacheTtlMs: number;

  private headers = {
    'User-Agent':
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
  };

  constructor(options?: { cachePath?: string; cacheTtlSeconds?: number }) {
    const dbPath = options?.cachePath ?? ':memory:'; // Pass a file path like './letterboxd-cache.sqlite' for persistent cache
    this.cacheTtlMs = (options?.cacheTtlSeconds ?? 3600) * 1000;
    this.db = new Database(dbPath);
    this.db.run(`
      CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        timestamp INTEGER NOT NULL
      )
    `);
  }

  private getCache<T>(key: string): T | null {
    const row = this.db
      .query<{ value: string; timestamp: number }, [string]>(
        'SELECT value, timestamp FROM cache WHERE key = ?'
      )
      .get(key);

    if (!row) return null;
    if (Date.now() - row.timestamp > this.cacheTtlMs) {
      this.db.run('DELETE FROM cache WHERE key = ?', [key]);
      return null;
    }
    return JSON.parse(row.value) as T;
  }

  private setCache(key: string, value: unknown): void {
    this.db.run(
      'INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)',
      [key, JSON.stringify(value), Date.now()]
    );
  }

  private async fetchWithRateLimit(url: string): Promise<Response> {
    const now = Date.now();
    const waitTime = this.lastRequestTime + this.rateLimitMs - now;
    if (waitTime > 0) {
      await Bun.sleep(waitTime);
    }
    this.lastRequestTime = Date.now();

    const response = await fetch(url, { headers: this.headers });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} when fetching ${url}`);
    }
    return response;
  }

  /**
   * 1. Get comprehensive film data (Fixes year, director URLs, and HTML entities)
   */
  async getFilmData(slug: string): Promise<FilmData> {
    const cacheKey = `film:${slug}`;
    const cached = this.getCache<FilmData>(cacheKey);
    if (cached) return cached;

    const url = `${this.baseUrl}/film/${slug}/`;
    const response = await this.fetchWithRateLimit(url);

    let jsonLdRaw = '';
    let metaDescription = '';
    let ogTitle = '';

    const rewriter = new HTMLRewriter()
      .on('script[type="application/ld+json"]', {
        text(text) {
          jsonLdRaw += text.text;
        },
      })
      .on('meta[name="description"]', {
        element(el) {
          metaDescription = el.getAttribute('content') || '';
        },
      })
      .on('meta[property="og:title"]', {
        element(el) {
          ogTitle = el.getAttribute('content') || '';
        },
      });

    await rewriter.transform(response).text();

    const cleanedJson = jsonLdRaw
      .replace(/\/\* <!\[CDATA\[ \*\//g, '') .replace(/\/\* \]\]> \*\//g, '')
      .trim();

    if (!cleanedJson) {
      throw new Error(`Could not extract JSON-LD metadata for slug: ${slug}`);
    }

    const ld = JSON.parse(cleanedJson);

    // Extract year from releasedEvent, or fallback to og:title "Parasite (2019)"
    let releaseYear: number | null = null;
    const rawDate = ld.releasedEvent?.[0]?.startDate || ld.dateCreated;
    if (rawDate) {
      releaseYear = parseInt(String(rawDate).slice(0, 4), 10);
    } else {
      const yearMatch = ogTitle.match(/\((\d{4})\)/);
      if (yearMatch) releaseYear = parseInt(yearMatch[1], 10);
    }

    const result: FilmData = {
      name: ld.name || slug,
      year: releaseYear,
      slug,
      url: ld.url || url,
      description: decodeHtmlEntities(metaDescription),
      posterUrl: ld.image || '',
      directors: (ld.director || []).map((d: any) => ({
        name: d.name,
        url: d.sameAs
          ? d.sameAs.startsWith('http')
            ? d.sameAs
            : `${this.baseUrl}${d.sameAs}`
          : undefined,
      })),
      genres: ld.genre || [],
      rating: {
        average: ld.aggregateRating?.ratingValue ?? null,
        count: ld.aggregateRating?.ratingCount ?? null,
      },
    };

    this.setCache(cacheKey, result);
    return result;
  }

  /**
   * 2. Get a user's recent watched films, ratings, & posters via RSS
   */
  async getUserRecentActivity(username = 'your-own-username', limit = 10): Promise<UserActivity[]> {
    const cacheKey = `rss:${username}:${limit}`;
    const cached = this.getCache<UserActivity[]>(cacheKey);
    if (cached) return cached;

    const url = `${this.baseUrl}/${username}/rss/`;
    const response = await this.fetchWithRateLimit(url);
    const xml = await response.text();

    const items: UserActivity[] = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match: RegExpExecArray | null;

    while ((match = itemRegex.exec(xml)) !== null && items.length < limit) {
      const block = match[1];
      const getTag = (tag: string) => {
        const m = block.match(
          new RegExp(`<${tag}>(?:<!\\[CDATA\\[)?([\\s\\S]*?)(?:\\]\\]>)?<\\/${tag}>`)
        );
        return m ? m[1].trim() : '';
      };

      const filmTitle = getTag('letterboxd:filmTitle');
      if (!filmTitle) continue;

      const yearRaw = getTag('letterboxd:filmYear');
      const ratingRaw = getTag('letterboxd:memberRating');
      const link = getTag('link');
      const descriptionHtml = getTag('description');

      // Extract poster image from RSS <description> CDATA
      const imgMatch = descriptionHtml.match(/<img\s+src="([^"]+)"/);
      // Extract film slug from user review link: https://letterboxd.com/pedroamaral/film/listen-2014/1/#
      const slugMatch = link.match(/\/film\/([^\/]+)\//);

      items.push({
        title: decodeHtmlEntities(getTag('title')),
        filmTitle: decodeHtmlEntities(filmTitle),
        filmYear: yearRaw ? parseInt(yearRaw, 10) : null,
        slug: slugMatch ? slugMatch[1] : '',
        userRating: ratingRaw ? parseFloat(ratingRaw) : null,
        watchedDate: getTag('letterboxd:watchedDate'),
        posterUrl: imgMatch ? imgMatch[1] : '',
        link,
      });
    }

    this.setCache(cacheKey, items);
    return items;
  }

  /**
   * 3. Search films by query
   */
  async searchFilms(query: string, limit = 10): Promise<SearchResult[]> {
    const cacheKey = `search:${query}:${limit}`;
    const cached = this.getCache<SearchResult[]>(cacheKey);
    if (cached) return cached;

    const url = `${this.baseUrl}/search/films/${encodeURIComponent(query)}/`;
    const response = await this.fetchWithRateLimit(url);

    const results: SearchResult[] = [];
    let currentResult: Partial<SearchResult> | null = null;
    let captureTitle = false;
    let captureYear = false;
    let captureDirector = false;

    const rewriter = new HTMLRewriter()
      .on('ul.results > li', {
        element() {
          if (currentResult?.name && results.length < limit) {
            results.push(currentResult as SearchResult);
          }
          currentResult = { name: '', year: '', slug: '', url: '', director: '' };
        },
      })
      .on('span.film-title-wrapper > a', {
        element(el) {
          if (!currentResult) return;
          const href = el.getAttribute('href') || '';
          currentResult.url = `https://letterboxd.com${href}`;
          currentResult.slug = href.split('/').filter(Boolean)[1] || '';
          captureTitle = true;
        },
        text(text) {
          if (captureTitle && currentResult) {
            currentResult.name += text.text;
            if (text.lastInTextNode) captureTitle = false;
          }
        },
      })
      .on('span.film-title-wrapper > small.metadata > a', {
        element() {
          captureYear = true;
        },
        text(text) {
          if (captureYear && currentResult) {
            currentResult.year += text.text;
            if (text.lastInTextNode) captureYear = false;
          }
        },
      })
      .on('p.film-metadata > a', {
        element() {
          captureDirector = true;
        },
        text(text) {
          if (captureDirector && currentResult) {
            currentResult.director += text.text;
            if (text.lastInTextNode) captureDirector = false;
          }
        },
      });

    await rewriter.transform(response).text();

    if (currentResult?.name && results.length < limit) {
      results.push(currentResult as SearchResult);
    }

    const cleaned = results.map((r) => ({
      ...r,
      name: decodeHtmlEntities(r.name.trim()),
      year: r.year.trim(),
      director: decodeHtmlEntities(r.director.trim()),
    }));

    this.setCache(cacheKey, cleaned);
    return cleaned;
  }
}

if (import.meta.main) {
  const scraper = new BunLetterboxdScraper({
    cachePath: '/Volumes/X-Drive/cache.sqlite',
    cacheTtlSeconds: 3600,
  });

  console.log('1. Testing getFilmData("incendies")...');
  console.log(await scraper.getFilmData('incendies'));

  console.log('\n2. Testing getUserRecentActivity("your-own-username")...');
  console.log(await scraper.getUserRecentActivity('your-own-username', 5));
}
