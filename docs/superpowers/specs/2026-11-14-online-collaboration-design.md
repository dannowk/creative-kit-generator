# Online Collaboration — Hub + Local Agents (Slice 1: Content Handoff) — Design

**Date:** 2026-11-14
**Status:** direction approved in chat; spec pending user review
**Builds on:** `2026-11-12-content-team-design.md` (sheet ingest, `use` routing),
`2026-11-13-content-review-design.md` (Copy panel, per-row statuses, apply gate,
decision-sheet round-trip)

## Context

Today every collaboration step is carried by files outside the kit: the content
team ships base copy via SharePoint/e-mail, approves via an exported decision
spreadsheet, and only Dann runs production. He wants the collaboration steps
online — a common path where the whole team uploads content, reviews and confirms
step by step — while graphic-piece production (AI via agent + MCP) stays on his
machine. The content team must be able to upload content files from another
computer, ask their own agent for adjustments per the briefing, and push the
approved result back up for Dann to continue production.

## Decisions (brainstorming, 2026-11-14)

1. **Topology: hosted app + local agents** (his option 1). A hosted hub holds
   shared campaign state; each participant runs the kit + their own agent locally.
2. **The content team gets "the visual step, but for content"** on THEIR machine
   via THEIR agent: the existing local **Revisar copy** panel is that step. They
   ask their agent for adjustments per the briefing, approve in the panel, and
   push the result up to hand off to Dann.
3. **Hub = common path only, never AI.** The hub stores campaigns, files and
   decisions. It does not generate copy, render, or talk to any provider. All AI
   runs on each participant's local agent.
4. **Platform: Qoder Sites** (his choice): backend functions (JSON API), database
   + migrations, storage (files), access policy + invited visitors (team access),
   secrets (tokens).
5. **Decomposition:** slice 1 (this spec) = hub + kit sync client + content
   handoff. Slice 2 (separate spec, later) = piece review/delivery online,
   onboarding wizard online, PPC sheets in the hub, real-time updates.

## Architecture

```
content teammate's machine                Dann's machine
┌──────────────────────────┐              ┌──────────────────────────┐
│ kit + their agent        │              │ kit + his agent + MCP    │
│ hub pull → Revisar copy  │              │ hub pull → content --apply│
│ panel (adjust/approve)   │              │ → plan/assets/render/video│
│ → hub push               │              │ → review → deliver       │
└────────────┬─────────────┘              └────────────┬─────────────┘
             │  HTTPS (token per campaign)             │
             ▼                                         ▼
        ┌─────────────────────────────────────────────────┐
        │ hub (Qoder Sites) — source of truth              │
        │ campaigns · content_rows · decisions log · files │
        │ web UI: campaign list + content tab (no AI)      │
        └─────────────────────────────────────────────────┘
```

- **Hub is the source of truth; the local campaign folder is a working cache.**
- **Local-first, offline-tolerant:** the kit keeps working 100% locally without a
  hub (current flow untouched). The hub is an optional sync layer; nothing in the
  existing pipeline depends on it.
- **Agent-mediated** (same pattern as `drop_dir`/normalize): the Python client
  prepares and validates, the agent runs the command, the hub stores. Any agent
  (Claude, Qoder, Codex, …) can drive it — the kit speaks plain HTTPS, no
  agent-specific SDK.

## Hub data model

- `campaigns`: id (slug), name, concepts (requested concept list), created_at,
  owner. Concepts are set by the owner at creation and refreshed by Dann's push;
  they let `content.validate` run on machines that have no brand/assets.
- `content_rows`: campaign_id, id (`c01…`), concept, axis, hook, kicker, program,
  cta, use, lang, origin (`sheet|agent`), status
  (`pending|approved|rejected|redo`), note, updated_at, updated_by. Same row shape
  as local `content.json`, plus who/when.
- `decisions` (append-only log): campaign_id, row_id, action
  (decide/rewrite/upload/push), resulting status/note, who, when. Never
  overwritten — the history of who decided what survives every conflict.
- `files` (storage + index): campaign_id, name, kind (`briefing|content|support`),
  path, uploaded_by, uploaded_at. Slice 1 carries the base sheet, content support
  docs and `briefing.md`. The full online wizard is slice 2.
- **Access:** the owner (Dann) creates campaigns and generates the campaign
  token; teammates enter via Qoder Sites invited visitors and may edit/decide
  content. No kit-specific login.

## Sync contract (kit ↔ hub)

New CLI command `hub` (campaign is a path, like every other command):

```bash
python -m kit.cli hub campaigns/<slug> link --url <hub-url> --id <campaign-id> --token <token> [--who <name>]
python -m kit.cli hub campaigns/<slug> pull
python -m kit.cli hub campaigns/<slug> push
```

- **Local config:** `campaigns/<slug>/hub.json` = `{url, campaign_id, token, who}`.
  Gitignored (`campaigns/*/hub.json`); the token is never committed. `who` defaults
  to the OS username and stamps `updated_by`. The token is shown in the hub UI
  when the owner creates the campaign; the owner can regenerate it there
  (invalidating the previous one), then re-run `hub link`.
