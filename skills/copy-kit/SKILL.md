---
name: copy-kit
description: Use when the user wants to generate only the COPY of a campaign (text for PPC and overlay) from a briefing + example texts, with row-by-row approval in a browser table. Independent of the visual kit — no logo, brandbook or images. Drives everything without the user opening a terminal.
---

# copy-kit

Generates the copy locally: the agent writes from the briefing + examples, the kit validates
the shape and exports **only the approved** (Meta / Google RSA / overlay sheets). Review in a
browser **table** (approve/reject/redo+note per row). **The user does not open a
terminal or type a command — you run everything; they use the chat and the browser.**

Independent of `campaign-kit` (visual): does not touch the visual campaign/render/ppc, does not ask for
logo/brandbook/refs. **One flow at a time in the UI** — visual wizard 8766/review 8765; copy
uses 8767 (wizard) / 8768 (table). Do not start both in the same session.

## Steps

1. **Find the kit root** (`AGENTS.md` + `install.sh`). If it is not in the workspace,
   clone it yourself from `https://github.com/dannowk/creative-kit-generator` into
   `~/Documents/creative-kit-generator` — do not ask the user to clone.
2. **Create the folder automatically**: default `~/Desktop/my-campaign-copy` (or
   `~/Desktop/<brand>-copy` if they already said the name in the chat). Without asking for a path.
3. **Bootstrap + copy wizard in a single command**, in the background: `./install.sh <inbox> --copy`
   (Mac/Linux) or `Install.bat <inbox> --copy` (Windows). Downloads `uv` + managed Python 3.12
   without admin, installs the deps and **opens the copy wizard in the browser**,
   creating only `briefing.md` + `examples.txt` (no logo/brandbook/refs/photos/videos).
   `.venv/` already exists → just reopens the wizard.
4. **Announce in the chat** that the copy wizard opened; ask for the **briefing** (goal, audience,
   tone of voice, offer/product, concepts, axes, constraints, languages) and the **example
   texts** (a text field where they paste copy they like / want to use as a model). Mention
   that **each field has a drop zone**: they can drag a file with copy they already have —
   `.md`/`.txt` content goes into the field, any file lands in `attachments/` for you to read.
   Wait for the user's "ready".
5. **`copy plan <folder>`** prints the briefing + examples + **attached files** (if any) + the
   destinations/kinds vocabulary. **Read the attachments** (plain text directly; PDF/docx/image:
   extract with your tools) — they are part of the source material.
   **YOUR JOB:** author `<folder>/copy.json` = `{"concepts":[...], "rows":[...]}`.
   Each row: `id` (`k01`…, next free), `destination` (`ppc`/`overlay`), `concept`,
   `axis` (optional), `kind`, `text`, `lang` (`en`), `status:"pending"`,
   `origin:"agent"`, `updated_at` (ISO UTC now), `updated_by` (your name/user).
   - **ppc kinds:** `headline` (≤30 for Google RSA), `description` (≤90), `primary_text`.
   - **overlay kinds:** `hook`, `kicker`, `program`, `cta`.
   High volume: concepts × axes × destinations × versions. **Never invent copy** beyond the
   briefing + examples + attached files; **never mark `approved`** — the decision is the user's in the table.
6. **`copy validate <folder>`** checks the shape (valid destinations/kinds/status/lang, non-empty
   text, unique ids, declared concept). Error → nothing written; fix and revalidate.
7. **`copy review <folder>`** opens the **table** in the browser (shortcut `OPEN-COPY-REVIEW.html`
   in the folder). Each row has approve / reject / redo+note; filters by status,
   destination (PPC/overlay) and concept. Only **marks** the row (intent). **Fulfill the batch:**
   `rejected` → rewrite the copy (new direction from the briefing/examples); `redo` →
   apply the `note`. Change the `text`, set `status:"pending"` back, clear `note`, re-stamp
   `updated_at`/`updated_by`. The table updates by itself (4 s poll). Repeat until done.
8. **Delivery:** everything approved → the user clicks **Export approved** in the table (or you
   run **`copy deliver <folder>`**). Generates **CSV + XLSX** sheets in
   `~/Desktop/Copy Kit/<folder>/`: `meta_bulk_import`, `google_search_rsa`, `overlay`
   (concept × axis × kind), `copy_manifest` + README. **Only the approved rows ship.** RSA
   limits (headline ≤30 / description ≤90) become a **warning + truncation**, not a gatekeeper.
   URL/budget/targeting/IDs stay **blank for the PPC team** — do not invent.
   Everything ships PAUSED. The **Open folder** button opens the folder on the user's computer; the
   files are also available for **download** in the table itself.

The copy is independent: it delivers its own file. There is no automatic import by the visual kit
(handoff = a future step, if the user wants it). The voice comes from the briefing + pasted examples,
not from a logo/brandbook.