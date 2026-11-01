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
    else if (/Failed to fetch|NetworkError|CORS|Load failed|TypeError/.test(msg)) hint = 'Network or CORS blocked this host from the webview. Say so plainly.';
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
    get: function (key) {
      const store = root.localStorage;
      if (!store) return null;
      const raw = store.getItem(storageKey(key));
      if (!raw) return null;
      try { return JSON.parse(raw); } catch (_) { return null; }
    },
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