- **`pull`** downloads hub rows + files and merges them into the local folder
  (`content.json`, `content/`, briefing). It materializes the minimum needed for
  the Copy panel to work on a content-only machine (a minimal `campaign.json`
  with the campaign's concepts — no brand.yaml/assets/templates required).
  **Pull never applies copy** — `content --apply` remains a separate local act.
- **`push`** uploads local rows + new files; the hub merges and validates.
- **Merge by row id, symmetric in both directions:** the side with the newer
  `updated_at` wins per row; a tie goes to the hub. New rows are appended with the
  next free id. Push carries full row content (text + origin + status + note) —
  unlike the decision-sheet import, which applies decisions only — because an
  agent fulfilling a redo must be able to ship rewritten text.
- **Atomic validate:** the merge result passes `content.validate`; any error
  rejects the whole block, nothing is written (same guarantee as
  `import_decisions`).
- **Last-write-wins per row + log:** conflicts never block; the newest decision
  wins and the `decisions` log preserves history. No locks, no queues, no
  field-level text merging.
- **Files** follow the same rule: newer timestamp wins per file name
  (`uploaded_at` on the hub, file mtime on the kit side).
- **Local stamping:** the kit stamps `updated_at`/`updated_by` on every local row
  change (ingest, decide, rewrite, import) so merges can order edits.
- **Auth:** per-campaign token in the `Authorization: Bearer` header; the hub
  checks it against the stored value (Sites secret or hashed DB column — the plan
  verifies the exact Sites primitive). Missing/invalid token → 401.
- **Offline:** no `hub.json` or no network → `pull`/`push` fail with a clear
  PT/EN message; the local flow continues normally and no local work is lost.

## Role flows

**Content teammate (their machine, their agent):**
1. Install the kit (`install.sh` / `Instalar.bat` — same bootstrap, no admin).
2. Their agent links the campaign (`hub link` + `hub pull`) and opens the local
   review.
3. The **Revisar copy** panel is their visual step: they ask their agent for
   adjustments per the briefing; the agent rewrites (`origin: agent`,
   `status: pending`, note cleared); they approve/reject/redo in the panel.
4. `hub push` ships the reviewed copy up to the hub.

**Dann (his machine):**
1. `hub pull` brings the team's approved copy down.
2. `content --apply` merges only approved rows into `campaign.json.copy`
   (existing gate, unchanged).
3. Local pipeline as today: plan → assets → render + MCP → video → review →
   deliver. Pushing pieces to the hub is slice 2.

**No local agent (fallback):** any invited teammate opens the hub in a browser
and decides directly in the content table (approve/reject/redo + note) or uploads
the base sheet. The hub never rewrites copy — only local agents (or humans) do.

## Hub web UI (slice 1)

- Campaign list (owner creates; invitees see the campaigns they have access to).
- **Content tab** per campaign: base-sheet upload (+ support docs), copy table
  with status/concept filters, per-row approve/reject/redo+note (same semantics
  as the local panel: deciding only marks; applying happens locally in Dann's
  `content --apply`), origin and who/when visible per row.
- Base-sheet upload runs the same ingest contract as `kit.cli content`
  (canonical columns + PT/EN aliases): sheet rows enter `origin: sheet,
  status: approved` (the team's own copy is trusted). Re-uploading a base sheet
  rebuilds rows and resets decisions for that campaign — same semantics as local
  re-ingest — with a visible warning in the UI.
- PT/EN toggle like the kit (cookie).
- No AI, no render, no piece preview in slice 1.

## Invariants preserved

- Never invent copy; the agent never marks `approved` (user/team only).
- The kit never talks to SharePoint — the hub replaces the spreadsheet
  back-and-forth, not SharePoint.
- No AI/generation in the hub; provider cost stays a notice (not a gatekeeper)
  and only exists on the local agent.
- Files and control stay local: the hub is an optional layer; the Sites app is
  developed as a **draft** and published only with Dann's explicit OK
  (AGENTS.md rule 5). The hub URL lives in `hub.json`, never hardcoded.
- Batch review: deciding marks; executing is always a separate act (local apply).
- Cross-agent contract: AGENTS.md gains an optional "Hub" section; the
  no-terminal flow and every existing command keep working without a hub.

## Errors & limits

- Invalid sheet on upload → validate errors shown, nothing applied (atomic).
- Invalid/expired token → 401 + clear message; re-run `hub link`.
- Edit conflict → last-write-wins per row; the log keeps history; no
  field-level merge (YAGNI).
- Hub unreachable → clean failure; local work intact.
- A campaign the token doesn't match → 403/404, no data leak across campaigns.

## Testing

- `tests/test_hub.py` (stdlib unittest): merge by id/updated_at (tie → hub), new
  rows, atomic validate (error → nothing written), 401 without token, offline
  (no `hub.json` → clear error), pull↔push round-trip — all against a **local
  hub-stub** (`http.server` on 127.0.0.1 serving the same API shape). No real
  network in tests.
- Live manual pass (checklist in the plan): Sites draft, two roles in separate
  browsers (owner + invitee), upload → decide → pull → `content --apply` in the
  real kit.
- Regression: the current suite (52 tests) stays green; the hub-less local flow
  is unchanged.

## Out of scope (explicitly)

- Slice 2: pieces online (out/ + state.json), online wizard/onboarding, PPC
  sheets in the hub, real-time/websockets.
- Kit-specific auth (login/password), roles beyond owner/invitee.
- Decision-sheet import in the hub UI (the local round-trip already covers
  offline teams; online teams decide in the table).
- SharePoint/Graph integration, e-mail notifications, simultaneous
  field-level collaborative editing.