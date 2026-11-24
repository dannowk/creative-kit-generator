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
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Dependencies: **Pillow, numpy, PyYAML, imageio-ffmpeg, faster-whisper**. Python 3.9+.
Run every command from the root as `python3 -m kit.cli ...` (inside the venv, or
`.venv/bin/python -m kit.cli ...`).

**No-terminal flow (default):** the user does not open a terminal or type a command — you
run everything. There is no installer: do the bootstrap above yourself (once), then run
`python3 -m kit.cli onboard <inbox>` in the background — it **opens the onboarding wizard
in the browser**. **Create the `<inbox>` folder automatically**
(default `~/Desktop/my-campaign`, or `~/Desktop/<brand>`), without asking the user for a
path; `onboard` does the scaffold (`logo/ refs/ brandbook/ fonts/ photos/ videos/ briefing/ briefing.md`).
Announce in the chat that onboarding opened, wait for the "ready" and follow the pipeline.

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
#    The wizard also has a **Technical direction** field (saved as direction.md) and a
#    Visual | Copy switch in the header (it discovers the other kit's wizard via /ping and
#    saves before navigating) — both wizards may run at the same time.
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
#    prints the briefing, the technical direction (direction.md, if the user filled it),
#    onboarding answers, refs, brandbook (if any),
#    reference_analysis, the requested concepts and the OPS vocabulary. Author the
#    templates/<concept>.yaml from THAT — one per requested concept. READ the brandbook
#    with vision (PDF/image): its rules (colors, typography, logo usage, voice)
#    prevail over the palette proposed from the logo; a conflict with the briefing becomes a question.

# 4. AI assets (image and video) — informative cost notice, no gatekeeper
python3 -m kit.cli assets campaigns/acme-launch
#    prints "≈ X credits (N image(s) + M video(s))" and generates/collects.
#    --jobs <id> ...  regenerates ONLY those asset jobs (a redo asking for a different image)

# 4b. Asset approval (step 5 in the UI) — the user looks at the RAW generated images/videos
#     before anything is composited on them. Opens the browser (free port from 8769) and writes
#     OPEN-ASSETS.html in the campaign folder. --no-open for headless.
python3 -m kit.cli approve campaigns/acme-launch
#    approve / reject / redo (with a note) per asset. Marks queue in assets/requests.json the
#    moment they happen; `wait` picks them up and you regenerate ONLY those with --jobs.
#    A regenerated file (new sha) comes back as pending on its own, badged NEW; untouched files
#    keep their approval. Decisions live in assets/state.json, spend/provenance in assets/manifest.json.

# 5. Render the piece matrix (concepts × formats × axes)
python3 -m kit.cli render campaigns/acme-launch
#    GATED: with assets still waiting for approval it stops and points at `approve`
#    (the gate is on the first render; --force skips it, --dry and --ids are not gated).
#    --concepts clean cinema --formats Meta-Feed --limit 4 --dry
#    --ids <id> ...  re-renders ONLY those pieces (stage 6: recreate/redo) without losing the decisions

# 5b. Edit video: trim, subject-centered reframe, brand overlay, concat, captions
python3 -m kit.cli video campaigns/acme-launch

# 6. Local review (127.0.0.1, free port starting at 8765): approve / reject / redo per piece.
#    Approve/reject/redo MARK the piece and queue it in requests.json right away; the regeneration
#    is yours and does not wait for "Continue" (Continue only exports the approved ones).
#    Opens the browser by itself and writes OPEN-REVIEW.html in the campaign folder (clickable shortcut).
#    --no-open for headless. The URL also appears at the top of the screen and at the end of render/video.
python3 -m kit.cli review campaigns/acme-launch

# 6b. YOUR trigger while the user approves assets or reviews pieces: blocks until either queue has
#     items, then prints the batch + the commands to fulfill it. Run it in the background, fulfill,
#     run it again. Items carry "stage": "assets" or "pieces". With nothing marked but every
#     generated asset approved and no state.json yet, it returns one synthetic item
#     {"stage":"assets","reason":"all_approved"} — that is your signal to run `render`.
#     --timeout N gives up after N seconds (0 = wait forever).
python3 -m kit.cli wait campaigns/acme-launch

# 7. Delivery — headless equivalent of "Continue". Exports the approved pieces to the delivery folder
#    on the Desktop (~/Desktop/Campaign Kit/<campaign>/<concept>/). Locked while anything is still
#    rejected/redo: it then prints the batch to fulfill instead of exporting. See "Stages 6–7 —
#    Review, regeneration and delivery". With the approved pieces exported, it also generates the PPC sheets
#    in ppc/ in the same delivery folder (Meta + Google).
python3 -m kit.cli deliver campaigns/acme-launch

