# Content-team step: base copy from a spreadsheet

Date: 2026-11-12 · Status: approved design, pending implementation plan

## Problem

The content team keeps base ad copy in a spreadsheet (SharePoint online or a local
file). Today the kit only accepts copy written by hand into the briefing /
`campaign.json.copy`. There is no field for the content team's sheet, no rule-driven
adaptation ("create 15 more versions"), and no way to say a copy is for the PPC
spreadsheets only — every copy currently flows to both images and PPC.

## Decisions (settled with the user)

1. **Source**: wizard slot for `.xlsx/.csv` + optional SharePoint link. The agent
   downloads the link once (browser session) into the campaign folder; the kit never
   talks to SharePoint. Local-first rule preserved.
2. **Routing**: a `use` column — `image` / `ppc` / `both`; empty = `both` (today's
   behavior). Image pieces render only `image`/`both`; PPC exports only `ppc`/`both`.
3. **Adaptation**: agent adapts/expands rows per the briefing rules (normalize
   pattern: kit prepares + validates, agent creates, kit applies). The kit never
   generates copy.
4. **Versions**: the briefing rule decides what "15 more versions" produces. Image
   variants use the existing axis mechanism (agent adds a version axis; `lookup`
   already keys copy by axis value). PPC-only variants multiply as ad rows / RSA
   headline-description pool. No new render machinery.

## Input

### Wizard (onboard)

- New optional slot `content` — "Base content (spreadsheet)", accepts `.xlsx`, `.csv`,
  single file. Same upload/remove mechanics as other slots.
- New text field **SharePoint link (optional)** next to the slot; saved to
  `<inbox>/content_link.txt`. If a link exists and no file was uploaded, the agent
   fetches it once and drops the exported file into `content/` before `content` runs.
- Localized PT/EN (slot label/hint, field label, CLI messages) via `kit/i18n.py`.

### Sheet schema (canonical columns)

| column    | required | meaning                                        |
|-----------|----------|------------------------------------------------|
| `concept` | yes      | declared concept slug                          |
| `axis`    | no       | axis value or `A\|B` combo; empty = default    |
| `hook`    | yes      | main copy / headline                           |
| `kicker`  | no       | short supporting line                          |
| `program` | no       | offer / program name                           |
| `cta`     | no       | call to action                                 |
| `use`     | no       | `image` / `ppc` / `both`; empty = `both`       |
| `lang`    | no       | locale override                                |

One row = one base copy. PT/EN header aliases accepted (e.g. `conceito`, `gancho`).
Free-form sheets: the agent maps them to these columns (same contract as briefing
normalize) — the kit validates the canonical form, not the raw sheet.

### Briefing

New optional section **11. Base content & rules** in both PT/EN templates: the sheet
link plus adaptation rules (e.g. "15 more versions, shorter hooks for Stories").
Rules are the agent's contract; the section is not required (logo + sections 1–3 stay
the only blockers).

## Flow — `content` command (normalize pattern)

```
python -m kit.cli content <campaign>          # ingest + validate → content.json
python -m kit.cli content <campaign> --apply  # validate + merge → campaign.json.copy
```

1. **Ingest** (`content`): read the sheet from the campaign's `content/` dir (copied
   there by intake, like other slots), parse with openpyxl (already a dependency) /
   csv, normalize headers, validate rows (concept declared, hook present, `use`
   enum). Write `campaigns/<slug>/content.json`:
   `{source: {file, link}, rows: [...], gaps: [...]}`. Print rows + briefing §11
   rules + gaps. Touches nothing else.
2. **Adapt** (agent): apply the briefing rules to `content.json` — expand versions,
   adapt copy per destination, keep each row's `use`. Never invent what the sheet /
   briefing don't say. Image variants → add a version axis to `campaign.json.axes`
   and key rows by it; PPC-only variants → extra rows with `use: ppc`.
3. **Apply** (`content --apply`): re-validate (schema, `use` enum, declared concepts,
   hook present), then merge into `campaign.json.copy` keyed by concept/axis as
   today. Each entry carries `use` and optional `versions: [{hook, kicker, program,
   cta, use}, ...]` (base row first). Deterministic; validation errors block apply.

`content.json` is the audit trail of base + adapted rows; `campaign.json.copy` stays
the single source the render and PPC already read.

## Output — routing

- **Render** (`campaign.run`): skip copy entries with `use: ppc` — image pieces get
  only `image`/`both`. Empty/absent `use` = `both`, so existing campaigns are
  untouched.
- **PPC** (`kit/ppc.py`): include `ppc`/`both`.
  - Meta: one ad row per version (base + `versions`).
  - Google RSA: versions feed the headline/description pool; existing ≤15 headlines
    / ≤4 descriptions limits unchanged.
  - `ppc`-only entries with no rendered piece export as extra ad rows (campaign/ad
    names derived from concept + axis + version).
- **Image variants**: no new mechanism — a version axis expands the matrix via
  `expand_axes`, and `lookup` resolves each piece's copy by axis value.

## Contract (docs)

- `AGENTS.md` + `skills/campaign-kit/SKILL.md`: new "Content" section — step between
  plan and assets; agent adapts, kit validates; `use` routing; never invent copy.
- Pipeline order: `intake → plan → content → assets → render → video → review →
  deliver → ppc`.

## Error handling

- Missing sheet + missing link → `content` prints a gap (optional step; campaign can
  proceed with hand-written copy as today).
- Link present, file absent → gap telling the agent to download it first.
- Unknown concept / bad `use` / empty hook → row-level errors listed; `--apply`
  refuses until fixed (same gate as briefing validate).
- Unreadable `.xlsx` → clear error suggesting CSV export.

## Verification

Assert-based checks (same loop as the i18n fix): csv/xlsx parse + header aliases,
`use` filtering in render and PPC, apply merge (base + versions), ppc-only extra
rows, wizard slot + link round-trip, briefing §11 PT/EN. Live wizard check for the
new slot/field.

## Out of scope

- SharePoint/Graph API in the kit (agent-mediated download only).
- Kit-generated copy variants (agent's job, per briefing).
- Free-form sheet parsing in the kit (agent maps to canonical columns).
- Changes to RSA/Meta column limits or the review/deliver flow.