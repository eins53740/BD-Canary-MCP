Canary MCP Server — Semantic→Tag Resolution

Purpose: This document instructs an LLM (and the humans guiding it) to design and implement an MCP (Model Context Protocol) server that converts natural‑language requests into real Canary Historian tag paths and executes data reads via the Canary Read API (Views).

0) TL;DR for the LLM

Parse the user prompt → timeframe, aggregates, plant/area context, and signal keywords.

Normalise text (lowercase, accent fold, replace _→ , strip punctuation) and expand synonyms.

Discover candidates using Canary browse endpoints (and/or path+deep+search shortcut if supported).

Rank candidates with fuzzy scoring + path context boosts.

Build a /getTagData (or /getTagData2) request with start/end, aggregate, quality and paging.

Return: (a) top matched fully‑qualified tags, (b) the executed/read data (or a ready request), and (c) assumptions made.

1) Scope & Non‑Goals

In scope

NL → tag resolution (single or top‑K)

Time/aggregate parsing and mapping

Canary tag browsing & searching

Read data with continuation paging and quality handling

Clear disambiguation flows

Out of scope (can be future work)

Write/insert operations

Complex analytics beyond Canary aggregates

Cross‑historian federation

2) Key API Surfaces (Read API over Views)

Browse: browseNodes, browseTags
Explore hierarchy and enumerate tags under a path.

Read: getTagData and getTagData2
Retrieve raw/aggregated values with startTime, endTime, aggregateName, includeQuality, maxSize, and continuationToken handling.

Aggregates: getAggregates
Discover supported aggregate names/descriptions.

Auth: Token (e.g., Authorization: Bearer <apiToken>). Keep base URL configurable.

Note: Some Canary versions accept path + deep + search directly in getTagData, letting the server resolve matching tags. Prefer this if available; otherwise, fall back to browse + explicit tags[].

3) High‑Level Architecture
MCP Client (LLM)
   │  natural language
   ▼
MCP Server (this project)
   ├─ Parser: time, aggregate, entities, keywords
   ├─ Normaliser: lowercase, accent fold, '_'→' ', punctuation
   ├─ Resolver: browse/search Canary; gather candidates
   ├─ Ranker: fuzzy score + path context boosts
   ├─ Builder: construct getTagData(/2) requests
   ├─ Reader: execute calls; handle paging & quality
   └─ Formatter: results + assumptions + alternatives


External: Canary Views Read API (HTTPS)
4) Configuration

CANARY_BASE_URL (e.g., https://<views-host>/readapi)

CANARY_API_TOKEN (secret)

DEFAULT_VIEW_ROOTS (e.g., Views/Outao/, Views/Maceira-Liz/)

PLANT_TIMEZONE (e.g., Europe/Lisbon)

CACHE_TTL for browse and aggregates (e.g., 15–30 min)

Request limits: MAX_PAGE_SIZE, MAX_TAGS_PER_QUERY

5) Semantic Parsing
5.1 Normalisation

Lowercase; trim; keep /, -, _, .

Replace _ with space to match human‑named tags: s = s.replace("_", " ")

Accent fold (e.g., Outão→Outao)

Tokenise by words and numbers

5.2 Entities & Dictionaries

Maintain lightweight dictionaries for:

Sites/Plants: Outao, Maceira‑Liz, ...

Units/Areas: Kiln, Raw Mill, Preheater, Cooler, ...

Signals: Speed, Temperature, Vibration, Flow, Pressure, ...

Synonyms (examples):
Speed ↔ RPM, Temperature ↔ Temp, Power ↔ kW, Load ↔ Amps

5.3 Time Window Extraction

Recognise: last 24h, yesterday, today, this week, last week,
from 2025‑10‑01 00:00 to 2025‑10‑02 00:00, 2025‑10‑10 08:00..18:00.

Convert to absolute ISO‑8601 (startTime, endTime) in plant timezone.

If unspecified: default to last 8h, but return a note with the assumption.

5.4 Aggregate Intent

