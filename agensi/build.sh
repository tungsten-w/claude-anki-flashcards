#!/usr/bin/env bash
# Builds agensi/anki-deck.zip: a flat skill folder ready to upload on Agensi.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/agensi/anki-deck.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PKG="$TMP/anki-deck"
mkdir -p "$PKG"
cp "$ROOT/skill/anki-deck/SKILL.md" "$ROOT/skill/anki-deck/anki_cards.py" "$ROOT/install.py" "$PKG/"
cp "$ROOT/agensi/BUYER_README.md" "$PKG/README.md"
cp -r "$ROOT/examples" "$PKG/examples"

rm -f "$OUT"
(cd "$TMP" && zip -rq -X "$OUT" anki-deck -x '*/__pycache__/*' '*.pyc' '*/config.json' '*/.DS_Store')
echo "built $OUT"
unzip -l "$OUT" | tail -n +4 | head -n -2 | awk '{print $4}'
