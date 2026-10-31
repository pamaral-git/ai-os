---
name: feed-reader
description: Universal RSS/Atom feed reader and article extractor, with a built-in Nowflation inflation preset and Google News per-ticker search. Use when the user asks for news, a feed, a blog's latest posts, today's inflation number, or what the press is saying about a stock. Supports multi-turn agent runs: fetch a feed, then drill into one item, then read the linked article, in separate tool calls.
metadata:
  homepage: https://github.com/google-ai-edge/gallery/tree/main/skills
---

# Feed Reader

A feed runtime for on-device agents. Fetches RSS 2.0, Atom, RDF, and JSON feeds,
normalizes them to a compact item list, extracts readable article text, and ships
with two presets: **Nowflation** (US inflation open data) and **Google News**
(per-ticker press coverage). All parsing and truncation happen in the webview.

## Instructions

Call the `run_js` tool with script name `index.html` and `data` as ONE of these
JSON objects. Pick exactly one action; do not invent fields.

- Fetch a feed: `{"action":"fetch","url":"<feed url or subscription name>","limit":8,"since":"2026-10-01"}`
  `limit` 1–15, default 8. `since` is optional ISO date (`YYYY-MM-DD`).
- Discover a feed: `{"action":"discover","url":"<site homepage>"}`
  Returns every `<link rel="alternate" type="application/rss+xml">` and common
  feed paths (`/feed`, `/rss`, `/feed.xml`, `/atom.xml`).
- Read an article: `{"action":"read","url":"<article url>","max_chars":1200}`
  Fetches the page, strips nav/scripts/ads, returns clean readable text.
- Per-ticker news: `{"action":"news","ticker":"AAPL","limit":5}`
  Uses Google News RSS search. This is press coverage, **not** a quote.
  Also supports freeform queries via `q` or `query`.
- Nowflation preset: `{"action":"nowflation","what":"brief"|"headline"|"series"|"gaps","series":"GASREGW","limit":5}`
  `what` defaults to `brief`. `series` is required only for `what:"series"`.
- Save a subscription: `{"action":"subscribe","url":"<feed url>","name":"<short name>"}`
- Remove a subscription: `{"action":"unsubscribe","name":"<short name>"}`
- List subscriptions and cache: `{"action":"list"}`

## Multi-turn agent contract (READ THIS FIRST)

This skill is designed for **multi-turn agent runs**, not single-shot answers.
One user request will often need 2–4 tool calls. You are expected to loop.

1. **You may call this skill up to 4 times per user request.** Stop at 4 and
   answer with whatever you have.
2. **After every call, read the returned `_next` field.** It is a verb phrase.
   - `_next` starting with `ANSWER` → stop calling tools, write the answer.
   - `_next` starting with a verb (`fetch`, `read`, `discover`, `nowflation`,
     `news`) → make that next call before answering.
3. **Never guess a URL.** If you do not know the feed, call `action:"discover"`
   on the homepage first; it returns real feed URLs.
4. **Drill down in a second call.** If the user asks *why* something moved or
   wants detail on one story, call `action:"read"` on that item's `link`. Do not
   paraphrase a headline as if you had read the article.
5. **Carry state in the conversation, not in the payload.** The script caches
   feeds for 10 minutes, so calling `fetch` again on the same URL is cheap. You
   do not need to pass previous results back in.
6. **If `calls_remaining` in the response is 0, answer immediately.** Do not
   call again even if `_next` suggests it.

## Failure rules

| Returned `error` contains | Do this |
|---|---|
| `CORS` or `proxy` | The proxy chain is exhausted. Tell the user the feed host blocks cross-origin reads and suggest trying the site directly. Do not retry the same URL. |
| `HTTP 404` on feed | Wrong URL. Run `action:"discover"` on the site root once. If still 404, report honestly. |
| `HTTP 403` | Bot protection. Do not retry. Offer `action:"read"` on a specific article instead. |
| `not a feed` | The URL returned HTML, not XML. Try `action:"discover"` on it, or `action:"read"`. |
| `empty feed` | The feed exists but has no items in the window. Widen `since` or drop it. |
| `empty article` | Readability failed. Return the item's `description` from the feed instead and say the full text was unavailable. |

## Response style

- News / feed: bullet list `- Title — date` with the link, max 6 bullets.
- Nowflation: lead with the number (`Realtime 3.19% YoY, CPI Gauge 3.38%, gap −0.32pp`),
  then one sentence on what moved. Always credit `Nowflation (nowflation.com)`.
- Article: 3–5 sentence summary. Never invent quotes.
- Total ≤ 150 words unless the user asked for a digest.

## Examples that trigger this skill

- "What's the latest on Nowflation?"
- "Is inflation up today?"
- "Show me the last posts from <blog>"
- "What's the press saying about NVDA?"
- "Read me that article about the CPI print"
- "Subscribe to that feed so I can ask again later"
