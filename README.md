# campaign-kit

Generate a complete campaign from a folder with a **logo + references + briefing**.
It runs on **your machine**, with **your AI agent** (Claude, Codex, Qoder…). It is not a
hosted service: no cloud, no login, no public URL — the files and the control are yours.

## Start here (step by step)

### 1. Start — no terminal

**You do not need to open a terminal or type a command.** The agent does it all for you:
it creates the campaign folder, installs the dependencies by itself (once), opens the
onboarding in the browser and walks you through to review. You just **chat with it** and
**use the browser**. Pick how to get the agent running:

**Door 1 · Claude Code (plugin — nothing to download):**

1. Open Claude Code.
2. Ask it to install the repository - https://github.com/dannowk/creative-kit-generator
   ```
   /plugin marketplace add dannowk/creative-kit-generator
   ```
   ```
   /plugin install campaign-kit@creative-kit-generator
   ```
3. To begin, type:
   ```
   /campaign-kit:start
   ```
   Just the **copy** (text for PPC + overlay), independent of the visual? Use
   `/campaign-kit:copy` — see [Copy Kit](#copy-kit).

**Door 2 · Any agent (Qoder, Codex, Claude… — no plugin):**

1. Clone or download the repository and open the folder in your agent:
   <https://github.com/dannowk/creative-kit-generator>
2. Say: *"read AGENTS.md and start a campaign"*. The agent follows the repository
   rules, installs the dependencies (`pip install -r requirements.txt`, once) and opens
   the onboarding in a **local browser tab** (`127.0.0.1`).
3. Everything is managed in the browser: you fill the inbox in the wizard and approve
   pieces in the review; the agent drives the rest from the chat. No plugin or native
   install is required — any agent that reads `AGENTS.md` can drive it.

### 2. Fill in YOUR folder (the campaign inbox)

Your folder lives **outside the kit** (e.g. `~/Desktop/my-campaign`) — the kit is the
tool; the inbox is your material. **The agent creates this folder and opens the wizard in
the browser for you.** That is where you prepare everything, without typing a command:
upload or drag files into each slot and fill in the briefing on screen.

The wizard creates exactly this structure inside the folder the agent created:

```
my-brand/
  logo/        ← logo png, transparent background preferred (required)
  photos/      ← photos that can become a piece
  videos/      ← source clips
  refs/        ← 2–6 ad/post references of the desired look
  brandbook/   ← brand manual as PDF/images/docx (optional)
  fonts/       ← brand .ttf / .otf (optional; there are substitutes)
  briefing/    ← supporting documents: ad copy, layout rules, safe areas, logo safety (optional, several)
  briefing.md  ← the briefing you filled on screen (or edited by hand)
  direction.md ← optional: technical direction for the whole creation (filled on screen)
```

Every slot accepts a **button or drag-and-drop** — and so does the briefing: drag a
`.md/.txt/.rtf/.pdf/.docx` onto the briefing area, or write/paste on screen. Each uploaded
file shows in the list with an **✕ to remove** just that file. If you
attach a **brandbook**, the agent reads the brand rules (colors, typography, logo usage,
voice) and follows them alongside the briefing and references.

**Supporting documents (several files):** the briefing area has a **"Supporting documents"**
zone to attach as many files as you like — the **ad content/copy** (when it lives in separate
files), **layout rules**, **safe areas** and **logo safety** from the brandbook. It accepts
text, PDF/Word, images (diagrams) and spreadsheets (`.csv/.xlsx`, e.g. a copy table). They
**add up** (they don't replace the briefing) and show in a list with a remove button. The
agent reads them all in `plan`: copy becomes the piece text (and the search-ad text in the
PPC sheets), and layout/safe-area/logo rules become geometry and compliance.

**Technical direction (optional, next to the briefing):** a third field for the guidance that
applies to **the whole creation** — the formats and sizes you need, grid and margins, the minimum
font size and how many lines a headline may take, what must never be covered, treatments to avoid,
delivery constraints. It is saved as `direction.md`, printed in full by `plan`, and **binds**
everything the agent authors after it: templates, formats, image prompts and copy. The copy kit has
the same field (limits per platform, how many variants, terms that must not be cut, languages).
If it conflicts with the briefing, the agent asks instead of guessing.

**Already have a briefing in any format** (Word, PDF, text, email)? No need to rewrite
anything: the agent **normalizes** it into the kit template and asks you only about what
is missing (a single round). Just say: *"normalize this briefing"* and point at the file.
Whoever fills in the template on screen (above) is already in the right format.

**Prefer to create it by hand, or reopen the wizard later?** Inside the kit folder, with
the dependencies installed (see [Quick start](#quick-start-manual)):

```
python3 -m kit.cli onboard ~/Desktop/my-brand
```

(Inside a venv, or `.venv/bin/python -m kit.cli onboard ...` / `.venv\Scripts\python ...`.)

### 3. Hand it to the agent

> **In the no-terminal flow (Doors 1 and 2)** the agent is already driving — this step is
> only for those who prepared the folder by hand (terminal alternatives).

Open the **kit folder** in your agent — Claude Code (`claude` in the terminal inside it),
Qoder (open the folder in the app), Codex (`codex`) — and say:

> "read AGENTS.md and run the campaign for `~/Desktop/my-brand`"

The agent drives `intake (or brief --apply) → plan → assets → approve → render → video` and creates:

- `brands/my-brand/` — `brand.yaml` (palette, fonts, voice), `assets/logo.png`;
- `campaigns/my-brand-<slug>/` — `campaign.json`, `templates/` (art direction),
  `assets/`, `out/`, `review/`.

Missing information? It becomes a **single round** of questions (in the wizard or in the
terminal). Before generating any paid asset, the agent shows the ≈ credits notice.

### 4. Approve in the browser — then click Continue to deliver

There are **two approvals**: first the raw generated images (step 5b), then the finished pieces
here. `review` **opens the browser by itself** at `http://127.0.0.1:8765` (or the next free
port). On screen you decide piece by piece — **reject and redo start working right away**:

- **✓ approve** → the piece is marked to go to the delivery folder (on your Desktop) and
  leaves the working grid (it goes only to the **Approved** list).
- **✕ reject** → the agent **recreates** another one automatically, and it always goes through
  the same readjustment checklist first: framing for that format (persona and action centered in
  the scene), safe zones, text contrast, nothing over a face — then the elements are refit to the
  frame (font size, one/two/more lines, text box) so the copy never hides the image and no word is
  cut in half.
- **↻ redo** → you write what to adjust; the agent applies your note and re-renders that piece.
- **Adjust style (the whole concept)** → filter a concept and click **Adjust style** to
  change **colors and fonts of all its pieces at once** (palette and type roles, plus a free
  note). The adjustment is saved to `styles/<concept>.yaml` and every piece of the concept
  enters the redo queue — the agent re-renders with the new look (and it applies to future
  renders too).

Marking writes the piece to the campaign's `requests.json`, and the agent watching the campaign
picks it up immediately: it recreates/redoes, re-renders only those pieces and they
**update on this same page** by themselves, back as pending with a **NEW** badge. You keep
reviewing; nothing to paste, no button to press.

The **Continue** button (step 7) is the delivery step: the approved pieces are **exported to the
delivery folder on your Desktop** (`~/Desktop/Campaign Kit/<campaign>/`), together with the PPC
sheets. An **Open folder** button appears next to Continue and opens that folder on your
computer (Finder on Mac, Explorer on Windows). Continue stays **locked while the agent is still
working** on marked pieces — it unlocks when every change is done.

- Lost the link? Clickable shortcut **`OPEN-REVIEW.html`** inside the campaign folder;
  the address is also at the top of the screen and at the end of `render` / `video` in the terminal.
- **Working queue:** everything you marked as reject/redo appears in a panel at the top of
  the review — what the agent is working on, with your note and the time you marked it. The card
  itself shows a **processing overlay** ("regenerating this image…" + when you marked it) and the
  page refreshes faster while anything is marked, so you don't have to reload: when the agent
  finishes, the new image replaces the old one in place (the URL carries the piece's version, so
  the browser never serves a cached copy) and a toast tells you it arrived.
  You can close the browser and check later: regenerated pieces come back as pending with
  a **NEW** badge (updated since your last visit).
- **A rule needs your decision:** the agent may not change a compliance rule or a briefing
  field on its own — it files a proposal, and the page (review **and** asset approval) pops a
  **blocking alarm**: the rule as it is now, what the agent proposes, why, and how many pieces
  it touches. You also get a **desktop notification** (macOS/Windows) and a ⚠ badge in the
  header, and Continue/Next stay locked until you answer. **Accept the change** saves the patch
  to `campaigns/<campaign>/rules/overrides.yaml` — it is merged on every render, so `brand.yaml`
  and `campaign.json` stay exactly as you wrote them. **Keep the original rule** leaves the rule
  (and the finding it produces) alone, and the agent fixes the layout or the copy instead.
- **No agent watching?** The review shows a **handoff** line with the exact instruction — copy it
  into the chat and the agent runs the batch.
- Delivered (approved) pieces: `~/Desktop/Campaign Kit/<campaign>/<concept>/` (png/mp4), on
  your Desktop. The working render lives in `campaigns/<campaign>/out/<concept>/` + contact
  sheet `review/sheet_<concept>.png`.
- **Sheets for the PPC team (Meta + Google):** Continue also generates
  `~/Desktop/Campaign Kit/<campaign>/ppc/` with each platform's bulk upload in **CSV + XLSX**
  (Meta Ads Manager, Google Search RSA and Google Display) + a creative manifest. Names,
  copy, CTA, placements and size come pre-filled; the traffic team fills URL, budget and
  IDs. Everything ships paused for review. See [PPC sheets](#ppc-sheets-meta--google).
- **Interface language:** everything — the wizard, the review and the terminal
  messages — is **English-only**; there is no language toggle.

### 5. Generate image/video with AI (optional — only for what is missing)

**Do you need this?** Only if you want the AI to **create** image or video that is
missing. If your inbox already has `photos/` and `videos/`, the kit renders from them and
you **skip this step**.

**Who does it?** The **agent**, by itself — you do not edit YAML or run a command twice.
Your only job is to have the provider's MCP installed in the agent (e.g. Magnific):
Claude Code (`claude mcp add …`), Qoder (Settings → MCP), Codex (`~/.codex/config.toml`).
Then tell the agent: *"generate the missing assets"*. It shows the ≈ credits notice
before generating (it is a notice, not a gatekeeper) and handles the rest.

**Why the agent and not the kit?** The kit is local Python and **holds no MCP connection** —
on purpose, it never sees your credentials. The agent is the one with the MCP; that is why
it generates, and the kit only collects the finished files.

<details>
<summary>Under the hood (advanced / manual)</summary>

The contract lives in the briefing's `provider` section:

```yaml
provider:
  nome: magnific-mcp        # manual | magnific-mcp | http
  creditos_imagem: 4        # feeds the "≈ X credits" notice
  creditos_video: 20
  drop_dir: ~/Downloads     # where the agent drops the generated files
```

1. `assets` prepares `campaigns/<campaign>/assets/jobs.json` and stops (`NeedsAgent`).
2. The agent fulfills each job through its MCP and saves into `drop_dir` with the **job id
   prefix** (e.g. `acme-hero_….png`).
3. `assets` again collects from `drop_dir`, copies into the campaign's `assets/` and writes
   `manifest.json` (type + credits).

Alternatives: `manual` (no MCP — you drop the files into `drop_dir` yourself) and `http`
(generic API: `api_url` + `api_key_env`, e.g. `MAGNIFIC_API_KEY`; **the key lives in an
environment variable, never in the briefing**).

</details>

### 5b. Approve the generated images — then the kit composites

Right after generating, the agent opens a second page in the browser: **the raw images and
videos, before any logo, overlay or copy**. You look at them and, per asset:

- **✓ approve** — ready to be composited;
- **✕ reject** — generate another image;
- **↻ redo** — write what should change ("more contrast, no people in frame") and the agent
  regenerates **only that asset**, applying your note to the prompt.

While the agent works, the marked card shows a **processing overlay** ("regenerating this
image…" + when you marked it) and the page polls faster; the new image then comes back to the
same page as pending, badged **NEW**, replacing the old one in place (no reload, no cached
copy); the ones you already approved keep their approval. The **All** filter shows every file
at once — approved, pending and the ones still regenerating — so a regenerated image never
leaves the overview. The next phase (logo, overlays, copy,
compliance) only starts when **every** asset is approved — the page says so and the
**Next: render** button unlocks.
Fixing a weak photo here is cheap; fixing it after the logo and the copy are on top is not.

<details>
<summary>Under the hood (advanced / manual)</summary>

```bash
python3 -m kit.cli approve campaigns/<campaign>    # browser at 127.0.0.1:8769+ (OPEN-ASSETS.html)
python3 -m kit.cli assets  campaigns/<campaign> --jobs <job-id>   # regenerate only the marked ones
python3 -m kit.cli render  campaigns/<campaign>    # gated: refuses while any asset is unapproved
```

Decisions live in `campaigns/<campaign>/assets/state.json`, keyed by **file + sha**: a
regenerated file (new sha) resets to pending by itself. Marked assets queue in
`assets/requests.json`, and `kit.cli wait` covers both queues (assets and pieces) — when
everything is approved it tells the agent to render.

</details>

### 6. New campaign

- **Same brand:** just a new briefing (goal, offer, CTA, channels, concepts, copy);
  the agent reuses `brands/<id>` and creates `campaigns/<id>-<new-slug>/`.
- **New brand:** a new inbox (step 2) and repeat from step 3.

### Where everything lives

| What | Where |
| --- | --- |
| kit code | where you downloaded/opened it (e.g. `~/Documents/creative-kit-generator`) |
| your files | the inbox the agent created (e.g. `~/Desktop/my-campaign`) |
| derived brand | `<kit>/brands/<id>/` |
| delivered (approved) pieces | `~/Desktop/Campaign Kit/<campaign>/<concept>/` (on your Desktop) |
| PPC sheets | `~/Desktop/Campaign Kit/<campaign>/ppc/` (CSV + XLSX) |
| working render | `<kit>/campaigns/<id>-<slug>/out/<concept>/` + `review/sheet_<concept>.png` |
| review | browser `127.0.0.1:8765+` · shortcut `OPEN-REVIEW.html` |
| asset approval | browser `127.0.0.1:8769+` · shortcut `OPEN-ASSETS.html` |
| regeneration batch | `<kit>/campaigns/<id>-<slug>/requests.json` (rejected + redo) |
| asset regeneration batch | `<kit>/campaigns/<id>-<slug>/assets/requests.json` (rejected + redo) |
| concept style adjustment | `<kit>/campaigns/<id>-<slug>/styles/<concept>.yaml` (colors/fonts; render applies it) |
| generated by MCP | `drop_dir` (e.g. `~/Downloads`) → collected into the campaign's `assets/` |

## Quick start (manual)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 -m kit.cli onboard ~/inbox/acme        # prepares the folder; wizard opens in the browser
python3 -m kit.cli intake  ~/inbox/acme acme   # derives the brand
#  or, via the canonical briefing template (advanced):
python3 -m kit.cli brief --template           # only PRINTS a markdown checklist (does not save a file)
#  fill in a briefing.yaml/.json with those fields and then:
python3 -m kit.cli brief ~/inbox/briefing.yaml --apply   # validates and writes brand + campaign
#  or normalize a free-form briefing (prose/PDF/docx) — emits a skeleton + contract for the agent:
python3 -m kit.cli brief --normalize ~/inbox/briefing.pdf   # agent fills it → brief <out> --apply
python3 -m kit.cli plan    campaigns/acme-launch
python3 -m kit.cli assets  campaigns/acme-launch
python3 -m kit.cli assets  campaigns/acme-launch --jobs <job-id>   # regenerate only that asset (a redo asking for a different image)
python3 -m kit.cli approve campaigns/acme-launch   # step 5: approve the RAW images in the browser (shortcut OPEN-ASSETS.html)
#  render is gated on that approval: it refuses to composite logo/overlay/copy over unapproved assets
python3 -m kit.cli render  campaigns/acme-launch
python3 -m kit.cli video   campaigns/acme-launch   # trim/reframe/overlay/concat/captions
python3 -m kit.cli review  campaigns/acme-launch   # opens the browser by itself; shortcut OPEN-REVIEW.html in the folder
python3 -m kit.cli wait    campaigns/acme-launch   # the agent's trigger: blocks until an asset or a piece is marked, prints the batch
python3 -m kit.cli deliver campaigns/acme-launch   # stage 7: the "Continue" — exports the approved (locked while anything is marked)
#  the agent fulfils the batch and re-renders only those pieces (preserves the approved):
python3 -m kit.cli render  campaigns/acme-launch --ids <id1> <id2>
python3 -m kit.cli ppc     campaigns/acme-launch   # bulk-upload sheets (Meta + Google), CSV + XLSX, in ppc/ in the delivery folder (Desktop)
python3 -m kit.cli ppc     campaigns/acme-launch --all   # export every piece, not just the approved ones
```

All output — CLI messages, wizard, review and the `plan` art-direction guidance (for the
agent, like `AGENTS.md`) — is English-only; there is no language toggle or `--lang` flag.

## PPC sheets (Meta + Google)

For campaigns with many ads, Meta and Google accept **bulk import via spreadsheet**. The kit
generates those sheets by itself — **Continue** already creates them, and you can also run
`python3 -m kit.cli ppc <campaign>` anytime. Everything lands in
`~/Desktop/Campaign Kit/<campaign>/ppc/` (on your Desktop), as **CSV** (direct import) and
**XLSX** (review in Excel/Google Sheets):

| File | Where to import | What it is |
|---|---|---|
| `meta_bulk_import` | Meta Ads Manager → Import/Export → **Import Ads in Bulk** | One row per Meta piece (feed/story/reels), with placements, CTA, copy and creative file name. |
| `google_search_rsa` | Google Ads Editor (CSV) or **Bulk actions → Uploads** | Responsive Search Ads: up to 15 headlines (≤30 chars) + 4 descriptions (≤90) per concept×axis. |
| `google_display` | Google Ads Editor / Uploads | Responsive Display Ads: text + image/logo file reference (attachment is done in Editor). |
| `creative_manifest` | — (human reference) | Each piece with platform, format, size, concept, file and copy. |
| `README.txt` | — | What is pre-filled vs. what PPC completes, and the character limits. |

**Pre-filled:** campaign/ad set/ad names, creative (file name), copy (hook/primary text,
headline, description), CTA, placements and size — all derived from the rendered campaign,
per platform and per piece format.

**The PPC team completes (blank columns):** final URL, Display Link, URL Tags (UTM),
objective, budget, targeting and IDs (Facebook Page, Instagram, Pixel). None of that is
invented by the kit. Every ad ships **paused** for review before going live.

<details>
<summary>Details (advanced)</summary>

- The export is **deterministic**: approved piece → row. Re-render/re-approve and run `ppc`
  again to refresh. `--all` includes pieces not yet approved (handy for drafts).
- Google RSA copy comes from the campaign `copy` (program/kicker/hook/CTA), truncated to
  Google's limits and stripped of the `[bracket]` highlights — and every cut is **reported**
  (a warn callout under Continue, a line in `ppc`/`deliver`), never silent. Improve the
  briefing `copy` for better headlines/descriptions — don't hand-edit the sheet.
- If the briefing has a landing page, set `landing_url` in `campaign.json` so the kit
  pre-fills `Link`/`Final URL`; otherwise they stay blank for PPC.
- XLSX needs `openpyxl` (already in `requirements.txt`). Without it the kit exports CSV only
  and says so.
- Google Display can't attach images via plain CSV: the sheet lists `Image file`/`Logo file`
  for you to attach in Editor. Meta uses the already-exported creative file name.

</details>

## Copy Kit

Need **only the copy** — text for PPC (Meta / Google) and for the piece overlay
(hook/kicker/program/CTA) — without generating image/video? **Copy Kit** is an
**independent** flow in the same repository: it asks for no logo, brandbook or visual
references and does not touch the visual kit. The reference is a **text field** where
you paste examples of copy you like.

**Start (no terminal):**

- **Claude Code (plugin):** `/campaign-kit:copy`
- **Any agent:** say *"read AGENTS.md and run the copy kit"* — the agent installs the
  dependencies (once) and opens the copy wizard in the browser
  (`python3 -m kit.cli copy onboard <folder>`).

The step-by-step is the same as the visual one, but lighter:

1. **Wizard** — fill in the **briefing** (goal, audience, tone, offer, concepts, axes,
   languages) and paste the **example texts** into the examples field. Each field has a
   **drag-and-drop / browse zone**: already have the copy in a file? Drop it — `.md`/`.txt`
   content goes straight into the field, and any file (PDF/docx included) is saved in
   `attachments/` for the agent to read. Only `briefing.md` + `examples.txt` + attachments —
   no logo/brandbook/refs/photos/videos.
2. **Generate** — the agent writes the copy from the briefing + examples + attached files,
   in volume (concepts × axes × destinations × versions), following the platform playbook:
   **Google RSA** — 15 headlines (≤30) + 4 descriptions (≤90) per concept × axis, keywords
   in the headlines and varied angles for Ad Strength "Excellent"; **Meta** — 5 primary
   texts (hook in the first 90–125 chars, before the mobile "See more") + 5 headlines (≤30)
   + 5 link descriptions (≤40) + the recommended native CTA; and **overlay**
   (hook/kicker/program/cta) for the pieces. It never invents beyond the
   briefing/examples/attachments.
3. **Review (table)** — approve / reject / redo+note **row by row** in a browser table.
   Every row says plainly **which concept and which program** it belongs to, plus the
   **platform** (Google / Meta / Google + Meta / Overlay) and a **readable type**
   (Headline ≤30, Primary text, Link description, CTA button, Hook, Kicker…) — no raw
   `axis`/`kind` jargon (the axis appears only as a small hint). Filters by status,
   destination, platform, concept and program, exact
   character counters per row (`[28/30]`, red when over) and the strategist's note.
   Reject/redo **start working right away**: the row goes to `requests.json` and to a
   **Working queue** panel (with your note and the time), the agent rewrites it and the table
   updates by itself — rewritten rows come back as pending with a **NEW** badge, so you can
   close the browser and check later. No agent watching? The table shows a **handoff** line to
   paste in the chat.
4. **Deliver** — all approved → click **Export approved** (or `copy deliver`):
   **CSV + XLSX** sheets in `~/Desktop/Copy Kit/<folder>/`, with **download** in the
   table itself and an **Open folder** button.
   - `copy_manifest` + `overlay` are the **approval sheets: vertical, one text per row**,
     labeled `Concept | Program | Platform | Variation | Type | Text | Chars`.
   - `meta_bulk_import` + `google_search_rsa` keep **each platform's own column layout** —
     that is what Meta Ads Manager and Google Ads Editor require to import.
   Plus README. **Only the approved rows ship.** Google
   RSA limits (headline ≤30 / description ≤90) become a warning + truncation, not a
   gatekeeper. URL/budget/targeting/IDs stay blank for the PPC team.

**Switching between the two kits:** both wizards carry a **`Visual | Copy`** control in the header.
Each one finds the other by itself (a local `/ping` probe on ports 8760–8790), **saves what you
typed before switching**, and shows a hint instead of a dead button when the other kit is not
running. Ports: visual 8766 (wizard) / 8769 (asset approval) / 8765 (review); copy 8767 (wizard) /
8768 (table). Each kit keeps its own folder — switching never mixes them and never loses your text.

<details>
<summary>Manual (terminal)</summary>

```bash
python3 -m kit.cli copy onboard  ~/Desktop/my-campaign-copy   # light wizard (briefing + examples)
python3 -m kit.cli copy plan     ~/Desktop/my-campaign-copy   # prints briefing + examples + vocabulary for the agent
#  the agent authors copy.json (concepts + rows) from that, then:
python3 -m kit.cli copy validate ~/Desktop/my-campaign-copy   # checks the shape (error → nothing written)
python3 -m kit.cli copy review   ~/Desktop/my-campaign-copy   # opens the table in the browser
python3 -m kit.cli copy wait     ~/Desktop/my-campaign-copy   # the agent's trigger: blocks until a row is marked, prints the batch
python3 -m kit.cli copy deliver  ~/Desktop/my-campaign-copy   # exports only the approved (CSV + XLSX) to Desktop/Copy Kit
```

Copy is independent: it delivers its own file. There is no automatic import by the
visual kit (handoff = a future step, if you want it). The voice comes from the briefing
+ pasted examples, not from a logo/brandbook.
</details>

## What is in the repo

- `kit/` — declarative render engine + compliance + providers + local UI.
- `templates/` — library of concept specs (overridable per campaign).
- `brands/acme` + `campaigns/acme-launch` — a generic example for you to follow.

The design **follows the briefing and the references** — it does not inherit another
client's look. Full rules and the provider contract are in **[AGENTS.md](AGENTS.md)**.
