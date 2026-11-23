---
description: Drives a campaign from scratch without the user opening a terminal — creates the folder, installs the dependencies, opens the onboarding in the browser and follows through to review.
---

The user **does not open a terminal or type a command**. You (the agent) run everything; they only
chat with you and use the browser. Drive in this order:

1. Find the kit root (the folder with `AGENTS.md` + `kit/`).
2. **Create the campaign folder automatically**, without asking for a path: default
   `~/Desktop/my-campaign` (or `~/Desktop/<brand>` if the user already said the brand
   name in the chat). Do not ask them to create a folder or type a path.
3. Install the dependencies once (`python3 -m venv .venv && .venv/bin/pip install -r
   requirements.txt`, or your environment's pip), then run `python3 -m kit.cli onboard
   <inbox>` in the **background** — it **opens the onboarding wizard in the user's
   browser**, creating `logo/ refs/ brandbook/ fonts/
   photos/ videos/ briefing/ briefing.md`. Each slot accepts a button + drag-and-drop (so does
   the briefing). Deps already installed → just reopen the wizard.
4. Say in the chat: *"I opened the onboarding in the browser. Upload the logo (required), photos
   and references, and fill in the briefing; if you have a brandbook, you can attach it too
   (optional). In the briefing area there is 'Supporting documents' to attach several files:
   ad copy, layout rules, safe areas, logo safety. Let me know when you're done."*
   Wait for the OK.
5. Read `AGENTS.md` and follow the pipeline: `intake (or brief --apply) → plan → assets →
   render → video`. Free-form briefing (prose/PDF/docx)? `brief --normalize <source>` →
   fill the skeleton (vision for PDF; whatever is missing stays empty, becomes a gap) → `brief --apply`.
6. Show the ≈ cost notice before provider jobs (it is a notice, not a gatekeeper).
7. Start `review` (opens the browser by itself). Approve/reject/redo only **mark**; the user
   clicks **Continue** (stage 6) — or you run `deliver` — to export the approved pieces to the
   Desktop delivery folder (`~/Desktop/Campaign Kit/<campaign>/`) and queue rejected/redo
   in `requests.json`. The **Open folder** button opens that folder on the user's computer. Fulfill
   the batch (actually recreate/redo, changing template/asset/copy), run `render --ids <ids>` and the
   review updates by itself. **The export is gated:** while a batch is still queued, Continue is
   disabled (`{"locked": n}`) — the user only exports after every change is done.
   If the user used **Adjust style** (colors/fonts of a whole concept), the `styles/<concept>.yaml`
   is already applied by the render — for that batch `render --ids` is enough. See AGENTS.md.
8. Continue/`deliver` also generates the **PPC sheets** (Meta + Google) in `ppc/` in the
   delivery folder (Desktop), CSV + XLSX, for the traffic team to bulk-import. Or run `ppc <campaign>`. URL/budget/
   targeting/IDs stay blank for PPC — do not invent. See "Stage 6b" in AGENTS.md.

Do not skip compliance (never cover faces) and do not hardcode brand visuals.