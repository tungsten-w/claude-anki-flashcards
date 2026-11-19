# Fiche Agensi — à copier-coller

Dashboard → Settings → activer **Creator Mode**, connecter **Stripe Connect** (paiements), puis **Submit a skill** :
glisser `anki-deck.zip`, coller les champs ci-dessous, mettre `cover.png` en image si on te la demande.

---

**Title**
Obsidian → Anki Flashcards (/anki-deck)

**Tagline / short description**
Turn your Obsidian notes into Anki flashcards, folder by folder, and keep them in sync — review history included.

**Price**
$9 (one-time)

**Tags**
anki, obsidian, flashcards, spaced-repetition, study, learning, notes, productivity, education, claude-code

**Listing description**

Stop writing flashcards by hand. `/anki-deck` reads the notes of an Obsidian folder, writes high-quality Anki cards for them, and syncs them to a matching Anki deck.

```
/anki-deck courses/linux
```

→ cards in `flashcards/courses/linux/`, synced to the Anki deck `courses::linux`.

**What you get**
- **Smart cards, not copies**: Claude picks what is worth remembering (definitions, commands, formulas, pitfalls) and writes self-contained questions — basic, reversed and cloze cards, in the language of your notes.
- **Incremental**: run it again and only new or modified notes are processed. Edited cards are updated in Anki **without losing their review history**; removed cards are deleted.
- **Safe**: your notes are never modified. Cards live in a separate folder that mirrors your vault.
- **Decks from folders**: `biology/cells/mitosis.md` → deck `biology::cells`, with tags.
- **Any Anki language**: note types and field names are detected automatically (Basic/Front/Back, Basique/Recto/Verso, …).
- **One-command setup**: `install.py` installs AnkiConnect, the Obsidian_to_Anki plugin and the skill, and configures everything. Idempotent, keeps a backup of your plugin settings.
- **Validation built in**: a checker catches malformed cards before they reach Anki.

**Requirements**: Anki desktop, Obsidian 1.12+, Claude Code, Python 3.9+ (no dependencies). Tested on Linux; macOS/Windows paths handled.

**Network access (for the security review)**: the installer downloads AnkiConnect from ankiweb.net and the Obsidian_to_Anki plugin from its GitHub releases. At runtime, the skill only talks to AnkiConnect on `127.0.0.1:8765` and calls the local `obsidian` CLI. No telemetry, no secrets, no other network calls.
