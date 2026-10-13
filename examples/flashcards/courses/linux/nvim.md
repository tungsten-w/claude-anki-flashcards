---
source: "[[courses/linux/nvim]]"
source_hash: "666f9958771324e6"
---
TARGET DECK: courses::linux
FILE TAGS: courses linux

START
Basic
Front: What are the 4 main modes of Neovim, and what is each one for?
Back: 
- **Normal** (default): move and edit
- **Insert**: type text
- **Visual**: select text
- **Command**: run commands (`:`)
<!--ID: 1700000000001-->
END

START
Cloze
Text: In nvim, {{c1::`gg`}} jumps to the start of the file and {{c2::`G`}} to the end.
<!--ID: 1700000000002-->
END

START
Basic
Front: In nvim, how do you quit without saving?
Back: `:q!`
<!--ID: 1700000000003-->
END

START
Basic
Front: In nvim, which command replaces every "old" with "new" in the whole file?
Back: `:%s/old/new/g`
<!--ID: 1700000000004-->
END

START
Basic
Front: In nvim, how do you search for "word" forward, backward, then jump to the next / previous match?
Back: `/word` (forward), `?word` (backward), then `n` / `N`
<!--ID: 1700000000005-->
END
