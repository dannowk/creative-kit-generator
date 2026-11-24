---
description: Drives a campaign from scratch without the user opening a terminal — creates the folder, installs the dependencies, opens the onboarding in the browser and follows through to review.
---

The user **does not open a terminal or type a command**. You (the agent) run everything; they only
chat with you and use the browser. Drive in this order:

1. Find the kit root (the folder with `AGENTS.md` + `kit/`).
2. **Create the campaign folder automatically** as a starting point: default
   `~/Desktop/my-campaign` (or `~/Desktop/<brand>` if the user already said the brand
   name in the chat). Do not ask in chat — the wizard's first card, **Campaign folder**,
   asks the user for the folder name and where to save it (native picker or typed path);
   the files move with it. After a move, the current path is in the wizard's step-5 phrase
   and in `<kit>/.last-inbox`.
3. Install the dependencies once (`python3 -m venv .venv && .venv/bin/pip install -r
   requirements.txt`, or your environment's pip), then run `python3 -m kit.cli onboard
   <inbox>` in the **background** — it **opens the onboarding wizard in the user's
   browser**, creating `logo/ refs/ brandbook/ fonts/
   photos/ videos/ briefing/ briefing.md`. Each slot accepts a button + drag-and-drop (so does
   the briefing). Deps already installed → just reopen the wizard. The header has a
   **`Visual | Copy`** switch (it finds the other kit's wizard on its own, saves before switching,
   and says so when the other kit is not running) — you may run both flows in the same session.
   Every page also has **← Back** and **Restart** (Restart confirms, clears working output and
   queues, keeps briefing/uploads/generated assets, and returns to the wizard).
4. Say in the chat: *"I opened the onboarding in the browser. First, name the campaign folder
   and choose where to save it (card 1). Then upload the logo (required), photos
   and references, and fill in the briefing; if you have a brandbook, you can attach it too
   (optional). In the briefing area there is 'Supporting documents' to attach several files:
   ad copy, layout rules, safe areas, logo safety — and a 'Technical direction' field for the
   constraints of this whole creation (formats, margins, minimum font size and line count, what
   must never be covered). Let me know when you're done."*
   Wait for the OK. `plan` prints the technical direction (`direction.md`) in full: it binds the
   templates, formats, asset prompts and copy.
5. Read `AGENTS.md` and follow the pipeline: `intake (or brief --apply) → plan → assets →
   approve → render → video`. Free-form briefing (prose/PDF/docx)? `brief --normalize <source>` →
   fill the skeleton (vision for PDF; whatever is missing stays empty, becomes a gap) → `brief --apply`.
6. Show the ≈ cost notice before provider jobs (it is a notice, not a gatekeeper).
7. After generating, start `approve` (opens the browser by itself) **and `wait <campaign>` in the
   background**: the user looks at the **raw images/videos** before logo/overlay/copy and marks
   reject/redo into `assets/requests.json`. Fulfill with `assets <campaign> --jobs <job>` (only the
   marked ones) — they come back as pending badged **NEW**. `render` is **gated** on this approval;
   when every asset is approved `wait` returns `{"stage":"assets","reason":"all_approved"}` — run
   `render` then. See "Stage 5" in AGENTS.md.
8. Start `review` (opens the browser by itself) **and `wait <campaign>` in the background** —
   approve marks the piece for delivery; reject/redo queue it in `requests.json` immediately and
   `wait` hands you the batch the moment it appears (no Continue needed). Fulfill it (actually
   recreate/redo, changing template/asset/copy — a note asking for a different image means
   `assets <campaign> --jobs <asset_job>` first), run `render --ids <ids>`, and the review updates
   by itself — the marked card shows a **processing overlay** while it is queued, then the piece
   comes back as pending badged **NEW** with the new image in place (cache-busted) — the **All**
   filter shows it next to the approved ones instead of hiding it in a status tab. Run `wait`
   again for the next round.
   **A reject is a layout brief, not a re-roll**: framing for that format (persona + action
   realigned to the middle of the scene) → safe zones → text contrast → nothing over a face →
   refit the elements to the frame (font size, one/two/more lines, box) so nothing hides the image
   and no word is cut in half. See "A reject is a layout brief" in AGENTS.md.
   **Never patch a rule to make it pass**: if a compliance check or a briefing field is what
   blocks you, propose the change — `rules <campaign> --propose --scope brand|campaign
   --target "compliance[check=contrast_min].ratio" --value 2.5 --reason "<why>"`. A **blocking
   alarm** pops in the review and in the asset page (+ desktop notification + ⚠ badge) and
   Continue/Next stay locked until the user picks **Accept the change** (saved to
   `rules/overrides.yaml`, merged on every load; `brand.yaml`/`campaign.json` stay pristine) or
   **Keep the original rule** (the finding stays → fix the layout/copy). `wait` returns the answer
   as `{"stage":"rules","reason":"agreed"|"kept"}` — agreed: re-render what it blocked.
   The user clicks **Continue** (or you run `deliver`) to export the approved pieces to the
   Desktop delivery folder (`~/Desktop/Campaign Kit/<campaign>/`); the **Open folder** button opens
   it on the user's computer. **The export is gated:** while anything is still rejected/redo,
   Continue is disabled and `deliver` returns `{"locked": n, "batch": [...]}`.
   If the user used **Adjust style** (colors/fonts of a concept, or only of the pieces they
   ticked / Select all), the `styles/<concept>.yaml`
   is already applied by the render — for that batch `render --ids` is enough. References attached
   in the panel live in `styles/<concept>/refs/` (listed under `refs:`) — look at them first.
   See AGENTS.md.
9. Continue/`deliver` also generates the **PPC sheets** (Meta + Google) in `ppc/` in the
   delivery folder (Desktop), CSV + XLSX, for the traffic team to bulk-import. Or run `ppc <campaign>`. URL/budget/
   targeting/IDs stay blank for PPC — do not invent. See "Step 7b — PPC sheets" in AGENTS.md.

Do not skip compliance (never cover faces) and do not hardcode brand visuals.