# 8. Bulk-upload sheets for the PPC team (Meta + Google), CSV + XLSX, in ppc/ in the delivery folder (Desktop).
#    Deterministic: each approved piece becomes a row in each platform's import columns.
#    --all exports every piece (not just the approved). See "Step 7b — PPC sheets".
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
  provider, asset_jobs) + `assets/` (generated files + `manifest.json` provenance/spend
  + `state.json` approvals + `requests.json` regeneration batch) + `out/<concept>/` (working render)
  + `review/` + `styles/<concept>.yaml` (concept color/font adjustment, optional)
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

## Technical direction (`direction.md`)

An optional field in **both wizards**, right next to the briefing: the technical guidance for the
whole creation — formats and sizes needed, grid and margins, minimum font size and how many lines a
block may take, what must never be covered, treatments to avoid, character limits and how many copy
variants, languages, delivery constraints. The wizard saves it as `direction.md` (visual:
`<inbox>/direction.md`, copy kit: `<folder>/direction.md`), `intake` records the path in
`intake.json.direction` — it is **not** a briefing and never lands in `briefs` — and both `plan`
and `copy plan` print it in full.

**It binds everything you author after it:** the templates (`size`/`min_size`/`max_lines`/
`width`/`max_h`, safe zones), the formats in `campaign.json`, the asset prompts and the copy rows.
A conflict with the briefing or the brandbook becomes a **question**, never a silent guess. When a
reject sends a piece back, the layout checklist in Stages 6–7 is applied *inside* these constraints.

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

### File naming (`naming` in `brand.yaml`/`campaign.json`)

Default `{slug}_{concept}{axes}_{size}`. Fields: `slug`, `concept`, `size` (format label),
`format`, `brand`, `n`/`V`, `locale`, each axis key by name (`{angle}`, `{product}`…) and
`{axes}`/`{axis}` — every axis as `key-value` joined by `_` (`_angle-urgency_locale-en`), or an
empty string when the campaign has no axes.

