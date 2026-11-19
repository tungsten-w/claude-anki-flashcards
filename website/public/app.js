// anki-deck landing page. No external calls, no innerHTML with dynamic data.
(() => {
  "use strict";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.from(root.querySelectorAll(s));

  // ---- Nav background on scroll
  const nav = $("#nav");
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 10);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---- Footer year
  const year = $("#year");
  if (year) year.textContent = String(new Date().getFullYear());

  // ---- Reveal on scroll
  if ("IntersectionObserver" in window && !reduced) {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    $$(".reveal").forEach((el) => io.observe(el));
  } else {
    $$(".reveal").forEach((el) => el.classList.add("in"));
  }

  // ---- Copy buttons
  $$("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "Copied!";
        btn.classList.add("done");
      } catch {
        btn.textContent = "Select it";
      }
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1600);
    });
  });

  // ---- Flip cards
  $$(".flip").forEach((card) => {
    card.addEventListener("click", () => {
      const on = card.classList.toggle("flipped");
      card.setAttribute("aria-pressed", String(on));
    });
  });

  // ---- Demo
  const term = $("#term");
  const stack = $("#stack");
  const review = $("#review");
  const prog = $("#prog");
  const counters = { new: $("#cNew"), upd: $("#cUpd"), del: $("#cDel") };
  if (!term) return;

  const fronts = {
    nvim: [
      "In nvim, which command saves and quits?",
      "In nvim, how do you jump to the end of the file?",
      "In nvim, which key enters visual block mode?",
      "In nvim, how do you undo the last change?",
      "In nvim, what does `ciw` do?",
      "In nvim, how do you search backwards?",
    ],
    bash: [
      "In bash, what does `$?` hold?",
      "In bash, how do you redirect stderr to stdout?",
      "In bash, difference between '…' and \"…\"?",
      "In bash, what does `set -e` do?",
      "In bash, how do you loop over the files of a folder?",
      "In bash, what does `$#` hold?",
      "In bash, how do you test if a file exists?",
      "In bash, what is a here-document?",
      "In bash, what does `&&` do between two commands?",
    ],
    perms: [
      "In Linux, what is the setuid bit?",
      "In Linux, what does `chown -R` do?",
      "In Linux, how do you read `drwxr-x---`?",
    ],
  };

  // Each step: [kind, payload, delayAfterMs]
  const script = [
    ["type", "/anki-deck courses/linux", 500],
    ["line", { cls: "dim", text: "● anki_cards.py status \"courses/linux\"" }, 450],
    ["line", { cls: "", text: "  3 new · 1 changed · 12 up to date", bul: false }, 650],
    ["line", { cls: "", text: "Writing cards for courses/linux/nvim.md", bul: true }, 500],
    ["cards", { set: "nvim", n: 6, line: "  ✎ flashcards/courses/linux/nvim.md   +6 cards" }, 600],
    ["line", { cls: "", text: "Writing cards for courses/linux/bash.md", bul: true }, 500],
    ["cards", { set: "bash", n: 9, line: "  ✎ flashcards/courses/linux/bash.md   +9 cards" }, 600],
    ["line", { cls: "", text: "Updating courses/linux/permissions.md (changed)", bul: true }, 500],
    ["update", { line: "  ✎ 2 fixed (IDs kept) · 1 removed · 3 added" }, 700],
    ["line", { cls: "dim", text: "● anki_cards.py check → 0 errors" }, 500],
    ["line", { cls: "dim", text: "● anki_cards.py sync → Obsidian_to_Anki → Anki" }, 900],
    ["line", { cls: "done", text: "✓ courses::linux  +18 added · 2 updated · 1 deleted" }, 600],
    ["review", null, 5200],
  ];

  let runId = 0;
  const sleep = (ms, id) => new Promise((res, rej) => setTimeout(() => (id === runId ? res() : rej(new Error("cancel"))), ms));

  let visible = false;
  let wake = null;
  const waitVisible = () => (visible ? Promise.resolve() : new Promise((res) => { wake = res; }));

  function addLine(cls, text, bullet) {
    const div = document.createElement("div");
    div.className = "tl " + (cls || "");
    if (bullet) {
      const b = document.createElement("span");
      b.className = "bul";
      b.textContent = "● ";
      div.append(b);
    }
    div.append(document.createTextNode(text));
    term.append(div);
    return div;
  }

  function bump(key, by) {
    const el = counters[key];
    el.textContent = String(Number(el.textContent) + by);
    el.classList.add("bump");
    setTimeout(() => el.classList.remove("bump"), 220);
  }

  function addMini(text, cls) {
    const m = document.createElement("div");
    m.className = "mini " + (cls || "");
    m.textContent = text;
    stack.prepend(m);
    while (stack.children.length > 9) stack.lastElementChild.remove();
    return m;
  }

  function reset() {
    term.replaceChildren();
    stack.replaceChildren();
    review.classList.remove("show", "flipped");
    counters.new.textContent = counters.upd.textContent = counters.del.textContent = "0";
    prog.style.width = "0%";
  }

  async function play() {
    const id = ++runId;
    reset();
    try {
      for (let i = 0; i < script.length; i++) {
        await waitVisible();
        const [kind, p, after] = script[i];
        if (kind === "type") {
          const line = addLine("prompt", "");
          const pr = document.createElement("span");
          pr.className = "p";
          pr.textContent = "› ";
          const typed = document.createElement("span");
          const caret = document.createElement("span");
          caret.className = "caret";
          line.append(pr, typed, caret);
          for (const ch of p) { typed.textContent += ch; await sleep(55 + Math.random() * 40, id); }
          await sleep(350, id);
          caret.remove();
        } else if (kind === "line") {
          addLine(p.cls, p.text, p.bul);
        } else if (kind === "cards") {
          addLine("ok", p.line);
          for (let k = 0; k < p.n; k++) {
            addMini(fronts[p.set][k % fronts[p.set].length]);
            bump("new", 1);
            await sleep(170, id);
          }
        } else if (kind === "update") {
          addLine("warn", p.line);
          addMini("In Linux, what does `chmod 755` grant?", "upd"); bump("upd", 1); await sleep(300, id);
          addMini("In Linux, what does `umask 022` do?", "upd"); bump("upd", 1); await sleep(300, id);
          const gone = addMini("In Linux, what is the sticky bit for files?", "");
          await sleep(350, id);
          gone.classList.add("del"); bump("del", 1); await sleep(400, id);
          for (const f of fronts.perms) { addMini(f); bump("new", 1); await sleep(170, id); }
        } else if (kind === "review") {
          review.classList.add("show");
          await sleep(1400, id);
          review.classList.add("flipped");
        }
        prog.style.width = ((i + 1) / script.length * 100).toFixed(1) + "%";
        await sleep(after, id);
      }
      play(); // loop
    } catch { /* cancelled by a newer run */ }
  }

  function renderStatic() {
    reset();
    addLine("prompt", "› /anki-deck courses/linux");
    addLine("", "3 new · 1 changed · 12 up to date", true);
    addLine("ok", "  ✎ flashcards/courses/linux/nvim.md   +6 cards");
    addLine("ok", "  ✎ flashcards/courses/linux/bash.md   +9 cards");
    addLine("warn", "  ✎ 2 fixed (IDs kept) · 1 removed · 3 added");
    addLine("done", "✓ courses::linux  +18 added · 2 updated · 1 deleted");
    [...fronts.nvim, ...fronts.bash].slice(0, 8).forEach((f) => addMini(f));
    counters.new.textContent = "18"; counters.upd.textContent = "2"; counters.del.textContent = "1";
    review.classList.add("show");
    prog.style.width = "100%";
  }

  $("#replay").addEventListener("click", () => (reduced ? renderStatic() : play()));

  if (reduced || !("IntersectionObserver" in window)) {
    renderStatic();
    return;
  }

  let started = false;
  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    if (visible) {
      if (wake) { wake(); wake = null; }
      if (!started) { started = true; play(); }
    }
  }, { threshold: 0.35 }).observe($("#demoWin"));
})();