Map words → Canary aggregates:
average→Average, min→Minimum, max→Maximum, last→Last, sum→Total, interpolated→Interpolated.

Validate against getAggregates; fallback: Interpolated for trend, Last for snapshot.

6) Tag Discovery Strategies
Strategy A — Hierarchical Browse (deterministic)

Build candidate paths from entities, e.g., Views/Outao/Line 1/Kiln/.

browseNodes(path, deep=false) to list subfolders.

browseTags(path, deep=true) to collect tags under promising nodes.

Filter by keywords/synonyms; send to ranker.

Strategy B — Read with Server‑Side Search (opportunistic)

If supported, call getTagData with:

{
  "path": "Views/Outao/Line 1/Kiln/",
  "deep": true,
  "search": "main drive speed",
  "startTime": "now-24h",
  "endTime": "now",
  "aggregateName": "Average"
}

The server returns data for matching tags; extract hit tags from response metadata.

Strategy C — Hybrid

Use B first for speed; if zero/low hits, fall back to A.

7) Fuzzy Ranking

Inputs: tagName, tagPath, tokens, context.

Scoring (suggested weights)

Exact token match in name: +4

Startswith / substring in name: +3 / +2

Edit distance ≤2 for a token: +1

Path context match (site/area/line folders): +2 each

Synonym match (e.g., RPM for speed): +1

Type/Unit compatibility (numeric vs boolean): +2 else −∞ for incompatible aggregates

Return top‑K (default 5). If best score < threshold, trigger disambiguation.

Normalisation applied to both sides: lowercase, accent fold, _→ .

8) Request Builder
Inputs

tags[] or path+deep+search

startTime, endTime (ISO‑8601 or now-24h style)

Optional: aggregateName, includeQuality, maxSize

Choosing endpoint

Prefer getTagData (simpler); use getTagData2 if you need specific pagination semantics.

Example — explicit tags
POST {BASE}/getTagData
Authorization: Bearer <token>
Content-Type: application/json


{
  "tags": [
    "Views/Outao/Line 1/Kiln/MainDrive/Speed"
  ],
  "startTime": "now-24h",
  "endTime": "now",
  "aggregateName": "Average",
  "includeQuality": true
}
Example — path search (if supported)
POST {BASE}/getTagData
Authorization: Bearer <token>
Content-Type: application/json


{
  "path": "Views/Outao/Line 1/Kiln/",
  "deep": true,
  "search": "main drive speed",
  "startTime": "now-24h",
  "endTime": "now",
  "aggregateName": "Average",
  "includeQuality": true
}
9) Pagination & Continuation

Honour continuationToken returned by the server.
Loop: include the token in the next request until it is absent.

Limit per‑call payload (maxSize) if needed; stream partial results to the client.

10) Quality & Type Handling

Include includeQuality=true for diagnostics.

If user requests “good data only”, filter records where quality ≠ Good.

For boolean tags + “average/min/max”: reject or coerce to Last.

For sparse signals: consider Interpolated or return sampling guidance.

11) Errors, Assumptions, Disambiguation
Errors

Auth (401/403) → instruct user to configure token/permissions on the View(s).

404 on paths → provide nearest existing path from browseNodes cache.

Invalid aggregate → suggest nearest valid aggregate from getAggregates.

Assumptions (always echo)

Plant/site (e.g., assumed Outao)

Line/unit (e.g., Line 1 / Kiln)

Timezone (e.g., Europe/Lisbon)

Default timeframe (e.g., last 8h)

Disambiguation (fast path)

Present top‑K tags with scores + short path snippet and ask the user to confirm one.

12) Caching Strategy

Cache browseNodes and browseTags results per path (TTL 15–30 min).

Cache getAggregates for 24h or until server restarts.

Negative cache for 5 min when a path doesn’t exist.

13) Minimal Server Skeletons
13.1 TypeScript (Node) — Outline
import express from "express";
import fetch from "node-fetch";


const BASE = process.env.CANARY_BASE_URL!; // https://<host>/readapi
const TOKEN = process.env.CANARY_API_TOKEN!;


