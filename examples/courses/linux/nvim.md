# Neovim basics

Neovim works with **modes**: Normal (default, to move and edit), Insert (`i`, `a`, `o`) to type text, Visual (`v`, `V`, `Ctrl+v`) to select, and Command (`:`).

## Moving
- `h` `j` `k` `l`: left, down, up, right
- `0` / `$`: start / end of the line
- `gg` / `G`: start / end of the file

## Saving and quitting
- `:w` saves, `:q` quits, `:wq` saves and quits, `:q!` quits without saving.

## Search and replace
- `/word` searches forward, `?word` backward; `n` / `N` go to the next / previous match.
- `:%s/old/new/g` replaces every `old` with `new` in the file.
