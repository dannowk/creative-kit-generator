---
description: Generates only the campaign COPY (text for PPC + overlay) from a briefing + example texts, with row-by-row approval in a browser table. Independent of the visual — no logo/brandbook. Without the user opening a terminal.
---

The user **does not open a terminal or type a command**. You (the agent) run everything; they only
chat and use the browser. This command is the **copy kit** (independent of
`/campaign-kit:start`, which is the visual). Follow the `copy-kit` skill in this order:

1. Find the kit root (the folder with `AGENTS.md` + `kit/`).
2. **Create the folder automatically**, without asking for a path: default
   `~/Desktop/my-campaign-copy` (or `~/Desktop/<brand>-copy` if the user already said the name).
3. Install the deps once (`python3 -m venv .venv && .venv/bin/pip install -r
   requirements.txt`, or your environment's pip), then run `python3 -m kit.cli copy onboard
   <folder>` in the **background** — it **opens the copy wizard in the browser**, creating
   only `briefing.md` + `examples.txt` (no logo/brandbook/refs). Deps already installed →
   just reopen the wizard.
4. Say in the chat: *"I opened the copy wizard in the browser. Fill in the briefing (goal,
   audience, tone, offer, concepts) and paste example texts into the examples field — or
   drop a file with copy you already have into either field's drop zone. Let me know when
   you're done."* Wait for the OK.
5. `copy plan <folder>` → read the briefing + examples + any listed attached files
   (`attachments/` — plain text: read directly; PDF/docx/image: extract with your tools) →
   **author `copy.json`** (concepts + rows: id, destination ppc/overlay, platform
   google/meta/both, concept, program — the advertised program/product of that text,
   always filled — axis, kind, text, lang, status pending, origin agent,
   updated_at/by + top-level `strategy_note` and `meta_cta`). PPC kinds:
   headline/description/primary_text/link_description/cta. Overlay:
   hook/kicker/program/cta. **Platform playbook per concept×axis:** Google RSA = 15
   headlines (≤30) + 4 descriptions (≤90), keywords in the headlines, varied angles
   (benefit / authority / CTA), no repeated words — Ad Strength "Excellent". Meta = 5
   primary_text (hook in the first 90–125 chars, before "See more") + 5 headline (≤30) +
   5 link_description (≤40) + 1 cta row (recommended native button). **Never invent copy**
   beyond the briefing+examples+attachments; **never mark approved** (it's the user's).
6. `copy validate <folder>` → fix errors (nothing written on error).
7. `copy review <folder>` → opens the **table** (shortcut `OPEN-COPY-REVIEW.html`). Each row is
   labeled with **Concept, Program, Platform and a readable Type** (not raw axis/kind). The user
   approves/rejects/redo+note per row — marking queues the row in `<folder>/requests.json`
   immediately. **Start `copy wait <folder>` in the background** while they review: it returns the
   batch (ids, texts, reason, note) as soon as a row is marked (`--timeout N`, 0 = forever).
   Fulfill it by rewriting the text, setting pending back, clearing the note and re-stamping
   updated_at/by; the table updates by itself and the row comes back badged **NEW**. Run `wait`
   again for the next round.
8. Everything approved → the user clicks **Export approved** (or you run `copy deliver
   <folder>`): CSV+XLSX sheets in `~/Desktop/Copy Kit/<folder>/`, approved only, with download
   + **Open folder**. `copy_manifest` and `overlay` are **vertical approval sheets** (one text
   per row: Concept | Program | Platform | Variation | Type | Text | Chars);
   `meta_bulk_import` and `google_search_rsa` keep each platform's own layout so the import
   works. RSA limits (≤30/≤90) become a warning. URL/budget/IDs blank for the PPC team — do not invent.
   **Export is gated:** while any row is still rejected/redo the button is disabled and `deliver`
   returns `{"locked": n, "batch": [...]}` — rewrite every marked row back to pending first.

**One flow at a time in the UI:** do not start the visual wizard/review and the copy one in the same session.
Independent of the visual: does not touch the visual campaign/render/ppc.