const headers = { "Authorization": `Bearer ${TOKEN}`, "Content-Type": "application/json" } as const;


const app = express();
app.use(express.json());


// --- helpers ---
const norm = (s: string) => s.normalize("NFKD").toLowerCase().replace(/_/g, " ").replace(/[\p{Diacritic}]/gu, "");


async function browseTags(path: string, deep = true) {
  const res = await fetch(`${BASE}/browseTags`, { method: "POST", headers, body: JSON.stringify({ path, deep }) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}


async function getAggregates() {
  const res = await fetch(`${BASE}/getAggregates`, { method: "POST", headers, body: JSON.stringify({}) });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}


app.post("/resolve", async (req, res) => {
  const { query, hintPaths = ["Views/Outao/"], startTime, endTime, aggregateName } = req.body;
  const tokens = norm(query).split(/\W+/).filter(Boolean);


  let candidates: { name: string; path: string }[] = [];
  for (const p of hintPaths) {
    const out = await browseTags(p, true);
    const tags = out?.tags ?? [];
    for (const t of tags) candidates.push({ name: t.name, path: t.path });
  }


  const score = (name: string, path: string) => {
    const n = norm(name), p = norm(path);
    let s = 0;
    for (const tok of tokens) {
      if (n === tok) s += 4; else if (n.startsWith(tok)) s += 3; else if (n.includes(tok)) s += 2; else if (lev(n, tok) <= 2) s += 1; // lev: implement/edit-dist
      if (p.includes(tok)) s += 2;
    }
    return s;
  };


  const ranked = candidates
    .map(c => ({ ...c, score: score(c.name, c.path) }))
    .filter(c => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);


  res.json({ tokens, ranked, assumed: { hintPaths, startTime, endTime, aggregateName } });
});


app.post("/read", async (req, res) => {
  const body = req.body; // expect { tags: string[], startTime, endTime, aggregateName }
  const first = await fetch(`${BASE}/getTagData`, { method: "POST", headers, body: JSON.stringify(body) });
  const json = await first.json();
  res.json(json);
});


app.listen(8765);
13.2 Python — Outline
import unicodedata, requests, os
BASE = os.environ["CANARY_BASE_URL"]
HDRS = {"Authorization": f"Bearer {os.environ['CANARY_API_TOKEN']}", "Content-Type": "application/json"}


def norm(s: str) -> str:
    s = s.replace("_", " ").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def browse_tags(path: str, deep: bool=True):
    r = requests.post(f"{BASE}/browseTags", headers=HDRS, json={"path": path, "deep": deep})
    r.raise_for_status(); return r.json()


# scoring & resolve functions … (mirror the TS version)

These skeletons intentionally omit MCP transport glue. Wrap them in your MCP framework of choice (e.g., server exposing tools endpoints callable by the LLM).

14) Tool Contract (for MCP)

Expose three tools for the agent:

canary.search_tags

{
  "type": "function",
  "name": "canary.search_tags",
  "description": "Browse Canary Views and return ranked tag candidates for a natural-language query.",
  "parameters": {
    "type": "object",
    "properties": {
      "nl_query": {"type": "string"},
      "hint_paths": {"type": "array", "items": {"type": "string"}},
      "k": {"type": "integer", "default": 5}
    },
    "required": ["nl_query"]
  }
}

canary.resolve_tags — orchestrates parse→rank→choose

{
  "type": "function",
  "name": "canary.resolve_tags",
  "description": "Return top-K fully-qualified tag paths and the assumptions made.",
  "parameters": {
    "type": "object",
    "properties": {
      "nl_query": {"type": "string"},
      "hint_paths": {"type": "array", "items": {"type": "string"}},
      "k": {"type": "integer", "default": 3}
    },
    "required": ["nl_query"]
  }
}

canary.read — executes the read

{
  "type": "function",
  "name": "canary.read",
  "description": "Execute getTagData(/2) with tags or path+search and return values with continuation handling.",
  "parameters": {
    "type": "object",
    "properties": {
      "tags": {"type": "array", "items": {"type": "string"}},
      "path": {"type": "string"},
      "deep": {"type": "boolean"},
      "search": {"type": "string"},
      "startTime": {"type": "string"},
      "endTime": {"type": "string"},
      "aggregateName": {"type": "string"},
      "includeQuality": {"type": "boolean", "default": true},
      "maxSize": {"type": "integer"}
    },
    "required": ["startTime", "endTime"]
  }
}
15) Prompting Guide for the LLM

