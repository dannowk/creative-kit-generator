# AGENTS.md — campaign-kit

Entry point for the agent (Claude, Codex, Qoder, etc.). Read this first and
run the pipeline below. Everything runs **on the user's machine**, with local files and
control. **It is not a hosted service** — there is no backend, login, cloud or public
URL. You (the agent) do the art direction and the AI generation; the Python engine is
deterministic and only renders what you specified.

## What it is

A kit that turns a folder (logo + references + briefing) into a complete campaign:
visual variations, multiple formats/aspect ratios, separate output folders,
generated copy and compliance rules. Generic for any company — the design **follows the
briefing and the references provided**, never an inherited fixed look.

## Bootstrap (once)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies: **Pillow, numpy, PyYAML, imageio-ffmpeg, faster-whisper**. Python 3.9+.
Run every command from the root as `python3 -m kit.cli ...`.

**No-terminal flow (default):** the user does not open a terminal or type a command — you
run everything. Instead of the manual venv above, use `./install.sh <inbox>` (Mac/Linux, without
`--no-open`) or `Install.bat <inbox>` (Windows) in the background: it downloads `uv` + managed Python 3.12 **without admin**, installs the deps and
**opens the onboarding wizard in the browser**. **Create the `<inbox>` folder automatically**
(default `~/Desktop/my-campaign`, or `~/Desktop/<brand>`), without asking the user for a
path; `onboard` does the scaffold (`logo/ refs/ brandbook/ fonts/ photos/ videos/ briefing/ briefing.md`).
Announce in the chat that onboarding opened, wait for the "ready" and follow the pipeline. The
`python3` commands below are the manual equivalent (door C); in the managed flow use
`.venv/bin/python -m kit.cli ...` (Mac/Linux) or `.venv\Scripts\python ...` (Windows).

**ffmpeg / codecs:** do not install system ffmpeg or codecs. `imageio-ffmpeg` embeds
the ffmpeg binary (used by the video module for trim/reframe/overlay/concat/captions).
`faster-whisper` is only imported/downloaded (model) when you ask for **automatic** captions;
manual captions or `captions:"off"` never touch it.

**Fonts:** do not download licensed fonts on your own. If the brand font did not come
in the folder, intake asks (single round) and render degrades with an OS fallback
(macOS/Windows/Linux), reporting exactly which ones were substituted (`font_warnings`).
To point at a fonts folder, use the `CAMPAIGN_FONTS` env var. It only fails if there is
not even a system fallback (rare).

## Pipeline