**Always keep `{axes}` (or the axis keys) in the pattern.** A pattern that ignores the axes makes
every variation of the same concept+format resolve to the same file name, so they silently
overwrite each other and the user sees one piece instead of N. The render guards against it
(`unique_name` appends the axes, then `_2`, `_3`…), but the guard only kicks in on collision —
the explicit pattern is what makes the names readable.

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
4. **Per-piece review, mark → agent runs it:** approve / reject / redo write the intent to
   `state.json` and queue rejected/redo in `requests.json` **immediately** — you pick the batch
   up with `wait` and re-render; **Continue** only exports the approved ones (and is locked while
   anything is still marked). Status filters (**All** + one per status) and compliance findings
   on the card. The **approved pieces leave the working grid** (they stay in the approved list
   and in **All**); rejected/redo update **on the same page** after regeneration.
   Marked pieces appear in a **Working queue** panel (what the agent is redoing, with the
   note and when it was marked), and their cards show a **processing overlay** ("regenerating
   this image…" + queued/waiting + when it was marked) until the new render lands; pieces the
   agent regenerated come back pending with a **NEW** badge (updated since the user's last
   visit — the browser remembers it). Media URLs carry `&v=<updated_at>` (assets: `&v=<sha>`),
   so the regenerated image replaces the old one instead of showing the cached copy, and the
   page polls faster (1.5 s) while anything is marked, 6 s when idle, plus an immediate poll on
   `visibilitychange`/`focus`. Keep this format.
5. **Local files and control.** Do not create a public URL, remote or deploy without
   explicitly asking the user.
6. **Design follows the briefing/refs.** `plan` gives you the raw material; the art direction is
   yours, not a fixed template.
7. **An empty field is not a crash.** Briefing/brand YAML left blank arrives as `None`
   (`credits_per_video:`, `tolerancia_rosto:`…): read those through the null-safe helpers
   (`providers.base.num`, `compliance._num`) or `or <default>` so the pipeline keeps running with
   the documented default instead of dying mid-render.
8. **The raw assets are approved before the render.** After `assets`, run `approve` and let the
   user look at what the provider actually produced; `render` refuses to composite logo/overlay/copy
   over unapproved assets. Fulfill `assets/requests.json` with `assets --jobs <id>` (only the marked
   ones) and stay in `wait` — it also tells you when everything is approved and the render is unlocked.
9. **A reject is a layout brief, not a re-roll.** Every `reason:"rejected"` piece goes through the
   framing/safe-zone/contrast/face checklist and then has its elements refit to the frame (font size,
   one/two/more lines, box) — see **"A reject is a layout brief"** in Stages 6–7. Regenerating the
   same spec with the same numbers is not fulfilling it.
10. **`direction.md` binds the whole creation.** When the user filled the technical direction
   field, every template, format, asset prompt and copy row honours it; a conflict with the
   briefing or the brandbook becomes a question, never a silent guess.

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

## Stage 5 — Asset approval (before logo/overlay/copy)

The user approves the **raw generated images/videos** before anything is composited on them:
regenerating a weak photo is cheap and fixes the cause, re-rendering a composited piece only hides it.

```bash
python3 -m kit.cli assets  campaigns/<slug>    # generate (cost notice first)
python3 -m kit.cli approve campaigns/<slug>    # the user's browser (port from 8769)
python3 -m kit.cli wait    campaigns/<slug>    # you: blocks until an asset is marked
```

- **approve** → ready for the render. **reject** → generate another image. **redo** + note →
  regenerate applying the note to the prompt. Marks queue in `assets/requests.json` immediately;
  each item is `{stage:"assets", id:<path>, file, job, kind, prompt, credits, reason, note, marked_at}`.
- Fulfill with `assets campaigns/<slug> --jobs <job> ...` (only the marked jobs — the spend stays
  proportional). The new file lands with a new sha, so it returns to the page as **pending**, badged
  **NEW**, and the queue empties itself. Decisions are keyed by path + sha in `assets/state.json`:
  untouched files keep their approval.
- `wait` also fires **once** when every generated asset is approved and `state.json` does not exist
  yet: `{"stage":"assets","reason":"all_approved","count":n}` — that is your signal to run `render`.
- **`render` is gated** on unapproved assets (first render only). `--force` skips the gate, `--dry`
  and `--ids` are not gated (a targeted re-render is the user iterating on pieces they already saw).

## Stages 6–7 — Review, regeneration and delivery (Continue)

Same logic as providers/normalize: Python prepares and exports, the agent regenerates,
Python re-renders and the UI updates. The review is **batched** — a click marks the piece and
writes it to `requests.json` right away; the regeneration is yours and starts **without** the
user pressing Continue.

**What each click does (marks in `state.json` + queues in `requests.json`):**
- **Approve** → `status:"approved"`. The piece leaves the working grid and stays **only in the
  approved list**, marked to go to the delivery folder (Desktop).
- **Reject** → `status:"rejected"`. Queued to **recreate** (no note).
- **Redo** → `status:"redo"` + `note` (what to adjust). Queued to **redo with the note**.
- **Adjust style** (per concept, when a concept is filtered) → writes `styles/<concept>.yaml`
  (colors/fonts/note) and queues **all** pieces of that concept as `redo`. See below.

`requests.json` is a **derived view** of the marked pieces, refreshed on every review poll,
after every `render` and on `deliver` — so it appears the moment the user marks something and
empties itself when you re-render those pieces back to `pending`. Each item:
`{id, concept, format, axes, path, kind, asset, asset_job, reason:"rejected"|"redo", note, marked_at}`.

**Stay watching while the user reviews — `wait` is your trigger:**

```bash
python3 -m kit.cli review campaigns/<slug>      # the user's browser
python3 -m kit.cli wait campaigns/<slug>        # you: blocks until something is marked
```

`wait` returns as soon as `requests.json` has items: it prints the batch JSON on stdout and the
exact commands to fulfill it on stderr (`--timeout N` to give up; 0 = wait forever). Run it again
after fulfilling for the next round. If no `wait` is running, the review shows a **handoff**
callout with a paste-ready line — that is the manual fallback, not the normal path.

**The "Continue" button (or `kit.cli deliver`) exports:**
1. **Exports** the approved pieces from `out/` to `~/Desktop/Campaign Kit/<campaign>/<concept>/`
   (local copy, immediate) and marks `delivered:true` + `delivery_path` (absolute path).
2. The UI reports what was exported, shows the **Open folder** button (opens the delivery folder
   on the Desktop) and advances the stepper to step 7 (Deliver).
3. If anything is still marked, `deliver` does **not** export: it returns `{"locked": n, "batch": [...]}`
   (exit 1) with the same fulfillment instructions as `wait`.

**The export is gated:** while any piece is still rejected/redo (you are working on it), Continue/
`deliver` is **locked** (button disabled + `{"locked": n}`) — the user can only export after every
change is done (all marked pieces re-rendered via `render --ids`).

**YOUR JOB as the agent — fulfill the batch:**
1. For each piece: `reason:"redo"` → apply the `note` (adjust the template/copy/asset);
   `reason:"rejected"` → **recreate** (new direction, new asset via MCP, or a layout variation)
   **through the checklist below** — a reject has no note, so the checklist *is* the note.
   The render is **deterministic**: re-rendering the same spec gives the same image — to change
   the result you **must** change an input (template, asset, copy or fx).
   A note asking for **a different image** means regenerating that asset: rewrite the prompt of
   the job in `campaign.json.asset_jobs` (id = `asset_job`) and run
   `python3 -m kit.cli assets campaigns/<slug> --jobs <asset_job>` — `--jobs` limits the spend to
   that asset instead of regenerating everything.
2. Run `render <campaign> --ids <id1> <id2> ...` to re-render **only** those pieces.
   `run` **merges** with the previous `state.json`: approved/delivered are preserved,
   the re-rendered pieces go back to `pending` (no `note`/`queued`) for a new review, and the
   rest stay intact. **Never** re-render the whole matrix after approving — use `--ids`.
3. The review **updates by itself** (1.5 s poll while anything is marked, 6 s when idle, plus an
   immediate poll when the tab becomes visible again): while the piece is queued its card shows a
   processing overlay, and after `render --ids` the rejected/redo pieces reappear as pending with
   the new image (cache-busted by `updated_at`, so the browser never shows the old one), on the
   same page, badged **NEW**; the approved ones leave the working grid (the **All** filter still
   shows them next to the cards being regenerated). The user reviews
   again until done.

### A reject is a layout brief (checklist, every time)

Permanent rule. A rejected rendered piece is readjusted in this order — **framing first, then the
elements inside the frame**:

1. **Framing for this format.** Is the persona *and* the action realigned to the middle of the
   scene, and does the crop suit *this* aspect ratio (a 9:16 story and a 1:1 feed frame the same
   asset differently)? Knobs: the `fx`/`crop` layer (`zoom`, `face_at`, `fx_at`, `face_y`,
   `subject_at`). Check the format, not only the asset.
2. **Safe zones.** Nothing important under the platform chrome — `safe_top`/`safe_bottom` in
   `kit/formats.py` plus `safe_zones` in `brand.yaml`; logo and copy inside the margins.
3. **Contrast.** Every text block readable over what sits behind it (`contrast_min`, ratio ≥ 3.0 —
   the findings are on the piece card in the review). Fix it with the scrim/`fade_to`/overlay, the
   ink color or the position; **never** by deleting the check.
4. **Nothing over a face.** `subject_safe`: no text, logo or overlay covering the subject. If it
   fails, reposition — move `at`, narrow `width`, push the block into the margin.
5. **Elements refit to the frame.** With the framing right, resize the copy to the space that is
   left so it never hides the image: `size`/`min_size` (font), `max_lines` (one line, two, or
   more), `width` + `max_h` (the box), `align`, `at`. Words wrap whole and the type shrinks until
   it fits — but if it *cannot* fit (a word wider than `width`, or the box too short), it overflows
   the block instead of breaking the word: widen the box, shorten the copy or lower `min_size`.
   No term is ever cut in half, and no line spills over the subject.

A `redo` with a note follows the same checklist, with the note on top: the note says *what* the
user wants changed, the checklist says *what still has to hold* after the change.

The final delivery folder (approved + PPC) lives at `~/Desktop/Campaign Kit/<campaign>/`, on the
user's Desktop — the **Open folder** button in the review opens it. `out/` (inside
`campaigns/<slug>/`) remains the working render. Nothing in the kit reads the delivery back:
the merge and the PPC use `state.json`/`out/`, so the Desktop delivery does not affect regeneration.

## Per-concept style adjustment (`styles/<concept>.yaml`)

To change **colors, fonts etc. of all pieces of a concept at once**, the user
filters the concept in the review and clicks **Adjust style**: tweaks the palette roles
(`primary/accent/ink/paper/dark`), the type roles (`display/text/accent`) and a
free note. That writes `campaigns/<slug>/styles/<concept>.yaml` and queues all pieces of the
concept as `redo` (approved ones go back to `pending`) — they land in `requests.json` right away,
like any other redo.

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

## Step 7b — PPC sheets (Meta + Google bulk upload)

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

**Limits are enforced, never silent:** copy longer than a platform limit (Meta title 40 / link
description 30, Google RSA headline 30 / description 90 / path 15, Display headline 30 / long
headline 90) is **cut at the limit and reported** per ad group — `N copy field(s) cut to the
platform limit: clean | Agenda Headline 74>30 …` on stderr from `ppc`/`deliver`, and a warn
callout under **Continue**. Nothing blocks (the ads ship paused); shorten the copy in the
briefing/`campaign.json.copy` and export again.

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