Always echo assumptions and offer the top‑K tags when confidence is low.

When the user references underscore names (e.g., Main_Drive_Speed), try also with spaces (Main Drive Speed).

Ask for site/line/unit when ambiguous; suggest examples from known paths.

If no time is given, default to last 8h, but show how to change it.

If the aggregate is incompatible with tag type, propose Last or Interpolated.

Example system prompt snippet

You are a Canary Historian assistant. Convert natural language into Canary tag paths.
1) Normalise text (lowercase, accent fold, '_'→' '). 2) Build hint paths from entities.
3) Use browse/search to find tags. 4) Rank candidates with fuzzy scoring.
5) Choose top tags and execute getTagData with start/end and an aggregate.
Always state assumptions and show alternatives when confidence is low.
16) Test Plan (Smoke & E2E)

Aggregates: Fetch getAggregates and verify mapping of average/min/max/last/interpolated.

Browse: From Views/Outao/, browseNodes then browseTags(deep=true) returns non‑empty lists.

Underscore heuristic: Queries containing Main_Drive_Speed also match Main Drive Speed.

Path search (if supported): getTagData with path+deep+search returns data for at least one known tag.

Pagination: Force a large window and verify continuationToken loop completes.

Quality filter: Return only Good quality when requested.

Disambiguation: For generic query “kiln temperature”, server returns top‑K with scores and asks follow‑up.

17) Example User Flows
A) “Average kiln main drive speed last 24h for Outão line 1”

Parse: site=Outao, unit=Kiln, signal=Speed, window=now-24h..now, agg=Average.

Resolve: search under Views/Outao/Line 1/Kiln/.

Read: return average series + tag path, e.g., Views/Outao/Line 1/Kiln/MainDrive/Speed.

B) “Raw mill fan rpm yesterday”

Tokens: raw mill, fan, rpm, time=yesterday 00:00..24:00

Hint paths: Views/<Plant>/Raw Mill/

Rank candidates: prefer names containing fan + rpm.

18) Security & Observability

Store the API token securely; never log secrets.

Respect Canary permissions—no attempt to bypass view access.

Enable request/response logging with PII‑safe redaction (paths and tag names are OK; values are OK; tokens are not).

Add metrics: resolve latency, hit‑rate, top‑K score distribution, continuation counts.

19) Deliverables Checklist




20) Notes for Production Readiness

Add rate limiting and exponential backoff on HTTP 429/5xx.

Graceful degradation: when Canary is slow/unavailable, provide best‑effort tag resolution without reading.

Internationalisation: maintain synonym lists per language; accent folding already helps.

Version flags: feature‑detect path+deep+search support at startup.

Appendix A — Useful Synonym Seeds (extend as you learn)

speed: rpm, velocity

temperature: temp, T

power: kW, load

pressure: press, P

flow: f, q, qv

Appendix B — Example Disambiguation Payload (JSON)
{
  "query": "kiln main drive speed last 24h",
  "assumptions": {
    "site": "Outao",
    "unit": "Kiln",
    "tz": "Europe/Lisbon",
    "window": ["now-24h", "now"],
    "aggregate": "Average"
  },
  "candidates": [
    {"path": "Views/Outao/Line 1/Kiln/MainDrive/Speed", "score": 17},
    {"path": "Views/Outao/Line 1/Kiln/MainDrive/RPM",   "score": 16},
    {"path": "Views/Outao/Line 1/Drive/Speed",           "score": 9}
  ]
}

End of document.