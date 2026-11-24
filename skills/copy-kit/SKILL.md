---
name: copy-kit
description: Use when the user wants to generate only the COPY of a campaign (text for PPC and overlay) from a briefing + example texts, with row-by-row approval in a browser table. Independent of the visual kit — no logo, brandbook or images. Drives everything without the user opening a terminal.
---

# copy-kit

Generates the copy locally: the agent writes from the briefing + examples, the kit validates
the shape and exports **only the approved** (vertical approval sheets — one text per row with
Concept + Program — plus the Meta / Google RSA import files). Review in a
browser **table** (approve/reject/redo+note per row). **The user does not open a
terminal or type a command — you run everything; they use the chat and the browser.**

Independent of `campaign-kit` (visual): does not touch the visual campaign/render/ppc, does not ask for
logo/brandbook/refs. Ports — visual wizard 8766/asset approval 8769/review 8765; copy 8767 (wizard) /
8768 (table). **Both wizards carry a `Visual | Copy` switch in the header**: each one discovers the
other by probing `/ping` on 8760–8790, saves what the user typed before navigating, and stays
disabled (with a hint) when the other kit is not running — so you may run both in the same session
and the user loses nothing by switching. Each kit still has its own folder. The copy wizard's
first card, **Copy folder**, names/moves the folder like the visual one; once saved, `folder.json`
makes both wizards show an "already saved" notice instead of asking again. Every page also has
**← Back** (review → this folder's wizard; wizard → previous panel) and **Restart** (confirms,
then clears copy.json, adjustments and the queue — briefing, examples and attachments stay).

## Steps

1. **Find the kit root** (`AGENTS.md` + `kit/`). If it is not in the workspace,
   clone it yourself from `https://github.com/dannowk/creative-kit-generator` into
   `~/Documents/creative-kit-generator` — do not ask the user to clone.
2. **Create the folder automatically**: default `~/Desktop/my-campaign-copy` (or
   `~/Desktop/<brand>-copy` if they already said the name in the chat). Without asking for a path.
