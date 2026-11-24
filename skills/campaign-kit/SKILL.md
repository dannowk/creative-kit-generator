---
name: campaign-kit
description: Use when the user wants to create or run a marketing campaign (images and videos in multiple formats) from a logo, references and briefing, with per-piece approval in the browser. Drives everything without the user opening a terminal.
---

# campaign-kit

Generates the campaign locally: declarative specs, compliance (never cover faces),
video with embedded ffmpeg and two browser approvals — the raw generated assets, then the
composited pieces (approve/reject/redo).
**The user does not open a terminal or type a command — you run everything; they use the chat
and the browser.**

## Steps

1. **Find the kit root** (`AGENTS.md` + `kit/`). If it is not in the workspace,
   clone it yourself from `https://github.com/dannowk/creative-kit-generator` into
   `~/Documents/creative-kit-generator` — do not ask the user to clone.
2. **Create the campaign folder automatically**: default `~/Desktop/my-campaign`
   (or `~/Desktop/<brand>` if they already said the name in the chat) as a starting point —
   the wizard's first card lets the user rename it and pick where it lives; after a move use
   the wizard's step-5 phrase / `<kit>/.last-inbox` as the current path.
3. **Bootstrap + onboarding**, in the background: install the deps once
   (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, or your
   environment's pip), then run `python3 -m kit.cli onboard <inbox>` — it
   **opens the wizard in the browser**, creating `logo/ refs/ brandbook/ fonts/ photos/
   videos/ briefing/ briefing.md`. Each slot accepts a button + drag-and-drop (so does the briefing).
   The header carries a **`Visual | Copy`** switch: it discovers the copy wizard via `/ping`
   (8760–8790), saves before navigating, and stays disabled with a hint when the other kit is not
   running — both may run in the same session, each in its own folder. Every page also has
   **← Back** (review → this folder's wizard; wizard → previous panel) and **Restart**
   (confirms, then clears renders, decisions, adjustments and queues — briefing, uploads
   and generated assets stay).
   Deps already installed → just reopen the wizard.
4. **Announce in the chat** that onboarding opened; ask for the logo (required) + photos/refs +
   briefing (brandbook is optional), then **end your turn**: the wizard's last panel shows a
   paste-ready line with a copy button, and the user pastes it in chat to continue the pipeline
   (manual handoff — the page cannot start the agent). In the briefing area there is
   **"Supporting documents"** (several, they add up): ad copy, layout rules, safe
   areas, logo safety — text/PDF/Word/image/spreadsheet. `plan` lists them all; read and
   apply (copy → campaign.json.copy; rules → geometry/safe_zones/compliance).
   Right below the briefing there is also **Technical direction** (optional, saved as
   `direction.md`): formats/sizes, grid and margins, minimum font size and line count, what must
   never be covered, treatments to avoid, delivery constraints. `plan` prints it in full and it
   **binds** the templates, the formats, the asset prompts and the copy — a conflict with the
   briefing becomes a question.
5. **Follow `AGENTS.md`**: `intake (or brief --apply) → plan → assets → approve → render →
   video`. The art direction comes from THIS briefing + refs + brandbook (if any), not from
   another client or a previous campaign. Author each `templates/<concept>.yaml` by looking at
   the reference with vision and translating its key visual — the shape ops are native
   (`gradient`, `grid`, `wave`, `card` chips, `badge` disc, `pill` CTA). **Never silently drop a
   direction element or degrade to an older layout**; if the ops can't express it, say so and
   propose a provider image or new ops. Every copy field lands where the direction places it.
   Free-form briefing (prose/PDF/docx)? `brief --normalize <source>` → fill the skeleton (vision
   for PDF; whatever is missing stays empty, becomes a gap) → `brief <out> --apply`.
6. **Cost is a notice**: show ≈ credits before provider jobs and proceed.
7. **Asset approval (stage 5)**: after `assets`, start `approve` — the user looks at the **raw
   generated images/videos** in the browser (shortcut `OPEN-ASSETS.html`) before any logo, overlay
   or copy is composited. Approve/reject/redo (with a note) queue in `assets/requests.json` right
   away; fulfill them with `assets campaigns/<slug> --jobs <job>` (only the marked ones) and they
   come back as pending badged **NEW** — untouched files keep their approval. The marked card
   shows a **processing overlay** until the new file lands, and its `sha` in the image URL makes
   the regenerated file replace the old one in place (no reload, no cached copy). The **All**
   filter shows every file at once — approved, pending and still regenerating. A rule proposal
   (step 8) pops its blocking alarm here too, and locks **Next: render** until it is answered.
   **`render` is gated**: it refuses to run while any asset is unapproved (`--force` skips it).
   `wait` covers this queue too and, when everything is approved and there is no `state.json` yet,
   returns `{"stage":"assets","reason":"all_approved"}` — your signal to render.
8. **Review + regeneration (stage 6)**: start `review` (opens the browser by itself; shortcut
   `OPEN-REVIEW.html` in the campaign folder). Approve marks the piece for delivery;
   reject/redo **queue it in `requests.json` right away** — the work is yours and does not wait
   for Continue. **Stay watching while the user reviews:**
   ```bash
   python3 -m kit.cli review campaigns/<slug>   # the user's browser
   python3 -m kit.cli wait campaigns/<slug>     # you: blocks until something is marked
   ```
   `wait` prints the batch (`stage`, `id`, `concept`, `format`, `axes`, `asset`, `asset_job`,
   `reason`, `note`) plus the exact commands; `--timeout N` gives up (0 = wait forever). Run it
   again after fulfilling for the next round. The review always shows a **handoff** callout
   with a paste-ready line — the normal path is the user pasting it in chat; a `wait` still
   running inside your turn picks the batch up without the paste.
   **Fulfill the batch**: adjust template/asset/copy (actually recreate — the render is
   deterministic). A note asking for **a different image** = regenerate that asset: rewrite the
   prompt of the job whose id is `asset_job` in `campaign.json.asset_jobs` and run
   `assets campaigns/<slug> --jobs <asset_job>` (only that asset, not the whole set). Then
   `render --ids <ids>` (preserves the approved) and the review updates by itself: the marked
   cards show a **processing overlay** while they are queued, then the re-rendered pieces come
   back as pending badged **NEW** — the media URL carries the piece's `updated_at` (assets: its
   `sha`), so the new image replaces the old one in place instead of showing a cached copy.
   The **All** filter keeps everything in one grid — approved, pending and the cards still
   regenerating — so a re-rendered piece never disappears from the overview.
   **A reject is a layout brief** (permanent rule — no note comes with it, so the checklist *is*
   the note): framing for that format with the persona and the action realigned to the middle of
   the scene → safe zones clear → text contrast readable → nothing over a face → then refit the
   elements to the frame (font size, one/two/more lines, `width`/`max_h`) so the copy never hides
   the image and no word is cut in half. `wait` prints it whenever the batch has a reject.
   **A rule change is the user's call** — never edit `kit/`, `brand.yaml` or `campaign.json` to
   make a render pass; file it: `rules campaigns/<slug> --propose --scope brand|campaign
   --target "compliance[check=contrast_min].ratio" --value 2.5 --reason "<why>"
   [--affected N --total M]` (a dotted path; `compliance[check=disclaimer_required].when_text`
   makes the disclaimer conditional on that text). A **blocking alarm** pops in the review *and*
   in the asset page (+ desktop notification + ⚠ badge in the header) and Continue/Next stay
   locked until the user picks **Accept the change** — the patch goes to
   `campaigns/<slug>/rules/overrides.yaml` and is merged on every load, so the YAMLs stay
   pristine — or **Keep the original rule**, which leaves the finding in place (fix the
   layout/copy instead). `wait` hands you the answer as
   `{"stage":"rules","reason":"agreed"|"kept"}`: agreed → re-render what it blocked
   (`render --ids`); kept → the checklist above. No browser: `rules campaigns/<slug>
   --decide <id> --agree|--keep`; list with `rules campaigns/<slug>`.
   **Continue** (or `deliver`) exports the approved pieces to the Desktop delivery folder
   (`~/Desktop/Campaign Kit/<campaign>/`); the **Open folder** button opens it on the user's
   computer. **The export is gated:** while anything is still rejected/redo, Continue is disabled
   and `deliver` returns `{"locked": n, "batch": [...]}` instead of exporting.
   **Per-concept style adjustment**: if the user used **Adjust style** in the review (always
   available; concept picked in the panel), there is a
   `styles/<concept>.yaml` (colors/fonts) that the **render itself applies** — for that batch
   `render --ids` is enough, no template editing. When the user ticked pieces / **Select all**,
   only those are queued and their override lives under `pieces:` in the yaml (the render merges
   it over the concept one). References the user attached (Attach button or
   drag&drop) live in `styles/<concept>/refs/` and are listed under `refs:` — open them before
   re-rendering. See "Per-concept style adjustment" in AGENTS.md.
9. **PPC sheets (Meta + Google)**: Continue/`deliver` already generates `ppc/` in the delivery folder
   (Desktop) with each platform's bulk upload in CSV + XLSX (Meta Ads Manager, Google Search RSA, Google
   Display) + manifest. Or run `ppc <campaign>` (`--all` for non-approved). Names/copy/CTA/
   placements/size come pre-filled; **URL, budget, targeting and IDs stay blank for
   the traffic team** — do not invent. Everything ships paused. See "Step 7b — PPC sheets" in AGENTS.md.

The asset provider (the user's MCP, e.g. Magnific) lives in the agent, not in the kit:
briefing `provider` section + `assets/jobs.json` → MCP → `drop_dir` → collection.

**Attachments are session-scoped:** when the user attaches a file, read THAT file — even if
a same-named file appeared in another session, project or campaign folder. Never say "I
already have this file" from a past session; same name ≠ same content, and nothing attached
needs to be carried across sessions.