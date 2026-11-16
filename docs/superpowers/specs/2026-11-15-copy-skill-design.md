# Copy Kit — independent copy skill (design)

**Date:** 2026-11-15
**Status:** approved in chat (Dann), awaiting review of this spec
**Repo:** creative-kit-generator · branch `main`

## Problem / context

The content feature (team spreadsheet + Review copy panel) was **removed** from main
(commit `3195e3d`) at Dann's request: copy/content must be an **independent system**,
not a step inside the visual kit. He wants that system as a **second skill in the
same repository**, with its own start command, to save effort (shared installer and
infra). The online hub is parked (branch `online-collaboration`); this
design does NOT depend on it.

## What it is

A guided, local, agent-driven flow — a mirror of the visual kit, but **copy only**:

1. **Lean onboarding** in the browser: **briefing** + a **text field** where the user
   pastes **example texts**. **No logo, no brandbook, no file refs, no
   photos/videos.** Same step-by-step style as the visual, different slots.
2. **Generation (agent):** the agent reads the briefing + examples and **writes the copy** — both for
   **PPC (text only)** and for **overlay** (hook/kicker/program/CTA). High volume
   (concepts × axes × destinations × versions). The kit **validates the shape**, does not invent copy
   (normalize pattern: agent generates, Python validates).
3. **Table review** in the browser: each row approve / reject / redo+note.
   Mark-then-batch discipline; **nothing non-approved moves forward**. A table because the
   volume can be large.
4. **Delivery:** everything approved → the agent generates a **file for download** (spreadsheet) and/or
   drops it in the **delivery folder on the Desktop** (`~/Desktop/Copy Kit/<campaign>/`), same
   pattern as the visual (Open folder button).
5. **Independent:** the visual kit stays intact. The copy delivers its own file; there is
   no coupling or automatic import by the visual (handoff = a future step, if he wants it).

## Command / skill contract

- The `campaign-kit` plugin gains a second command: **`/campaign-kit:copy`** (`commands/copy.md`)
  and a second skill **`skills/copy-kit/SKILL.md`**. The current `/campaign-kit:start` stays
  visual-only.
- **One flow at a time in the browser UI:** each command starts its own server on
  loopback; run one or the other, never both in the same session. (Visual wizard 8766 /
  review 8765; copy uses its own ports starting at 8767/8768 — no collision.)
- CLI: new **`copy`** subcommand with actions (`python3 -m kit.cli copy <action> <path>`):
  - `copy onboard <inbox>` — lean scaffold (briefing.md + examples.txt) + light wizard.
  - `copy plan <campaign>` — prints briefing + examples + destinations/kinds vocabulary
    for the agent to author the copy.
  - `copy validate <campaign>` — validates `copy.json` (canonical shape; gaps/errors).
  - `copy review <campaign>` — review table server (opens the browser; shortcut
    `OPEN-COPY-REVIEW.html`).
  - `copy deliver <campaign>` — exports approved → spreadsheet(s) + Desktop folder.

## Data model (`campaigns/<slug>/copy.json`)

List of rows; each row:

```json
{
  "id": "k01",
  "destination": "ppc",            // "ppc" | "overlay"
  "concept": "clean",
  "axis": "default",               // optional
  "kind": "headline",              // ppc: headline|description|primary_text
                                    // overlay: hook|kicker|program|cta
  "text": "...",
  "lang": "en",                    // en
  "use": "both",                   // optional for overlay: image|ppc|both (future routing)
  "status": "pending",             // pending|approved|rejected|redo
  "note": "",
  "origin": "agent",               // always agent here (generated); sheet if it came from a spreadsheet
  "updated_at": "ISO-UTC",
  "updated_by": "name"
}
```

- `copy validate`: valid destinations/kinds/status/lang; non-empty `text`; unique ids.
  Error → nothing written (atomic). Gaps (e.g. concept without a hook) become a question.
- `decide(id, status, note)`: marks the row (intent). `redo` requires a note. Re-stamps
  `updated_at`/`updated_by`. **The agent never marks `approved`** — it's the user's.
- Re-ingest/new generation preserves decisions by id when the text did not change; new text
  goes back to `pending`.

## Delivery (file)

`copy deliver` exports **only the approved**:
- **PPC** → spreadsheet(s) in import format (Meta primary text/headline; Google RSA
  headlines ≤30 / descriptions ≤90), CSV + XLSX. URL/budget/IDs blank (PPC team).
- **Overlay** → concept × axis × kind spreadsheet (hook/kicker/program/CTA), CSV + XLSX.
- Goes to `~/Desktop/Copy Kit/<campaign>/` + **Open folder** button and **download** in the UI.
- RSA character limits validated at export (notice, not gatekeeper).

## What it reuses from the kit (DRY)

- `kit/i18n.py`, the HTTP server pattern from `kit/ui.py` (`_serve`,
  `ThreadingHTTPServer`, browser opening, HTML shortcut).
- Desktop delivery folder pattern + `_open_folder`.
- `openpyxl`/csv already used by `ppc.py` for the XLSX.
- Installer (`install.sh`/`Install.bat`) and managed venv — identical.

## What is NEW (independent of the visual)

- `kit/copy.py` — model + validate + decide + export (without touching the visual campaign/render/ppc).
- `kit/copy_ui.py` — light wizard (briefing + examples) + table page + routes
  (`/state`, `/decide`, `/deliver`, `/download`, `/open-folder`). Own server.
- `commands/copy.md`, `skills/copy-kit/SKILL.md`.
- `copy` subcommand in `kit/cli.py` (additive only; does not change the existing ones).
- README.md (English-only): "Copy Kit" section + `/campaign-kit:copy` command.
- Tests for the copy module (TDD).

## Inviolable rules (inherited)

- **Never invent copy** — the agent generates from the briefing + examples; the kit validates the shape.
- **Nothing non-approved ships** — deliver/export only with `approved`.
- **The agent never marks approved** — the decision is the user's in the table.
- **Local files and control** — no public URL/deploy without asking.
- **One flow at a time in the UI.**

## Honest limits

- The creativity (writing the copy) belongs to the agent; Python validates the shape and exports.
- No logo/brandbook: the voice comes from the briefing + pasted examples.
- Independent of the visual: does not render images, does not talk to providers, does not touch the visual PPC.