3. **Bootstrap + copy wizard**, in the background: install the deps once
   (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, or your
   environment's pip), then run `python3 -m kit.cli copy onboard <folder>` — it
   **opens the copy wizard in the browser**,
   creating only `briefing.md` + `examples.txt` (no logo/brandbook/refs/photos/videos);
   `direction.md` is written by the wizard when the user fills the technical direction field.
   Deps already installed → just reopen the wizard.
4. **Announce in the chat** that the copy wizard opened; ask for the **briefing** (goal, audience,
   tone of voice, offer/product, concepts, axes, constraints, languages) and the **example
   texts** (a text field where they paste copy they like / want to use as a model). Mention
   that **each field has a drop zone**: they can drag a file with copy they already have —
   `.md`/`.txt` content goes into the field, any file lands in `attachments/` for you to read.
   Point out the third field, **Technical direction** (optional): limits per platform, how many
   variants they need, terms that must appear or never be cut, languages, delivery formats.
   Then start `python3 -m kit.cli copy wait <folder>` in the background: the wizard's last
   panel has a **Next step →** button — when the user presses it, `wait` returns
   `stage:"ready"` and you continue in chat (the copy-phrase fallback under the button
   works too).
5. **`copy plan <folder>`** prints the briefing + examples + **the technical direction** +
   **attached files** (if any) + the destinations/kinds vocabulary. **Read the attachments**
   (plain text directly; PDF/docx/image: extract with your tools) — they are part of the source
   material. **`direction.md` binds the rows you author**: honour every limit and constraint in it,
   and turn a conflict with the briefing into a question instead of a guess.
   **YOUR JOB:** author `<folder>/copy.json` = `{"concepts":[...], "rows":[...]}`.
   Each row: `id` (`k01`…, next free), `destination` (`ppc`/`overlay`), `platform`
   (`google`/`meta`/`both`, ppc rows only), `concept`,
   `program` (the advertised program/product/course of that text, from the briefing —
   always fill it: it labels every row in the review table and in the delivered sheets),
   `axis` (optional), `kind`, `text`, `lang` (`en`), `status:"pending"`,
   `origin:"agent"`, `updated_at` (ISO UTC now), `updated_by` (your name/user).
   - **ppc kinds:** `headline` (≤30), `description` (≤90), `primary_text` (hook in the
     first 90–125 chars), `link_description` (≤40, Meta), `cta` (native Meta button).
   - **overlay kinds:** `hook`, `kicker`, `program`, `cta`.
   - **Platform playbook (per concept × axis):** GOOGLE RSA = **15 headlines + 4
     descriptions**, keywords worked naturally into the headlines, angles spread across
     benefit / differentiator+authority / strong CTA, no repeated words (Ad Strength
     "Excellent"). META = **exactly 5 primary_text + 5 headline + 5 link_description**,
     hook (pain/desire/promise) in the first 90–125 chars of each primary text (before
     the mobile "See more" cut), feed-stop storytelling — plus one `cta` row with the
     recommended native button (e.g. "Learn More", "Sign Up").
   - Write at the top level of copy.json: `strategy_note` (how the Google Ads terms were
     used, which angles break the scroll) and `meta_cta` (recommended native button) —
     both show in the review table.
   High volume: concepts × axes × destinations × versions. **Never invent copy** beyond the
   briefing + examples + attached files; **never mark `approved`** — the decision is the user's in the table.
6. **`copy validate <folder>`** checks the shape (valid destinations/kinds/status/lang, non-empty
   text, unique ids, declared concept). Error → nothing written; fix and revalidate.
7. **`copy review <folder>`** opens the **table** in the browser (shortcut `OPEN-COPY-REVIEW.html`
   in the folder). Each row has approve / reject / redo+note and is labeled with **Concept,
   Program, Platform and a readable Type** (Headline ≤30 / Primary text / Hook / CTA button…) —
   the raw `axis` only appears as a small hint. Filters by status, destination (PPC/overlay),
   platform, concept and program. **Adjust copy** (always-available button, same format as the
   visual Adjust style): a concept picker + direction note + attached references; queues the
   whole concept as redo, or only the rows the user ticked / **Select all**. The direction and
   refs live in `<folder>/styles/<concept>.yaml` + `styles/<concept>/refs/` — read them first.
   Marking a row writes it to **`<folder>/requests.json` immediately** (a derived queue refreshed
   on every poll) — the rewrite is yours and does **not** wait for Export. **Stay watching:**
   ```bash
   python3 -m kit.cli copy review <folder>    # the user's table
   python3 -m kit.cli copy wait  <folder>     # you: blocks until a row is marked
   ```
   `copy wait` prints the batch (`id`, `concept`, `program`, `kind`, `text`, `reason`, `note`) plus
   the contract; `--timeout N` gives up after N seconds (0 = wait forever). **Fulfill it:**
   `rejected` → rewrite the copy (new direction from the briefing/examples); `redo` →
   apply the `note`. Change the `text`, set `status:"pending"` back, clear `note`, re-stamp
   `updated_at`/`updated_by`. The table updates by itself (4 s poll), the row comes back badged
   **NEW** and `requests.json` empties. Run `copy wait` again for the next round.
   If no `wait` is running, the table shows a **handoff** callout with a paste-ready line —
   that is the manual fallback, not the normal path.
8. **Delivery:** everything approved → the user clicks **Export approved** in the table (or you
   run **`copy deliver <folder>`**). **The export is gated:** while any row is still
   rejected/redo, the button is disabled and `deliver` returns `{"locked": n, "batch": [...]}` —
   the user can only export after every change is done (you rewrote all marked rows back to
   pending).
   Generates **CSV + XLSX** sheets in `~/Desktop/Copy Kit/<folder>/`:
   - **`copy_manifest`** and **`overlay`** are the **approval sheets: vertical, one text per
     row**, labeled `Concept | Program | Platform | Variation | Type | Text | Chars`.
   - **`meta_bulk_import`** and **`google_search_rsa`** stay in each platform's own column
     layout (that is what their importers require) — they are the upload files, not the
     reading ones.
   Plus README. **Only the approved rows ship.** RSA
   limits (headline ≤30 / description ≤90) become a **warning + truncation**, not a gatekeeper.
   URL/budget/targeting/IDs stay **blank for the PPC team** — do not invent.
   Everything ships PAUSED. The **Open folder** button opens the folder on the user's computer; the
   files are also available for **download** in the table itself.

The copy is independent: it delivers its own file. There is no automatic import by the visual kit
(handoff = a future step, if the user wants it). The voice comes from the briefing + pasted examples,
not from a logo/brandbook.

**Attachments are session-scoped:** when the user attaches a file, read THAT file — even if
a same-named file appeared in another session, project or copy folder. Never say "I already
have this file" from a past session; same name ≠ same content, and nothing attached needs to
be carried across sessions. Re-uploads coexist (`name (2).ext`), they are never refused.