/* Shared toolkit for Gallery JS skills.
 * Browser webview: window.AgentTools. Also attached to globalThis for a node harness.
 * Each skill copies this file to scripts/tools.js. If you already maintain a richer
 * toolkit, merge scripts/mcp-call.append.js into it instead of replacing yours. */
(function (root) {
  'use strict';

  const Tools = {};

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  Tools.cap = function (s, n) {
    s = s == null ? '' : String(s);
    n = n || 200;
    return s.length <= n ? s : s.slice(0, n - 1).trimEnd() + '…';
  };

  Tools.clampInt = function (v, min, max, fallback) {
    const n = parseInt(v, 10);
    if (!isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  };

  Tools.ok = function (data) {
    return Object.assign({ ok: true }, data || {});
  };

  Tools.err = function (msg, hint) {
    return { ok: false, error: String(msg || 'error'), hint: hint || undefined };
  };

  Tools.describeError = function (e) {
    const msg = e && e.message ? String(e.message) : String(e);
    let hint = 'Do not invent data. Tell the user this call failed.';
    if (/HTTP 404/.test(msg)) hint = 'Not found. Check the id, slug, or path. Do not guess a replacement.';
    else if (/HTTP 403/.test(msg)) hint = 'HTTP 403. Do not retry the same URL in a loop.';
    else if (/HTTP 429/.test(msg)) hint = 'Rate limited. Do not loop; retry in about a minute.';
    else if (/HTTP 5\d\d/.test(msg) || /MCP error/.test(msg)) hint = 'Backend error. Use the skill fallback if it has one; otherwise stop.';
    else if (/CORS\/proxy|Failed to fetch|NetworkError|CORS|Load failed|TypeError/.test(msg)) hint = 'CORS/proxy exhausted or the host blocked the webview. Do not retry the same URL.';
    else if (/not a feed/.test(msg)) hint = 'That URL is not a feed. Run action discover on the site, or action read if it is an article.';
    else if (/empty feed/.test(msg)) hint = 'The feed has no items in this window. Widen since or drop it. Do not invent items.';
    else if (/empty article/.test(msg)) hint = 'Use the feed item summary. Do not invent the article body.';
    else if (/timeout/i.test(msg)) hint = 'The request timed out. Retry once only if the skill failure table says to.';
    return { msg: msg.slice(0, 300), hint: hint };
  };

  /* CORS-aware fetch. Throws Error('HTTP <status> <url>') so skill tables can match. */
  Tools.fetchText = async function (url, opts) {
    opts = opts || {};
    const timeoutMs = opts.timeoutMs || 15000;
    const retries = opts.retries == null ? 1 : opts.retries;
    const method = opts.method || 'GET';
    let lastErr;
    for (let attempt = 0; attempt <= retries; attempt++) {
      const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeoutMs);
      try {
        const res = await fetch(url, {
          method: method,
          headers: opts.headers || {},
          body: opts.body,
          signal: ctrl ? ctrl.signal : undefined,
        });
        const text = await res.text();
        if (!res.ok) {
          const err = new Error('HTTP ' + res.status + ' ' + url);
          err.status = res.status;
          const retryable = attempt < retries && (res.status === 429 || res.status >= 500);
          if (retryable) {
            lastErr = err;
            await sleep(350 * (attempt + 1));
            continue;
          }
          throw err;
        }
        return text;
      } catch (e) {
        const aborted = e && (e.name === 'AbortError' || /aborted/i.test(String(e.message || '')));
        lastErr = aborted ? new Error('timeout after ' + timeoutMs + 'ms') : e;
        const msg = String(lastErr && lastErr.message || lastErr);
        const retryable = attempt < retries && method === 'GET' && !/HTTP 4/.test(msg);
        if (!retryable) throw lastErr;
        await sleep(350 * (attempt + 1));
      } finally {
        clearTimeout(timer);
      }
    }
    throw lastErr;
  };

  Tools.fetchJson = async function (url, opts) {
    const text = await Tools.fetchText(url, opts);
    try { return JSON.parse(text); }
    catch (e) { throw new Error('non-JSON from ' + url); }
  };

  /* Parse SSE `data:` frames into JSON values (or raw strings). */
  Tools.sseData = function (raw) {
    const out = [];
    String(raw || '').split(/\n\n+/).forEach(function (block) {
      const lines = block.split(/\n/).filter(function (l) { return l.indexOf('data:') === 0; });
      if (!lines.length) return;
      const payload = lines.map(function (l) { return l.slice(5).trim(); }).join('\n');
      if (!payload || payload === '[DONE]') return;
      try { out.push(JSON.parse(payload)); }
      catch (_) { out.push(payload); }
    });
    return out;
  };

  /* MCP JSON-RPC over streamable HTTP. DeepWiki and the Yahoo gateway both
   * answer tools/call without a prior initialize. Default timeout is 45s
   * because ask_wiki_question often exceeds 20s. Pass opts.timeoutMs to override.
   * opts is the optional 5th argument so the 4-arg form in older skills still works. */
  Tools.mcpCall = async function (url, method, params, id, opts) {
    id = id || 1;
    opts = opts || {};
    const body = JSON.stringify({ jsonrpc: '2.0', id: id, method: method, params: params || {} });
    const raw = await Tools.fetchText(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
      },
      body: body,
      timeoutMs: opts.timeoutMs || 45000,
      retries: opts.retries == null ? 0 : opts.retries,
    });

    function unwrap(r) {
      if (!r || typeof r !== 'object') throw new Error('MCP: empty response frame');
      if (r.error) throw new Error('MCP error: ' + (r.error.message || JSON.stringify(r.error)));
      const result = r.result;
      if (result && result.isError) {
        const msg = (result.content || []).map(function (c) { return c && c.text; }).filter(Boolean).join(' ');
        throw new Error('MCP error: ' + (msg || 'tool error').slice(0, 220));
      }
      return result;
    }

    try {
      const j = JSON.parse(raw);
      if (j && (j.result !== undefined || j.error)) return unwrap(j);
    } catch (e) {
      if (e && /MCP/.test(String(e.message || ''))) throw e;
    }

    const frames = Tools.sseData(raw).filter(function (f) { return f && typeof f === 'object'; });
    const hit = frames.find(function (f) { return f.id === id || f.id === String(id); }) || frames[frames.length - 1];
    return unwrap(hit);
  };

  Tools.chunkSentences = function (text, size) {
    size = size || 500;
    const sentences = String(text || '').replace(/\s+/g, ' ').match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
    const chunks = [];
    let buf = '';
    sentences.forEach(function (p) {
      p = p.trim();
      if (!p) return;
      if (buf && (buf.length + 1 + p.length) > size) {
        chunks.push(buf);
        buf = p;
      } else {
        buf = buf ? buf + ' ' + p : p;
      }
      while (buf.length > size * 1.5) {
        chunks.push(buf.slice(0, size).trim());
        buf = buf.slice(size).trim();
      }
    });
    if (buf) chunks.push(buf);
    return chunks;
  };

  /* Prefix agt: once. rag-memory scans localStorage keys agt:rag:* . */
  function storageKey(key) {
    key = String(key);
    return key.indexOf('agt:') === 0 ? key : 'agt:' + key;
  }
  Tools.kv = {
    set: function (key, value) {
      const store = root.localStorage;
      if (!store) throw new Error('localStorage unavailable');
      store.setItem(storageKey(key), JSON.stringify(value));
    },
    get: function (key, fallback) {
      const store = root.localStorage;
      if (!store) return fallback === undefined ? null : fallback;
      const raw = store.getItem(storageKey(key));
      if (raw == null || raw === '') return fallback === undefined ? null : fallback;
      try { return JSON.parse(raw); } catch (_) { return fallback === undefined ? null : fallback; }
    },
    keys: function (prefix) {
      const store = root.localStorage;
      if (!store) return [];
      const want = prefix ? storageKey(prefix) : 'agt:';
      const out = [];
      for (let i = 0; i < store.length; i++) {
        const k = store.key(i);
        if (k && k.indexOf(want) === 0) out.push(k.slice(4));
      }
      return out;
    },
  };

  Tools.now = function () { return new Date().toISOString(); };

  /* Strips scripts/styles and tags, decoding HTML entities properly */
  Tools.htmlToText = function (html) {
    const s = String(html || '');
    if (!s) return '';
    if (typeof DOMParser === 'undefined') {
      return s
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, ' ')
        .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, ' ')
        .replace(/<[^>]+>/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;|&apos;/g, "'")
        .replace(/\s+/g, ' ')
        .trim();
    }
    const doc = new DOMParser().parseFromString('<div>' + s + '</div>', 'text/html');
    const kill = doc.querySelectorAll('script,style,noscript');
    for (let i = 0; i < kill.length; i++) kill[i].remove();
    return ((doc.body && doc.body.textContent) || '').replace(/\s+/g, ' ').trim();
  };

  /* Extracts readable article text from HTML */
  Tools.extractArticle = function (html) {
    if (typeof DOMParser === 'undefined') {
      return { title: '', text: Tools.htmlToText(html) };
    }
    const doc = new DOMParser().parseFromString(String(html || ''), 'text/html');
    const kill = doc.querySelectorAll('script,style,noscript,nav,footer,header,aside,form,iframe,svg,button');
    for (let i = 0; i < kill.length; i++) kill[i].remove();
    const og = doc.querySelector('meta[property="og:title"]');
    const tw = doc.querySelector('meta[name="twitter:title"]');
    const titleEl = doc.querySelector('title');
    const h1 = doc.querySelector('h1');
    const title = (og && og.getAttribute('content')) ||
      (tw && tw.getAttribute('content')) ||
      (titleEl && titleEl.textContent) ||
      (h1 && h1.textContent) || '';

    const rootNode = doc.querySelector('article') ||
      doc.querySelector('[role="main"]') ||
      doc.querySelector('main') ||
      doc.querySelector('.post-content') ||
      doc.querySelector('.entry-content') ||
      doc.querySelector('#content') ||
      doc.body;

    let text = '';
    if (rootNode) {
      const paragraphs = Array.from(rootNode.querySelectorAll('p'))
        .map(function (p) { return (p.textContent || '').replace(/\s+/g, ' ').trim(); })
        .filter(function (t) { return t.length > 20; });
      if (paragraphs.length >= 2) {
        text = paragraphs.join('\n\n');
      } else {
        text = ((rootNode && rootNode.textContent) || '').replace(/\s+/g, ' ').trim();
      }
    }
    return { title: title.replace(/\s+/g, ' ').trim(), text: text };
  };

  /* Keyless CORS proxy chain for feeds and web content */
  Tools.PROXIES = [
    function (u) { return 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u); },
    function (u) { return 'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(u); },
    function (u) { return 'https://corsproxy.io/?' + encodeURIComponent(u); },
  ];

  /* Try direct fetch first, then fall through the proxy chain and feed fallbacks. */
  Tools.fetchViaProxy = async function (url, opts) {
    opts = opts || {};
    try {
      const text = await Tools.fetchText(url, { timeoutMs: opts.timeoutMs || 12000, retries: 0 });
      return { text: text, via: 'direct' };
    } catch (directErr) {
      let last = directErr;
      for (let i = 0; i < Tools.PROXIES.length; i++) {
        try {
          const proxyUrl = Tools.PROXIES[i](url);
          const text = await Tools.fetchText(proxyUrl, { timeoutMs: 15000, retries: 0 });
          if (text && text.length > 40) return { text: text, via: 'proxy' };
        } catch (e) {
          last = e;
        }
      }

      /* Feed-specific fallback to rss2json if this is a feed request */
      if (opts.feed || /\.(xml|rss|atom)$/i.test(String(url).split('?')[0]) || /\/(feed|rss|atom)(\.xml)?$/i.test(String(url).split('?')[0])) {
        const api = 'https://api.rss2json.com/v1/api.json?count=15&rss_url=' + encodeURIComponent(url);
        try {
          const text = await Tools.fetchText(api, { timeoutMs: 15000, retries: 0 });
          const j = JSON.parse(text);
          if (j && j.status === 'ok') {
            return { text: text, via: 'rss2json', json: j };
          }
        } catch (e) {
          last = e;
        }
      }

      const n = new Error('CORS/proxy exhausted for ' + String(url).split('?')[0]);
      n.status = 0;
      n.cause = last;
      throw n;
    }
  };

  /* JSON through the same proxy chain */
  Tools.fetchJsonThroughProxy = async function (url, opts) {
    const { text } = await Tools.fetchViaProxy(url, opts);
    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error('invalid JSON from ' + String(url).split('?')[0]);
    }
  };

  function directChildText(el, names) {
    const want = {};
    names.forEach(function (n) { want[n.toLowerCase()] = true; });
    let best = '';
    const children = el.children || el.childNodes || [];
    for (let i = 0; i < children.length; i++) {
      const node = children[i];
      if (node.nodeType && node.nodeType !== 1) continue; // element only
      const ln = (node.localName || node.tagName || '').toLowerCase();
      if (!want[ln]) continue;
      const t = (node.textContent || '').trim();
      if (t.length > best.length) best = t;
    }
    return best;
  }

  function findLink(el) {
    const links = el.getElementsByTagName ? el.getElementsByTagName('link') : [];
    if (!links || !links.length) {
      const direct = directChildText(el, ['link']);
      return direct || '';
    }
    // Prefer rel="alternate" or links with href that are not rel="self"
    for (let i = 0; i < links.length; i++) {
      const l = links[i];
      const rel = (l.getAttribute && l.getAttribute('rel') || '').toLowerCase();
      if (rel === 'alternate') {
        const href = l.getAttribute('href');
        if (href) return href.trim();
      }
    }
    for (let i = 0; i < links.length; i++) {
      const l = links[i];
      const rel = (l.getAttribute && l.getAttribute('rel') || '').toLowerCase();
      if (rel !== 'self') {
        const href = l.getAttribute && l.getAttribute('href');
        if (href) return href.trim();
        const text = (l.textContent || '').trim();
        if (text && /^https?:\/\//i.test(text)) return text;
      }
    }
    const fallback = links[0];
    return (fallback.getAttribute && fallback.getAttribute('href')) || (fallback.textContent || '').trim();
  }

  /* RSS 2.0 / Atom 1.0 / RDF / JSON Feed -> normalized items */
  Tools.parseFeed = function (input) {
    // 1. JSON Feed or rss2json object/string
    if (typeof input === 'object' && input !== null) {
      return parseJsonFeed(input);
    }
    if (typeof input === 'string' && /^\s*\{/.test(input)) {
      try {
        const j = JSON.parse(input);
        return parseJsonFeed(j);
      } catch (_) {
        // Fall through to XML parsing
      }
    }

    // 2. XML Feed (RSS 2.0, Atom 1.0, RDF)
    if (typeof DOMParser === 'undefined') throw new Error('not a feed: no XML parser');
    const doc = new DOMParser().parseFromString(String(input || ''), 'text/xml');
    if (doc.querySelector('parsererror')) throw new Error('not a feed: XML parse error');

    const channel = doc.getElementsByTagName('channel')[0] ||
      doc.getElementsByTagName('feed')[0] ||
      doc.documentElement;
    if (!channel) throw new Error('not a feed: no channel or feed element');

    const nodes = [];
    const items = channel.getElementsByTagName('item');
    const entries = channel.getElementsByTagName('entry');
    for (let i = 0; i < items.length; i++) nodes.push(items[i]);
    for (let i = 0; i < entries.length; i++) nodes.push(entries[i]);
    if (!nodes.length) throw new Error('empty feed: no item or entry nodes');

    const out = nodes.map(function (el) {
      const rawDesc = directChildText(el, ['summary', 'description', 'content', 'encoded']);
      const dateRaw = directChildText(el, ['pubDate', 'published', 'updated', 'dc:date', 'date']);
      let d = null;
      if (dateRaw) {
        const p = Date.parse(dateRaw);
        if (!isNaN(p)) d = new Date(p);
        else {
          const p2 = Date.parse(dateRaw.replace(' ', 'T'));
          if (!isNaN(p2)) d = new Date(p2);
        }
      }
      const link = findLink(el);
      return {
        title: Tools.cap(Tools.htmlToText(directChildText(el, ['title'])) || '(untitled)', 160),
        link: link,
        date: d && !isNaN(d.getTime()) ? d.toISOString().slice(0, 10) : null,
        summary: Tools.cap(Tools.htmlToText(rawDesc), 420),
        id: directChildText(el, ['guid', 'id']) || link || '',
      };
    }).filter(function (it) { return it.title || it.link; });

    out.sort(function (a, b) { return String(b.date || '').localeCompare(String(a.date || '')); });
    const channelTitle = directChildText(channel, ['title']) || (doc.documentElement && directChildText(doc.documentElement, ['title'])) || '';
    return { title: Tools.cap(Tools.htmlToText(channelTitle), 120), items: out };
  };

  function parseJsonFeed(j) {
    if (!j) throw new Error('not a feed: empty JSON');
    if (j.status === 'error') throw new Error('not a feed: ' + (j.message || 'error'));
    const rawItems = j.items || [];
    if (!rawItems.length) throw new Error('empty feed: no items in feed');
    const feedTitle = (j.feed && j.feed.title) || j.title || '';
    const items = rawItems.map(function (it) {
      const d = it.pubDate || it.date_published || it.date || null;
      let iso = null;
      if (d) {
        const p = Date.parse(d);
        if (!isNaN(p)) iso = new Date(p).toISOString().slice(0, 10);
      }
      return {
        title: Tools.cap(Tools.htmlToText(it.title || '(untitled)'), 160),
        link: it.link || it.url || '',
        date: iso,
        summary: Tools.cap(Tools.htmlToText(it.description || it.summary || it.content_text || it.content || ''), 420),
        id: it.guid || it.id || it.link || it.url || '',
      };
    }).filter(function (it) { return it.title || it.link; });

    items.sort(function (a, b) { return String(b.date || '').localeCompare(String(a.date || '')); });
    return { title: Tools.cap(Tools.htmlToText(feedTitle), 120), items: items };
  }

  /* CSV -> rows of objects (quote-aware and BOM-safe) */
  Tools.parseCSV = function (text) {
    const s = String(text || '').replace(/^\uFEFF/, '');
    const rows = [];
    let row = [];
    let cur = '';
    let q = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q) {
        if (c === '"') {
          if (s[i + 1] === '"') { cur += '"'; i++; }
          else q = false;
        } else cur += c;
      } else if (c === '"') q = true;
      else if (c === ',') { row.push(cur); cur = ''; }
      else if (c === '\n') {
        row.push(cur); cur = '';
        if (row.some(function (x) { return x.trim() !== ''; })) rows.push(row);
        row = [];
      } else if (c !== '\r') cur += c;
    }
    if (cur !== '' || row.length) {
      row.push(cur);
      if (row.some(function (x) { return x.trim() !== ''; })) rows.push(row);
    }
    if (rows.length < 2) return [];
    const head = rows[0].map(function (h) {
      return h.trim().replace(/^["']|["']$/g, '').toLowerCase();
    });
    return rows.slice(1).map(function (r) {
      const o = {};
      head.forEach(function (h, i) { o[h] = (r[i] || '').trim(); });
      return o;
    });
  };

  function smaSeries(values, window) {
    const out = [];
    let sum = 0;
    for (let i = 0; i < values.length; i++) {
      sum += values[i];
      if (i >= window) sum -= values[i - window];
      out.push(i >= window - 1 ? sum / window : null);
    }
    return out;
  }

  function rsi(values, period) {
    period = period || 14;
    if (!values || values.length <= period) return null;
    let gains = 0;
    let losses = 0;
    for (let i = 1; i <= period; i++) {
      const d = values[i] - values[i - 1];
      if (d >= 0) gains += d; else losses -= d;
    }
    let avgG = gains / period;
    let avgL = losses / period;
    for (let i = period + 1; i < values.length; i++) {
      const d = values[i] - values[i - 1];
      const g = d > 0 ? d : 0;
      const l = d < 0 ? -d : 0;
      avgG = (avgG * (period - 1) + g) / period;
      avgL = (avgL * (period - 1) + l) / period;
    }
    if (avgL === 0) return 100;
    const rs = avgG / avgL;
    return 100 - (100 / (1 + rs));
  }

  Tools.stats = {
    pctChange: function (last, first) {
      if (last == null || first == null || !isFinite(last) || !isFinite(first) || first === 0) return null;
      return (last / first - 1) * 100;
    },
    smaSeries: smaSeries,
    rsi: rsi,
  };

  root.AgentTools = Tools;
})(typeof window !== 'undefined' ? window : globalThis);