```bash
# 1. Prepare the campaign folder (scaffold + guided UI at 127.0.0.1:8766)
python3 -m kit.cli onboard ~/inbox/acme
#    creates logo/ refs/ brandbook/ fonts/ photos/ videos/ briefing/ + briefing.md; the user fills it in.
#    In the wizard, each slot accepts a button + drag-and-drop; so does the briefing (drag
#    .md/.txt/.rtf/.pdf/.docx). Each uploaded file has an ✕ to remove just that file.
#    brandbook/ is optional (brand manual as PDF/images/docx).
#    briefing/ = supporting documents (several, they add up): ad copy, layout rules,
#    safe areas, logo safety — text/PDF/Word/image/spreadsheet (.csv/.xlsx). plan lists them all.
#    --no-ui = scaffold + checklist only, no server.

# 2. Derive the brand from the dropped folder (palette, logo, refs analysis, gaps)
python3 -m kit.cli intake ~/inbox/acme acme
#    writes brands/acme/brand.yaml + intake.json. Gaps become a single round of questions;
#    the answers (brands/acme/answers.json) are applied to brand.yaml in that round.

# 2-alt. Canonical briefing (schema + validate + apply), when the user fills in
#        the template or asks to adapt an existing briefing to it:
python3 -m kit.cli brief --template            # markdown generated FROM the schema (never diverges)
python3 -m kit.cli brief ~/inbox/briefing.yaml          # validates: gaps + structural errors
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply  # writes brand.yaml + campaign.json
#    apply is deterministic: copies logo/fonts/photos/videos/refs, maps channels→formats,
#    concepts→concepts+copy, compliance→checks, provider→credits, and the video block.
#    Without a declared palette, derives a proposal from the logo (palette_proposed=true → confirm).

# 2-alt-normalize. FREE-form briefing (prose .md/.txt, PDF, docx) → canonical schema:
python3 -m kit.cli brief --normalize ~/inbox/briefing.pdf   # [--out ~/inbox/briefing.yaml]
#    Emits a YAML skeleton of the schema (empty fields + each field's question) and a
#    contract <out>.normalize.md. YOUR JOB: read the source (vision for PDF/docx),
#    map the prose into the fields and fill the skeleton. Whatever you don't know stays EMPTY
#    (becomes a gap in the single round) — never guess a value, color, channel, concept or copy.
#    Then: brief <out> --apply. The deterministic guarantee is the validate, not the reading.

# 3. Art direction from the briefing + references  ← YOUR CREATIVE JOB
python3 -m kit.cli plan campaigns/acme-launch
#    prints the briefing, onboarding answers, refs, brandbook (if any),
#    reference_analysis, the requested concepts and the OPS vocabulary. Author the
#    templates/<concept>.yaml from THAT — one per requested concept. READ the brandbook
#    with vision (PDF/image): its rules (colors, typography, logo usage, voice)
#    prevail over the palette proposed from the logo; a conflict with the briefing becomes a question.

# 4. AI assets (image and video) — informative cost notice, no gatekeeper
python3 -m kit.cli assets campaigns/acme-launch
#    prints "≈ X credits (N image(s) + M video(s))" and generates/collects.

# 5. Render the piece matrix (concepts × formats × axes)
python3 -m kit.cli render campaigns/acme-launch
#    --concepts clean cinema --formats Meta-Feed --limit 4 --dry
#    --ids <id> ...  re-renders ONLY those pieces (stage 6: recreate/redo) without losing the decisions

# 5b. Edit video: trim, subject-centered reframe, brand overlay, concat, captions
python3 -m kit.cli video campaigns/acme-launch

# 6. Local review (127.0.0.1, free port starting at 8765): approve / reject / redo per piece.
#    Each click only MARKS the piece (intent); nothing runs until the "Continue" button (UI stage 6).
#    Opens the browser by itself and writes OPEN-REVIEW.html in the campaign folder (clickable shortcut).
#    --no-open for headless. The URL also appears at the top of the screen and at the end of render/video.
python3 -m kit.cli review campaigns/acme-launch

# 7. Delivery — headless equivalent of "Continue". Exports the approved pieces to the delivery folder
#    on the Desktop (~/Desktop/Campaign Kit/<campaign>/<concept>/) and queues rejected (recreate) +
#    redo (with the note) in requests.json. The regeneration is YOURS (agent): fulfill the batch and run
#    `render --ids`. See "Stage 6 — Delivery and regeneration". With the approved pieces exported, it also
#    generates the PPC sheets in ppc/ in the same delivery folder (Meta + Google).
python3 -m kit.cli deliver campaigns/acme-launch

# 8. Bulk-upload sheets for the PPC team (Meta + Google), CSV + XLSX, in ppc/ in the delivery folder (Desktop).
#    Deterministic: each approved piece becomes a row in each platform's import columns.
#    --all exports every piece (not just the approved). See "Stage 6b — PPC sheets".
python3 -m kit.cli ppc campaigns/acme-launch
```

`campaign` is always a **path** (e.g. `campaigns/acme-launch`), not a slug.

## Structure

- `kit/` — engine (declarative render, PIL primitives, compliance, intake, onboard,
  providers, UI). Do not hardcode brand visuals here.
- `templates/` — global library of concept specs (`cinema.yaml`, `editorial.yaml`,
  `poster.yaml`, `typographic.yaml`). Each campaign can override in
  `campaigns/<slug>/templates/<concept>.yaml`.
- `brands/<id>/` — `brand.yaml` (palette, type roles with OS fallback, voice,
  axes, naming, compliance, safe zones, locales) + `assets/logo.png` + `intake.json`.
- `campaigns/<slug>/` — `campaign.json` (brand, channels, concepts, axes, cta, copy,
  provider, asset_jobs) + `assets/` + `out/<concept>/` (working render) + `review/`
  + `styles/<concept>.yaml` (concept color/font adjustment, optional)
  + `state.json` (decisions) + `requests.json` (regeneration batch).
- `~/Desktop/Campaign Kit/<campaign>/` — **final delivery folder**, outside the kit, on the
  user's Desktop: `<concept>/` with the approved pieces exported by Continue + `ppc/` (Meta + Google
  bulk-upload sheets, CSV + XLSX). The **Open folder** button in the review opens this folder.
- `brands/acme` + `campaigns/acme-launch` — generic example that ships with the repo.

## Briefing supporting documents (`<inbox>/briefing/`)

