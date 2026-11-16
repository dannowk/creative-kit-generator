---
description: Generates only the campaign COPY (text for PPC + overlay) from a briefing + example texts, with row-by-row approval in a browser table. Independent of the visual — no logo/brandbook. Without the user opening a terminal.
---

The user **does not open a terminal or type a command**. You (the agent) run everything; they only
chat and use the browser. This command is the **copy kit** (independent of
`/campaign-kit:start`, which is the visual). Follow the `copy-kit` skill in this order:

1. Find the kit root (the folder with `AGENTS.md` + `install.sh`).
2. **Create the folder automatically**, without asking for a path: default
   `~/Desktop/my-campaign-copy` (or `~/Desktop/<brand>-copy` if the user already said the name).
3. Run `./install.sh <inbox> --copy` (Mac/Linux) or `Install.bat <inbox> --copy`
   (Windows) in the **background**. Downloads `uv` + managed Python 3.12 (no admin), installs
   the deps and **opens the copy wizard in the browser**, creating only `briefing.md` +
   `examples.txt` (no logo/brandbook/refs). If `.venv/` already exists, it just reopens the wizard.
4. Say in the chat: *"I opened the copy wizard in the browser. Fill in the briefing (goal,
   audience, tone, offer, concepts) and paste example texts into the examples field — or
   drop a file with copy you already have into either field's drop zone. Let me know when
   you're done."* Wait for the OK.
5. `copy plan <folder>` → read the briefing + examples + any listed attached files
   (`attachments/` — plain text: read directly; PDF/docx/image: extract with your tools) →
   **author `copy.json`** (concepts +
   rows: id, destination ppc/overlay, concept, axis, kind, text, lang, status pending,
   origin agent, updated_at/by). PPC: headline/description/primary_text. Overlay:
   hook/kicker/program/cta. **Never invent copy** beyond the briefing+examples+attachments; **never
   mark approved** (it's the user's).
6. `copy validate <folder>` → fix errors (nothing written on error).
7. `copy review <folder>` → opens the **table** (shortcut `OPEN-COPY-REVIEW.html`). The user
   approves/rejects/redo+note per row. Fulfill rejected/redo by rewriting the text,
   setting pending back and re-stamping updated_at/by; the table updates by itself.
8. Everything approved → the user clicks **Export approved** (or you run `copy deliver
   <folder>`): CSV+XLSX sheets (Meta / Google RSA / overlay / manifest) in
   `~/Desktop/Copy Kit/<folder>/`, approved only, with download + **Open folder**. RSA
   limits (≤30/≤90) become a warning. URL/budget/IDs blank for the PPC team — do not invent.

**One flow at a time in the UI:** do not start the visual wizard/review and the copy one in the same session.
Independent of the visual: does not touch the visual campaign/render/ppc.