---
name: campaign-kit
description: Use when the user wants to create or run a marketing campaign (images and videos in multiple formats) from a logo, references and briefing, with per-piece approval in the browser. Drives everything without the user opening a terminal.
---

# campaign-kit

Generates the campaign locally: declarative specs, compliance (never cover faces),
video with embedded ffmpeg and browser review (approve/reject/redo).
**The user does not open a terminal or type a command — you run everything; they use the chat
and the browser.**

## Steps

1. **Find the kit root** (`AGENTS.md` + `install.sh`). If it is not in the workspace,
   clone it yourself from `https://github.com/dannowk/creative-kit-generator` into
   `~/Documents/creative-kit-generator` — do not ask the user to clone.
2. **Create the campaign folder automatically**: default `~/Desktop/my-campaign`
   (or `~/Desktop/<brand>` if they already said the name in the chat). Without asking for a path.
3. **Bootstrap + onboarding in a single command**, in the background: `./install.sh <inbox>`
   (Mac/Linux, without `--no-open`) or `Install.bat <inbox>` (Windows). Downloads `uv` +
   managed Python 3.12 without admin, installs the deps
   and **opens the wizard in the browser**, creating `logo/ refs/ brandbook/ fonts/ photos/
   videos/ briefing/ briefing.md`. Each slot accepts a button + drag-and-drop (so does the briefing).
   `.venv/` already exists → just reopens the wizard.
4. **Announce in the chat** that onboarding opened; ask for the logo (required) + photos/refs +
   briefing (brandbook is optional) and wait for the user's "ready". In the briefing area there is
   **"Supporting documents"** (several, they add up): ad copy, layout rules, safe
   areas, logo safety — text/PDF/Word/image/spreadsheet. `plan` lists them all; read and
   apply (copy → campaign.json.copy; rules → geometry/safe_zones/compliance).
5. **Follow `AGENTS.md`**: `intake (or brief --apply) → plan → assets → render →
   video`. The art direction comes from the briefing + refs + brandbook (if any), not from
   another client. Free-form
   briefing (prose/PDF/docx)? `brief --normalize <source>` → fill the skeleton (vision
   for PDF; whatever is missing stays empty, becomes a gap) → `brief <out> --apply`.
6. **Cost is a notice**: show ≈ credits before provider jobs and proceed.
7. **Review + delivery (stage 6)**: start `review` (opens the browser by itself; shortcut
   `OPEN-REVIEW.html` in the campaign folder). Approve/reject/redo only **mark** the piece;
   the user clicks **Continue** (or you run `deliver`) to export the approved pieces to the
   Desktop delivery folder (`~/Desktop/Campaign Kit/<campaign>/`) and queue rejected
   (recreate) + redo (with the note) in `requests.json`. The **Open folder** button in the review opens
   that folder on the user's computer.
   **Fulfill the batch**: adjust template/asset/copy (actually recreate — the render is deterministic),
   run `render --ids <ids>` (preserves the approved) and the review updates by itself. Repeat until done.
   **Per-concept style adjustment**: if the user used **Adjust style** in the review, there is a
   `styles/<concept>.yaml` (colors/fonts) that the **render itself applies** — for that batch
   `render --ids` is enough, no template editing. See "Per-concept style adjustment" in AGENTS.md.
8. **PPC sheets (Meta + Google)**: Continue/`deliver` already generates `ppc/` in the delivery folder
   (Desktop) with each platform's bulk upload in CSV + XLSX (Meta Ads Manager, Google Search RSA, Google
   Display) + manifest. Or run `ppc <campaign>` (`--all` for non-approved). Names/copy/CTA/
   placements/size come pre-filled; **URL, budget, targeting and IDs stay blank for
   the traffic team** — do not invent. Everything ships paused. See "Stage 6b" in AGENTS.md.

The asset provider (the user's MCP, e.g. Magnific) lives in the agent, not in the kit:
briefing `provider` section + `assets/jobs.json` → MCP → `drop_dir` → collection.