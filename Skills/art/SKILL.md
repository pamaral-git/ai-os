---
name: art
description: Search public-domain art (Art Institute of Chicago, Met Museum), poems (PoetryDB, Poetry Foundation, Lyrikline, Tumblr, Poets.org, Poetry in Translation), and full public-domain books (Project Gutenberg). Ingest Gutenberg books into on-device RAG. Use when the user asks about paintings, sculptures, poems, or classic books, or wants to read/quote from a public-domain work.
metadata:
  author: github.com/pamaral-git
  modified: 1-November-2026
---

# Culture Shelf

Curated public-domain culture: art, poetry, and full books. All endpoints are
free and keyless. Full book text is ingested into localStorage under
`agt:rag:culture:pg<id>` so a `rag-memory` skill that scans `agt:rag:*` can search it later.

## Sources Summary

**Art:**
- Art Institute of Chicago API (artic)
- Met Museum API (met)

**Poetry:**
- PoetryDB - JSON API (poetrydb)
- Having a Poem With You (Tumblr) - RSS feed (tumblr)
- Poetry Foundation - HTML scraping (poetryfoundation)
- Lyrikline - HTML scraping (lyrikline)
- Poets.org (Academy of American Poets) - HTML scraping (poetsorg)
- Poetry in Translation - HTML scraping (poetryintranslation)

**Books:**
- Project Gutenberg - HTML scraping (pg)

## Instructions

Call `run_js` with script name `index.html` and `data` as ONE of:

- Search art: `{"action":"search","source":"artic"|"met","query":"van gogh","n":5}`
  `source` defaults to `artic`. `n` ≤ 8.
- Artwork detail: `{"action":"work","source":"artic"|"met","id":<numeric id>}`
  Returns compact digest (title, artist, date, medium, image URL). No full JSON.
- Poem: `{"action":"poem","by":"title"|"author"|"random","q":"Ozymandias","n":1,"source":"poetrydb"|"tumblr"|"poetryfoundation"|"lyrikline"|"poetsorg"|"poetryintranslation"}`
  `by` defaults to `title`. `n` ≤ 10, defaults to 3 for search, 1 for random.
  `source` defaults to `poetrydb`.
  
  Poetry sources:
  - **poetrydb**: Fast JSON API. Rejects `/poems`, `.json`, and `?fields=` with a 405 *inside a 200 body*. Uses bare paths only (`/title/X`, `/author/Y`, `/random/N`).
  - **tumblr**: Fetches from `havingapoemwithyou.tumblr.com` RSS feed. Free, keyless, no rate limits.
  - **poetryfoundation**: Scrapes `https://www.poetryfoundation.org/`. May be blocked by Cloudflare in some environments.
  - **lyrikline**: Scrapes `https://www.lyrikline.org/en/`. May be blocked in some environments.
  - **poetsorg**: Scrapes `https://poets.org/` (Academy of American Poets). Free, keyless.
  - **poetryintranslation**: Scrapes `https://www.poetryintranslation.com/`. Free, keyless.
  
- Book search: `{"action":"book","query":"romeo and juliet"}`
  Scrapes Gutenberg's ebook catalog and returns `{id, title, author}` rows.
- Book ingest: `{"action":"ingest","id":1513}`
  Downloads Gutenberg plain text (strips license header/footer), chunks it, and
  stores it. Returns a 1-line preview only.

Do NOT call any other tool. Do NOT invent artwork IDs, poem lines, or book text.

## Failure rules

| Symptom | Do this |
|---|---|
| Artic returns HTTP 403, or `Failed to fetch` | The script already retries once against the Met. If both fail, say both museums are briefly blocked. |
| PoetryDB `405` in the error string | Do not rewrite the URL yourself. Tell the user the poem lookup failed. Do not invent lines. |
| Poetry Foundation / Lyrikline / Poets.org / Poetry in Translation `CORS` or `Failed to fetch` | These sites may be behind Cloudflare or other protection. In a webview, this may work; if not, fall back to PoetryDB or Tumblr. |
| Tumblr RSS `Failed to fetch` | Tumblr RSS feed should always work. If blocked, it's a network issue. |
| Gutenberg `HTTP 404` | Ebook ID is wrong. Run `action:book` first. |
| `text too large` | Books over ~1.2 MB are skipped. Ask for a shorter work. |
| `CORS` or `Failed to fetch` on Gutenberg | Gutenberg does not send CORS headers. The Gallery webview cannot read it. Say that plainly. Art and poems still work. Do not invent the book. |

## Response style

- Art: 1-line title + artist + year, then the thumbnail URL on its own line.
- Poem: quote the first 6 lines inside a code fence, then attribution. For Tumblr/Poetry Foundation/Lyrikline/Poets.org/Poetry in Translation, use the content field for the poem text.
- Book ingest: `"Ingested pg<id> (<n> chunks). Ask me anything about it."` — nothing else.
- Total ≤ 140 words unless the user asked to see the poem in full.

## Examples

- "Find me Van Gogh paintings with images"
- "Show me Ozymandias by Shelley"
- "Show me a random poem from Tumblr"
- "Find poems by Emily Dickinson from Poetry Foundation"
- "Get me a random poem from Lyrikline"
- "Find poems by Robert Frost from Poets.org"
- "Show me a random poem from Poetry in Translation"
- "What's a good Met Museum Monet?"
- "Ingest Romeo and Juliet so I can ask about it"
