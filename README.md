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

The agent drives `intake (or brief --apply) → plan → assets → render → video` and creates:

- `brands/my-brand/` — `brand.yaml` (palette, fonts, voice), `assets/logo.png`;
- `campaigns/my-brand-<slug>/` — `campaign.json`, `templates/` (art direction),
  `assets/`, `out/`, `review/`.

Missing information? It becomes a **single round** of questions (in the wizard or in the
terminal). Before generating any paid asset, the agent shows the ≈ credits notice.

### 4. Approve in the browser — then click Continue to deliver

`review` **opens the browser by itself** at `http://127.0.0.1:8765` (or the next free
port). On screen you decide piece by piece — **each click only marks, nothing runs immediately**:

- **✓ approve** → the piece is marked to go to the delivery folder (on your Desktop) and
  leaves the working grid (it goes only to the **Approved** list).
- **✕ reject** → marked for the system to **recreate** another one automatically.
- **↻ redo** → you write what to adjust; the note is saved.
- **Adjust style (the whole concept)** → filter a concept and click **Adjust style** to
  change **colors and fonts of all its pieces at once** (palette and type roles, plus a free
  note). The adjustment is saved to `styles/<concept>.yaml` and every piece of the concept
  enters the redo queue — the agent re-renders with the new look (and it applies to future
  renders too).

When you finish marking, click the **Continue** button (stage 6). Only then does everything
run at once: the approved pieces are **exported to the delivery folder on your Desktop**
(`~/Desktop/Campaign Kit/<campaign>/`) and the rejected/redo ones enter the regeneration
queue. An **Open folder** button appears next to Continue and opens that folder on your
computer (Finder on Mac, Explorer on Windows). The **agent recreates/redoes** the queued
pieces and they **update on this same page** by themselves, ready to review again. Approved
pieces stay only in the approved list. Repeat until the campaign is done.

- Lost the link? Clickable shortcut **`OPEN-REVIEW.html`** inside the campaign folder;
  the address is also at the top of the screen and at the end of `render` / `video` in the terminal.
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
| regeneration batch | `<kit>/campaigns/<id>-<slug>/requests.json` (rejected + redo) |
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
python3 -m kit.cli render  campaigns/acme-launch
python3 -m kit.cli video   campaigns/acme-launch   # trim/reframe/overlay/concat/captions
python3 -m kit.cli review  campaigns/acme-launch   # opens the browser by itself; shortcut OPEN-REVIEW.html in the folder
python3 -m kit.cli deliver campaigns/acme-launch   # stage 6: the "Continue" — exports approved + queues recreation/redo
#  the agent fulfils requests.json and re-renders only the batch pieces (preserves the approved):
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
  Google's limits and stripped of the `[bracket]` highlights. Improve the briefing `copy`
  for better headlines/descriptions — don't hand-edit the sheet.
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
3. **Review (table)** — approve / reject / redo+note **row by row** in a browser table,
   with filters by status, destination, platform (Google/Meta) and concept, exact
   character counters per row (`[28/30]`, red when over) and the strategist's note.
   Each click only marks; the agent rewrites the rejected/redo rows and the table updates by itself.
4. **Deliver** — all approved → click **Export approved** (or `copy deliver`):
   **CSV + XLSX** sheets in `~/Desktop/Copy Kit/<folder>/` (`meta_bulk_import`,
   `google_search_rsa`, `overlay`, `copy_manifest` + README), with **download** in the
   table itself and an **Open folder** button. **Only the approved rows ship.** Google
   RSA limits (headline ≤30 / description ≤90) become a warning + truncation, not a
   gatekeeper. URL/budget/targeting/IDs stay blank for the PPC team.

**One flow at a time in the UI:** the visual uses ports 8766 (wizard) / 8765 (review);
copy uses 8767 (wizard) / 8768 (table). Don't run both in the same session.

<details>
<summary>Manual (terminal)</summary>

```bash
python3 -m kit.cli copy onboard  ~/Desktop/my-campaign-copy   # light wizard (briefing + examples)
python3 -m kit.cli copy plan     ~/Desktop/my-campaign-copy   # prints briefing + examples + vocabulary for the agent
#  the agent authors copy.json (concepts + rows) from that, then:
python3 -m kit.cli copy validate ~/Desktop/my-campaign-copy   # checks the shape (error → nothing written)
python3 -m kit.cli copy review   ~/Desktop/my-campaign-copy   # opens the table in the browser
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
