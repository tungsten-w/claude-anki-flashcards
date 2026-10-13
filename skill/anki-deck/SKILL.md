---
name: anki-deck
description: Generate Anki flashcards (Obsidian_to_Anki format) from the notes of a vault folder, then sync them to Anki. Use when the user asks for a deck, flashcards or Anki cards from a folder or a note (e.g. "/anki-deck courses/biology").
argument-hint: <folder or note> [--force] [--no-sync]
---

# /anki-deck — vault notes → Anki deck

Arguments: `$ARGUMENTS`

Pipeline (installed by `install.py` from claude-anki-flashcards):
- Anki + the **AnkiConnect** add-on (2055492159) on `127.0.0.1:8765`, with origin `app://obsidian.md` allowed.
- The Obsidian plugin **Obsidian_to_Anki** (marqp fork, id `obsidian-to-anki-plugin`) scans the card directory (`cards_dir` in `config.json`, `flashcards/` by default).
- Helper script: `python3 .claude/skills/anki-deck/anki_cards.py <cmd>` (run it from the vault root).

Fixed rules:
- **Never modify the source notes.** Cards for `a/b/c/note.md` go to `<cards_dir>/a/b/c/note.md`.
- Deck = folder path joined with `::` (`a/b/c/x.md` → `a::b::c`). Always use the `deck` and `tags` returned by `info`; never compute them yourself.
- Never touch the `<!--ID: ...-->` lines of existing cards: they link each block to its Anki note (and its review history).
- Note type and field names depend on the language of the user's Anki: get them with `anki_cards.py models` before writing cards, and use exactly those names. The examples below use the English defaults.

## Steps

1. **Status**: `python3 .claude/skills/anki-deck/anki_cards.py status "<folder>"`, plus `anki_cards.py models` once.
   Process the `new` and `changed` notes (also the `ok` ones with `--force`). If the argument is a single note, process it directly.
   If more than ~25 notes need processing, say how many before starting.
2. **For each note**:
   1. `anki_cards.py info "<note>"` → `cards_file`, `deck`, `tags`.
   2. Read the note (and, for a `changed` note, its existing card file).
   3. Write or update the card file using the format below.
      - `changed` note: keep the cards that are still correct **with their ID line**, fix the text of the cards that need it (keeping the ID, so Anki updates the card), delete the blocks that became wrong (the plugin deletes them from Anki), add new cards without an ID.
      - Note with nothing worth learning (shopping list, todo, images only, empty draft): still write the file with the frontmatter, the `TARGET DECK` line and `<!-- no cards: <short reason> -->`, so it is not proposed again.
   4. `anki_cards.py stamp "<note>"` (stores the note's hash, so it becomes `ok`).
   With many notes, work one subfolder at a time; this can be parallelised with sub-agents that follow these same rules.
3. **Orphans** (card files whose note no longer exists): list them and ask before deleting anything. Deleting a card file does **not** delete its cards from Anki; to do that, first empty its START…END blocks and sync.
4. **Validate**: `anki_cards.py check "<folder>"`, and fix until there are 0 errors.
5. **Sync** (unless `--no-sync`): `anki_cards.py sync`. If Obsidian is closed or its CLI is unavailable, tell the user to open Obsidian and click the Anki icon in the ribbon (or run "Obsidian_to_Anki: Scan Vault" from the command palette).
6. **Report**: cards added / updated / deleted per deck, and skipped notes.

## Card file format

````markdown
---
source: "[[courses/linux/nvim]]"
source_hash: ""
---
TARGET DECK: courses::linux
FILE TAGS: courses linux

START
Basic
Front: In nvim, which command saves and quits?
Back: `:wq` (or `ZZ` in normal mode)
END

START
Cloze
Text: In nvim, {{c1::`gg`}} jumps to the start of the file and {{c2::`G`}} to the end.
Back Extra: `:<n>` jumps to line n.
END
````

- `source`: wikilink to the note, full path without `.md`. `source_hash`: leave empty, `stamp` fills it.
- Note types (names from `models`): `basic` (question/answer), `reversed` (only when both directions are worth learning, e.g. vocabulary), `cloze`.
- Cloze deletions use Anki's native syntax: `{{c1::text}}`, `{{c2::text}}`… Each number is one card; use the same number to hide several parts on the same card.
- A field may span several lines and contain Markdown, code blocks, LaTeX `$...$`. No line of a field may start with a field name followed by `:` (e.g. `Front:`, `Back:`, `Text:`), or with `START` or `END`.
- Images from the note: reuse them with `![[image.png]]` when they are essential to the answer.

## Card quality

- Write in the language of the note. One idea per card, short and precise answers.
- Self-contained questions: give the context ("In bash, …", "In Java, …", "In organic chemistry, …").
- Prioritise what is worth remembering: definitions, commands and their syntax, useful options, differences between concepts, formulas, dates and orders of magnitude, pitfalls. Skip anecdotes, formatting and links.
- Commands and code: ask "which command to …?" and answer with `code`, plus one line of explanation if useful.
- Rough volume: 3–8 cards for a short note, 10–30 for a full course, without copying the whole note.
- No duplicates within a note, nor between notes of the same folder that overlap. No card whose answer is obvious from its question.