Besides `briefing.md` (the structured text) and `brandbook/` (the brand manual), the user
can attach **several supporting documents** in the `briefing/` folder — via the wizard (button or
drag-and-drop, "Supporting documents" area) or by dropping the files straight into the folder.
They **add up** (they don't replace the briefing) and accept text (.md/.txt/.rtf), PDF/Word,
images (.png/.jpg/.webp — safe-area/logo diagrams) and spreadsheets (.csv/.xlsx — copy
table). Examples: ad content/copy in separate files, layout rules, safe
areas per format, logo safety/clearspace extracted from the brandbook.

`intake` collects everything into `brief_docs` in `intake.json` and `plan` lists each file.
**YOUR JOB as the agent:** read them all (vision for PDF/image; text/spreadsheet directly) and
apply them — the ad copy/content feeds `campaign.json.copy` (hook/kicker/program/
CTA per concept×axis, and the RSA copy in the PPC export); layout rules, safe areas and
logo safety become `geometry`/`safe_zones` and `compliance` in `brand.yaml` and in the
templates. The brandbook and these documents' rules prevail over the proposed palette;
a conflict with the briefing becomes a question — never a silent guess.

## Template specs (declarative)

A template is a list of `layers`; each layer has an `op` that is a PIL primitive
(`paper`, `photo`, `text`, `rule`, `logo`, ...). Expressions use a restricted AST
evaluator (variables like `w`, `h`, `scale`, `top`, `m`). Knobs per text layer:
`underline`, `accent_upper`, `accent_scale`, `max_h`, anchoring. Author from the
briefing + refs — do not copy another client's look.

## Multiple concepts

The briefing requests the concepts in **section 7** (comma-separated list, e.g.
`clean, editorial, cinema`). `intake` extracts that into `concepts_requested` (and asks
in the single round if left blank); `plan` prints it. For each requested concept:

1. Author `campaigns/<slug>/templates/<concept>.yaml` (the local one wins over the global library).
2. List it in `campaign.json.concepts`.
3. Give a `copy.hook` per concept (or a voice block `copy.<axis>.<concept>`). **Without
   a hook, the concept is skipped in render** with a warning.

The matrix is `concepts × formats × axes`. Each concept delivers into its own folder
`out/<concept>/` and gets its own contact sheet `review/sheet_<concept>[_<axis>].png`.
In the review, the **concept** chips (besides the status ones) isolate one direction at a time to
approve/reject/redo without mixing. With a concept filtered, the **Adjust style** button
changes colors/fonts of **all** pieces of that concept at once (see "Per-concept style
adjustment").

## Video

The `kit/video.py` module edits locally with the embedded ffmpeg (no system ffmpeg):

- **Trim** by duration (`durations` per format, or `default`).
- **Reframe** by aspect ratio with a subject-centered crop (`subject_center`), so the
  face stays at the center of the cut — never cropped out.
- **Brand overlay** reusing the concept's declarative spec in transparent
  mode (`render.render(..., transparent=True)`): logo, kicker, hook, CTA in the
  safe zones, same as the PNGs.
- **Concat** of clips with the same geometry (`video.concat`, stream copy without re-encode).
- **Burned-in captions**: `"auto"` (faster-whisper, model downloaded on first use) or a
  manual list `[{start,end,text}]`. Becomes a PIL PNG overlaid per time window — does not
  depend on libass/fontconfig. With captions, the overlay's `bottom` rises so the copy/CTA
  does not collide with the caption strip.

Config in `campaign.json.video`:
```json
{"source": "assets/clip.mp4", "durations": {"meta_story": 15, "default": 6},
 "captions": "auto", "concepts": ["clean"], "formats": ["meta_story", "meta_feed_square"]}
```
`source` can be a mapping per axis; `concat: [paths]` generates a master first. The pieces
land in `out/<concept>/<name>.mp4`, enter `state.json` with `kind:"video"` and appear
in the review as a player with approve/reject/redo. Face compliance runs on a
composed frame (overlay + middle frame), same as images.

## Rules (inviolable)

1. **Never cover faces.** The `subject_safe` check compares the subject center with the
   elements; respect the safe zones. If it blocks, reposition — do not turn the check off.
2. **Cost is a notice, not a gatekeeper.** The user already expects to be charged for the
   contracted generation. Show `≈ X credits` (the provider's estimate) and proceed. Do not block.
3. **Video is a provider job** (`kind:"video"`), generated via the user's MCP (e.g.
   Magnific) — there is no local video render. `credits_per_video` is separate from
   `credits_per_image`.
4. **Per-piece review, in batch:** approve / reject / redo only **mark** the piece
   (intent in `state.json`); nothing runs until **Continue** (stage 6). Status filters
   and compliance findings on the card. The **approved pieces stay only in the approved list** (they leave
   the working grid); rejected/redo update **on the same page** after regeneration.
   Keep this format.
5. **Local files and control.** Do not create a public URL, remote or deploy without
   explicitly asking the user.
6. **Design follows the briefing/refs.** `plan` gives you the raw material; the art direction is
   yours, not a fixed template.

## Providers (contract = folder + manifest, not API)

`campaign.json.provider.name`:
- `manual` — you/the agent drop the files into `drop_dir`; the kit collects.
- `magnific-mcp` (or `mcp`) — **agent-mediated**. `assets` prepares
  `campaigns/<slug>/assets/jobs.json` and raises `NeedsAgent`; the CLI prints the jobs.
  You fulfill each job through your MCP (image or video), save into `drop_dir`, and run
  `assets` again to collect + write `manifest.json` (with `kind` and credits).
- `http_api` — configurable generic POST (`credits_per_image`, `credits_per_video`,
  `{duration}` in the body; `.mp4` for video, `.png` for image).

`estimate()` is mandatory on every provider and returns the informative notice.

## Normalize (free-form briefing → schema, agent-mediated)

Same logic as the providers: Python prepares, the agent fulfills, Python validates.
`brief --normalize <source>` emits a **YAML skeleton** of the schema (empty fields, each
field's question as a comment) + a contract `<out>.normalize.md` with the source
(the text, if `.md/.txt/.rtf`; otherwise the instruction to extract).

Your job as the agent:
1. Read the source — **vision** for PDF/image, a docx reader for `.docx`.
2. Map the prose into the skeleton's fields, respecting enums and map keys.
3. **Don't know → leave empty** (`null/[]/{}`). Empty becomes a question in the single
   round of `validate`; never invent a value, color, channel, concept, copy or path.
4. File paths relative to the contract's base (the `--out` folder).
5. `brief <out>` (validates) → `brief <out> --apply` (writes brand + campaign).

The deterministic guarantee is the **validate + apply**, not your reading of the prose.

## Stage 6 — Delivery (Continue) and regeneration

Same logic as providers/normalize: Python prepares and exports, the agent regenerates,
Python re-renders and the UI updates. The review is **batched** — deciding runs nothing.

**What each click does (marks only, in `state.json`):**
- **Approve** → `status:"approved"`. The piece leaves the working grid and stays **only in the
  approved list**, marked to go to the delivery folder (Desktop).
- **Reject** → `status:"rejected"`. Marked to **recreate** (no note).
- **Redo** → `status:"redo"` + `note` (what to adjust). Marked to **redo with the note**.
- **Adjust style** (per concept, when a concept is filtered) → writes `styles/<concept>.yaml`
  (colors/fonts/note) and marks **all** pieces of that concept as `redo`. See below.

**The "Continue" button (or `kit.cli deliver`) runs the batch:**
1. **Exports** the approved pieces from `out/` to `~/Desktop/Campaign Kit/<campaign>/<concept>/`
   (local copy, immediate) and marks `delivered:true` + `delivery_path` (absolute path).
2. **Queues** rejected + redo in `requests.json` — a batch with
   `{id, concept, format, axes, path, kind, asset, reason:"rejected"|"redo", note}`.
3. The UI reports what was exported/queued, shows the **Open folder** button (opens the
   delivery folder on the Desktop) and advances the stepper to stage 6 (Deliver).

**YOUR JOB as the agent — fulfill the `requests.json` batch:**
1. For each piece: `reason:"redo"` → apply the `note` (adjust the template/copy/asset);
   `reason:"rejected"` → **recreate** (new direction, new asset via MCP, or a layout variation).
   The render is **deterministic**: re-rendering the same spec gives the same image — to change
   the result you **must** change an input (template, asset, copy or fx).
2. Run `render <campaign> --ids <id1> <id2> ...` to re-render **only** those pieces.
   `run` **merges** with the previous `state.json`: approved/delivered are preserved,
   the re-rendered pieces go back to `pending` (no `note`/`queued`) for a new review, and the
   rest stay intact. **Never** re-render the whole matrix after approving — use `--ids`.
3. The review **updates by itself** (4 s poll of `state.json`): the rejected/redo pieces
   reappear as pending with the new image, on the same page; the approved ones stay only in the
   approved list. The user reviews again and clicks Continue again until done.

The final delivery folder (approved + PPC) lives at `~/Desktop/Campaign Kit/<campaign>/`, on the
user's Desktop — the **Open folder** button in the review opens it. `out/` (inside
`campaigns/<slug>/`) remains the working render. Nothing in the kit reads the delivery back:
the merge and the PPC use `state.json`/`out/`, so the Desktop delivery does not affect regeneration.

## Per-concept style adjustment (`styles/<concept>.yaml`)

To change **colors, fonts etc. of all pieces of a concept at once**, the user
filters the concept in the review and clicks **Adjust style**: tweaks the palette roles
(`primary/accent/ink/paper/dark`), the type roles (`display/text/accent`) and a
free note. That writes `campaigns/<slug>/styles/<concept>.yaml` and marks all pieces of the
concept as `redo` (approved ones go back to `pending`). **Nothing renders immediately** — same
as redo, the batch goes out on **Continue** (`requests.json`).

**The override is applied by the render itself**, per concept: `campaign.run` merges
`styles/<concept>.yaml` over the base brand's palette/typography (`styled_brand`) before
rendering and checking compliance. That means:

- To fulfill a restyle batch, **just run `render --ids <ids>`** — the new style already
  comes in by itself; you do **not** need to edit the template or `brand.yaml` for color/font.
- The adjustment **persists**: it applies to this and to future renders of that concept.
- The restyle `note` is extra guidance (e.g. "more contrast"); if it asks for something beyond
  color/font (layout, safe area), then adjust the template/`brand.yaml` as in a normal redo.
- A conflict between the override and the briefing/brandbook becomes a question — do not guess.

```yaml
# campaigns/<slug>/styles/cinema.yaml (example)
palette: {dark: "#040D0B", accent: "#FC6C54"}
type: {display: DINPro-Bold.otf}
note: more contrast
```

## Stage 6b — PPC sheets (Meta + Google bulk upload)

When demand is high, Meta and Google accept importing ads in bulk via spreadsheet.
`kit.cli ppc` (and **Continue**, which already calls the export) generates those sheets in
`ppc/` in the delivery folder (`~/Desktop/Campaign Kit/<campaign>/ppc/`), **one per platform**,
as **CSV** (direct import) and **XLSX** (review in
Excel/Sheets). It is deterministic: each approved piece (creative + copy) becomes a row in the
platform's import columns, according to format/size/channel.

**Generated files:**
- `meta_bulk_import` → Meta Ads Manager → Import/Export → **Import Ads in Bulk**. One row
  per Meta piece (feed/story/reels), with placements per format, CTA, copy and creative file name.
- `google_search_rsa` → Google Ads Editor (CSV) or **Bulk actions → Uploads**. Responsive
  Search Ads: up to 15 headlines (≤30 chars) + 4 descriptions (≤90) derived from the copy per
  concept×axis (not per piece — RSA is text, not image).
- `google_display` → Google Ads Editor / Uploads. Responsive Display Ads: text + **image/logo
  file reference** (the image attachment is done in Editor, not via plain CSV).
- `creative_manifest` → human reference: each piece with platform, format, size,
  concept, axes, file, delivery path and copy (hook/kicker/program/CTA).
- `README.txt` → what comes pre-filled vs. what the PPC team completes, and the limits.

**Pre-filled by the kit:** campaign/ad set/ad names, creative (file name), copy
(hook/primary text, headline, description), CTA (Meta enum), placements and size.
**Left blank (labeled column) for the PPC team:** final URL (`Link`/`Final URL`),
Display Link, URL Tags (UTM), objective, budget, optimization goal, billing event,
countries/targeting and IDs (Facebook Page/`Link Object ID`, Instagram Account ID, Pixel). Everything
ships **PAUSED/Paused** for review before going live.

**YOUR JOB as the agent:** the export is mechanical and does not invent URL or budget. If the
briefing includes the landing page, you can write `landing_url` into `campaign.json` so the
kit pre-fills `Link`/`Final URL`; otherwise leave it blank and tell the user
that PPC completes it. Do not fill Page/Pixel/Instagram IDs or budget — those belong to the
traffic team. The RSA copy comes from the campaign's `copy`; if headline/description are missing, improve the
`copy` in the briefing and re-render/export — do not hardcode in the sheet.

## Language

Everything is English-only: the UI (wizard + review), the CLI, the schema questions,
gaps, compliance findings and the docs (this AGENTS.md, the skills, the `plan` output).
There is no language toggle and no `--lang` flag. When chatting with the user, still
reply in the user's own language.

## Honest limits

The engine renders specs deterministically (PIL). The creativity — authoring
templates, copy, refs analysis, provider choice — belongs to the agent. The kit does not
"guess" the brand on its own: `intake` derives what it can (palette, logo) and the rest comes from the
briefing + your art direction in `plan`. In `normalize`, you adapt the prose to the
schema, but what is missing still becomes a question — never a silent guess.