# Content Review Step — Design

**Date:** 2026-11-13
**Status:** design approved in chat; spec pending user review
**Builds on:** `2026-11-12-content-team-design.md` (sheet ingest, `use` routing, apply)

## Context

The content-team step ships base copy from the content team's spreadsheet into
`content.json`, the agent adapts/expands it per briefing section 11, and
`content --apply` merges it into `campaign.json.copy`, which render and PPC read.
Two gaps remain:

1. Nobody approves the AI-suggested copy before it reaches images and PPC sheets.
2. The content team works online (SharePoint); they need a way to approve or retake
   proposals without opening the local browser UI.

This design adds a review step for copy that mirrors the image-piece review
(mark intent → batch execute → agent fulfills the redo loop), plus a spreadsheet
round-trip as a second approval channel for the team.

## Decisions (brainstorming, 2026-11-13)

1. **Placement:** a Copy panel in the existing review page (step 5), shown whenever
   `content.json` exists. The agent opens the review right after adapting copy,
   before render; pieces appear in the same tab later. One browser tab per campaign.
2. **Scope:** rows exactly as ingested from the sheet start approved (`origin: sheet`)
   — the team's own copy is trusted. Rows the agent adds or changes start pending
   (`origin: agent`). Any row can still be rejected/redo from the UI.
3. **Granularity:** one card per row/version (base and each version separately),
   matching the granularity of the PPC rows they become.
4. **Mechanism:** apply-approved-only. `content.json` is the proposal store with
   per-row status; the Apply button merges only approved rows into
   `campaign.json.copy`. Render and PPC are untouched — they keep reading
   `campaign.json.copy`, so unapproved copy cannot reach an image or a sheet.
5. **Team channel:** export a review spreadsheet → team fills decisions → user
   imports it back. Decisions only; copy text edits in the return sheet are ignored.
   The kit never talks to SharePoint (standing rule); the user carries the file.

## Data model

`content.json` keeps its top level (`source`, `rows`, `gaps`, `errors`). Each row
gains four fields:

| field    | values                                        | set by |
|----------|-----------------------------------------------|--------|
| `id`     | `c01`, `c02`, … sequential, stable until re-ingest | ingest |
| `origin` | `sheet` \| `agent`                            | ingest / agent |
| `status` | `pending` \| `approved` \| `rejected` \| `redo` | ingest / UI / import / agent |
| `note`   | free text (redo/reject note)                  | UI / import; cleared by agent on fulfill |

- **Ingest** stamps sheet rows `origin: sheet, status: approved`.
- **Agent contract (AGENTS.md):** rows added or edited while adapting are
  `origin: agent, status: pending`; new rows take the next free sequential id.
  Fulfilling a `rejected`/`redo` row means rewriting its copy fields, setting
  `status: pending` and clearing `note`. The agent never sets `approved` itself.
- **Re-ingest** (new sheet) rebuilds ids and resets all decisions — documented.
- **`validate(rows, concepts)`** additionally rejects unknown or missing
  `status`/`origin` values (PT errors, same contract as today; missing means
  re-run ingest).
- **`apply(camp)`** merges only `status: approved` rows: first per
  (`axis` or `default`, `concept`) = base entry, further approved rows = `versions`
  in row order. Returns `{errors, merged, pending}`; validation errors block;
  `merged: 0` is a notice, not an error. Unrelated existing copy entries preserved.

## Browser UI (review page)

Same review server and 4s poll; four new endpoints. No stepper change.

- **Visibility:** `/state` in review mode gains `content: {rows, counts}` when
  `content.json` exists; without it the page is exactly as today.
- **Panel** above the pieces grid: title, live counts (pending/approved/rejected/redo),
  and three actions — **Export review sheet** (download), **Import decisions**
  (file picker, `.xlsx`/`.csv`), **Apply approved copy** (primary).
- **Chips:** status filter + concept filter, same toggle behavior as pieces filters.
- **Cards** (one per row, existing card styling): hook as title; kicker · program ·
  CTA meta line; tags for concept, axis, `use`, lang, origin (`sheet` grey / `AI`
  blue) and status (piece status colors); warn callout with `note` when
  rejected/redo. Buttons **approve / reject / redo** (redo opens the existing note
  dialog) → `POST /copy-decision {id, status, note}`. Clicks only mark.
