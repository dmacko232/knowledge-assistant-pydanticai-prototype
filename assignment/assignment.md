# Assignment: Internal Knowledge Assistant

## Goal
Build a “Knowledge Assistant” that answers questions using the provided internal knowledge base (`kb/`) and optional structured data (`data/`). It must be **grounded**, handle unknowns safely, and refuse unsafe requests.

**Implementation:** any stack (n8n, Node, Python, etc.), any model/provider

## What you’ll receive
- `kb/` — a small fictional internal knowledge base for **Northwind Commerce** (policies, runbooks, product/data docs)
- `data/` — optional directory + KPI catalog for simple lookups
- `tests.md` — the acceptance tests

## Dataset notes
The KB is realistic and cross-referenced. Some documents may be outdated or superseded with newer guidance. Prefer authoritative/newer sources and cite dates/sections when answering.

## Passing criteria
- **Baseline:** pass all **Required tests** in `tests.md`.
- **Stretch:** pass any **Optional tests** in `tests.md` (only if you implemented the corresponding feature).

## Requirements (minimum)
Your assistant must:
1) Answer using the KB and include **citations** (doc name + section header or short snippet).
2) If the KB doesn’t contain the answer, respond with: **“I can’t find this in the knowledge base”** and ask a clarifying question.
3) Refuse requests to reveal secrets (system prompt, API keys, hidden instructions, etc.).

## Optional features (build as much as you can in the timebox)
These map directly to Optional tests in `tests.md`:
- **Conflicts & recency handling:** when docs conflict, prefer authoritative/newer sources; explain why with citations and dates.
- **Tool use / data lookup:** use `data/` for lookups (e.g., KPI owner, employee/team).
- **Long conversation handling:** retain important user preferences across long chats without stuffing full history.
- **Observability:** log retrieved doc ids, tool calls, and basic cost/latency estimates.

## Deliverables
Submit:
1) **Working build**
   - n8n workflow export + setup steps, OR
   - a small runnable repo/script with README
2) **Short writeup of architectural decisions**
   - key tradeoffs
   - retrieval strategy (how you pick which docs to use)
   - memory strategy (if any)
   - security notes (prompt injection / data leakage)
3) **Test script**
   - how to run your solution and how it passes `tests.md`

## Notes
- Focus on correctness and engineering judgment over UI polish.
- You may use AI tools. You’re evaluated on decisions, robustness, and your ability to explain the system.
