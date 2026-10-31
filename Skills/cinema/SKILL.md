---
name: cinema
description: Look up a film. Tries Letterboxd's public film page (JSON-LD only, no account or watch history) and falls back to Wikipedia when Letterboxd is blocked or its search page has no server-rendered results. Use when the user asks about a movie, wants a poster, or needs year/director/rating facts.
metadata:
  homepage: https://github.com/google-ai-edge/gallery/tree/main/skills
---

# Film Digest

Film facts for a small model. Letterboxd is attempted first. Its search HTML is
client-rendered (a plain fetch often contains zero `/film/<slug>/` links) and the
film page does not send CORS headers, so the Gallery webview frequently cannot
read it. When that happens the script falls back to Wikipedia, which is CORS-open.
**Never present a Wikipedia blurb as a Letterboxd rating.**

No user account, watch history, or list data is touched.

## Instructions

Call `run_js` with script name `index.html` and `data` as ONE of:

- Search: `{"action":"search","query":"parasite 2019"}`
  Returns up to 6 rows. A row with `slug` is Letterboxd. A row with `page` and
  `source:"wikipedia"` is not — pass `page` to `action:film` as `title`.
- Letterboxd detail: `{"action":"film","slug":"parasite-2019"}`
  Only when search returned a slug. `parasite` is a different film from
  `parasite-2019`. Do not invent slugs.
- Wikipedia detail: `{"action":"film","title":"Parasite (2019 film)"}`
  Use the `page` string from search. `rating_out_of_5` will be null.

Do NOT scrape user profiles or lists.

## Failure rules

| Returned `error` contains | Do this |
|---|---|
| `HTTP 403` or `CORS` on Letterboxd | Do not retry that URL. If search already returned a Wikipedia `page`, call `action:film` with `title`. Otherwise say Letterboxd is blocked. |
| `HTTP 404` on film | Slug is wrong. Re-run search. Do not guess `parasite` vs `parasite-2019`. |
| `empty LD+JSON` | Page layout changed or the body was a challenge page. Say so. Do not fabricate a rating. |
| `no search results` | Try a shorter title once. Then stop. |

## Response style

- Search: bullet list. Letterboxd rows as `- Title — slug`. Wikipedia rows as `- Title — wikipedia`.
- Letterboxd film: title + year, director, rating (`2.4/5`), poster URL on its own line.
- Wikipedia film: title, one-sentence description, poster URL. Say the rating is not from Letterboxd.
- Total ≤ 120 words.

## Examples

- "Tell me about Parasite (2019)"
- "Find the poster for Spirited Away"
- "What's Letterboxd's rating for There Will Be Blood?"