- **Approved rows leave the grid** into a compact "Approved copy (n)" list
  (hook + concept/axis/use tags), each with a ↺ reopen button back to `pending`.
- **Apply** → `POST /copy-apply` → callout in the panel: "N copies applied ·
  M still awaiting review", or the validation errors in red; toast confirms.
  While `pending > 0`, a warn line states the campaign still runs on the previous
  copy (no silent gate).
- **Redo loop:** when the agent rewrites a row back to `pending`, the poll redraws
  the card in place — same live loop as images.
- **Endpoints:** `/copy-decision` (400 on unknown id or status), `/copy-apply`,
  `/copy-export` (GET download; 404 without `content.json`), `/copy-import`
  (POST raw file bytes; 400 on bad extension or parse failure).
- **i18n:** all new strings PT/EN via the catalog (`rv.copy.*`).

## Spreadsheet round-trip (team approval)

- **Export** (`content --export`, panel button): writes `content_review.xlsx` into
  `<delivery>/content_review/` (Desktop delivery folder, created on demand; same
  handoff place as `ppc/`, reachable via "Abrir pasta"), overwritten on each
  export. Two tabs:
  - **Review:** `id, concept, axis, hook, kicker, program, cta, use, lang, origin,
    status, decision, note` — `decision`/`note` empty for the team to fill.
  - **Instructions** (PT/EN per UI lang): fill `decision` with `approve` / `reject` /
    `redo` (also `aprovar` / `rejeitar` / `refazer`); blank = no change; copy text
    edits are ignored; send the file back to be imported.
- **Import** (`content --import <path>`, panel file picker): parses `.xlsx`/`.csv`
  with the existing alias normalization plus `decision` aliases
  (`decisao`, `aprovacao`, `decision`, `approval`) and `note` aliases
  (`nota`, `observacao`, `comment`, `note`). Matches rows by `id`. Files over 20 MB
  are rejected (400/413, same cap as briefing docs). Validates every
  row first; any unknown id, invalid decision value, or missing `id` column blocks
  the whole import with per-row PT errors — nothing written. On success writes only
  `status`/`note` into `content.json` and returns
  `{approved, rejected, redo, unchanged}` counts.
- Browser and sheet write the same fields; last write wins (documented).
- After import the panel poll shows the team's decisions; **Apply approved copy**
  remains the single gate into `campaign.json.copy`.

## Error handling

- Import: atomic block on unknown id / bad decision / missing `id` column.
- Apply: row validation errors block; zero approved = notice.
- `/copy-decision`: unknown id or status → 400. Redo note optional (as pieces).
- `/copy-export` without `content.json` → 404 (button hidden anyway).
- `/copy-import`: unsupported extension or unparseable file → 400.
- Import parsing reuses the read-only-workbook `close()` pattern (Windows locks).
- Re-ingest resets decisions; documented in AGENTS.md and Instructions tab.
- Render/PPC never gate on review state; the panel warn line keeps "still on
  previous copy" visible.

## Verification

- New `tests/test_content_review.py` (stdlib unittest): ingest stamping;
  status/origin enum validation; apply-approved-only + versions + pending count;
  export tabs/columns; import round-trip (approve / reject / redo+note / blank /
  unknown id / bad value / missing id column); the four endpoints over a real local
  server; `/state` carrying content; review page panel markers PT/EN.
- Full existing suite stays green (27 tests at design time).
- Live browser pass on a fixture campaign: approve, reject, redo-with-note, apply,
  export → fill decisions → import, watching the poll update; PT and EN.

## Docs

- `AGENTS.md`: content section gains the review contract (statuses, origin, agent
  fulfill loop, apply as the only gate) and the round-trip; pipeline step 3b notes
  "review copy before render".
- `skills/campaign-kit/SKILL.md`: steps 5b and 7 mention the Copy panel.
- `kit/i18n.py`: PT/EN keys for every new string.

## Out of scope

- Copy text edits via the return sheet (decisions only).
- Any SharePoint API integration (kit stays local; user carries the file).
- Rendered-image previews inside copy cards.
- Reviewing manual `campaign.json.copy` entries that never came from a sheet.
- Changes to the piece review/deliver flow.