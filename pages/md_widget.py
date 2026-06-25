"""
Lightweight Markdown renderer for tkinter.

Supports: # h1/h2/h3, **bold**, *italic*, `inline code`,
          ```code blocks```, --- horizontal rules,
          - / * bullet lists, 1. ordered lists, blank-line paragraphs.

Usage:
    md = MarkdownText(parent, bg="#1a1a24")
    md.pack(fill="both", expand=True)
    md.set_markdown("# Hello\n**world**")
"""
import re
import tkinter as tk

# ── palette (callers can override via configure_colors) ─────────────────────
_DEF = {
    "bg":         "#1a1a24",
    "fg":         "#e2e0f0",
    "muted":      "#8a8aa0",
    "accent":     "#7c5cbf",
    "accent2":    "#9472d8",
    "code_bg":    "#0f0f13",
    "code_fg":    "#c0e0ff",
    "rule_color": "#2e2e3e",
    "h1_color":   "#c9b8ff",
    "h2_color":   "#a88fe8",
    "h3_color":   "#8a8aa0",
    "font":       ("Segoe UI", 13),
    "mono":       ("Consolas", 12),
}


class MarkdownText(tk.Frame):
    """Read-only markdown display widget."""

    def __init__(self, parent, height=None, **colors):
        cfg = {**_DEF, **colors}
        super().__init__(parent, bg=cfg["bg"], bd=0, highlightthickness=0)

        kw = {"height": height} if height else {}
        self._t = tk.Text(
            self,
            bg=cfg["bg"], fg=cfg["fg"],
            insertbackground=cfg["fg"],
            selectbackground=cfg["accent"],
            relief="flat", bd=0, highlightthickness=0,
            wrap="word", cursor="arrow",
            font=cfg["font"],
            padx=10, pady=8,
            spacing1=2, spacing3=4,
            **kw,
        )
        sb = tk.Scrollbar(self, orient="vertical", command=self._t.yview,
                          bg=cfg["bg"], troughcolor=cfg["bg"],
                          activebackground=cfg["accent"])
        self._t.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        self._t.pack(side="left", fill="both", expand=True)

        self._cfg = cfg
        self._setup_tags()

    # ── tag definitions ──────────────────────────────────────────────────────

    def _setup_tags(self):
        c = self._cfg
        f_base = c["font"]
        f_name, f_size = f_base[0], f_base[1]
        mono   = c["mono"]

        self._t.tag_configure("h1",
            font=(f_name, f_size + 7, "bold"),
            foreground=c["h1_color"],
            spacing1=12, spacing3=6)
        self._t.tag_configure("h2",
            font=(f_name, f_size + 4, "bold"),
            foreground=c["h2_color"],
            spacing1=10, spacing3=4)
        self._t.tag_configure("h3",
            font=(f_name, f_size + 1, "bold"),
            foreground=c["h3_color"],
            spacing1=8, spacing3=2)
        self._t.tag_configure("bold",
            font=(f_name, f_size, "bold"))
        self._t.tag_configure("italic",
            font=(f_name, f_size, "italic"))
        self._t.tag_configure("bold_italic",
            font=(f_name, f_size, "bold italic"))
        self._t.tag_configure("code",
            font=(mono[0], mono[1]),
            foreground=c["code_fg"],
            background=c["code_bg"])
        self._t.tag_configure("codeblock",
            font=(mono[0], mono[1]),
            foreground=c["code_fg"],
            background=c["code_bg"],
            lmargin1=16, lmargin2=16,
            spacing1=4, spacing3=4)
        self._t.tag_configure("bullet",
            lmargin1=16, lmargin2=28)
        self._t.tag_configure("ordered",
            lmargin1=16, lmargin2=36)
        self._t.tag_configure("muted",
            foreground=c["muted"])
        self._t.tag_configure("hr",
            font=(f_name, 2),
            foreground=c["rule_color"],
            background=c["rule_color"],
            spacing1=8, spacing3=8)
        self._t.tag_configure("para_space",
            spacing1=6)

    # ── public API ───────────────────────────────────────────────────────────

    def set_markdown(self, text: str):
        self._t.configure(state="normal")
        self._t.delete("1.0", "end")
        self._render(text or "")
        self._t.configure(state="disabled")

    def configure_colors(self, **colors):
        self._cfg.update(colors)
        self._setup_tags()

    # ── renderer ─────────────────────────────────────────────────────────────

    def _render(self, text: str):
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # ── fenced code block ```
            if line.strip().startswith("```"):
                i += 1
                block_lines = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    block_lines.append(lines[i])
                    i += 1
                i += 1  # consume closing ```
                block_text = "\n".join(block_lines)
                self._insert(block_text + "\n", ("codeblock",))
                continue

            # ── horizontal rule
            if re.match(r"^(\*{3,}|-{3,}|_{3,})\s*$", line):
                self._insert("─" * 60 + "\n", ("hr",))
                i += 1
                continue

            # ── headings
            m = re.match(r"^(#{1,6})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                tag = {1: "h1", 2: "h2", 3: "h3"}.get(min(level, 3), "h3")
                self._insert_inline(m.group(2) + "\n", (tag,))
                i += 1
                continue

            # ── bullet list
            m = re.match(r"^(\s*)([-*+])\s+(.*)", line)
            if m:
                depth = len(m.group(1)) // 2
                bullet = "  " * depth + "•  "
                self._t.insert("end", bullet, ("bullet",))
                self._insert_inline(m.group(3) + "\n", ("bullet",))
                i += 1
                continue

            # ── ordered list
            m = re.match(r"^(\s*)(\d+)[.)]\s+(.*)", line)
            if m:
                num = m.group(2)
                self._t.insert("end", f"  {num}.  ", ("ordered",))
                self._insert_inline(m.group(3) + "\n", ("ordered",))
                i += 1
                continue

            # ── blank line → paragraph gap
            if line.strip() == "":
                self._t.insert("end", "\n", ("para_space",))
                i += 1
                continue

            # ── normal paragraph line
            self._insert_inline(line + "\n", ())
            i += 1

    # ── inline span parser ───────────────────────────────────────────────────

    # Pattern order matters: bold-italic before bold before italic.
    _INLINE = re.compile(
        r"(\*\*\*(?P<bi>[^*]+?)\*\*\*"          # ***bold italic***
        r"|\*\*(?P<b>[^*]+?)\*\*"               # **bold**
        r"|__(?P<b2>[^_]+?)__"                  # __bold__
        r"|\*(?P<i>[^*]+?)\*"                   # *italic*
        r"|_(?P<i2>[^_]+?)_"                    # _italic_
        r"|`(?P<c>[^`]+?)`"                     # `code`
        r")"
    )

    def _insert_inline(self, text: str, base_tags: tuple):
        pos = 0
        for m in self._INLINE.finditer(text):
            # plain text before this match
            if m.start() > pos:
                self._insert(text[pos:m.start()], base_tags)
            pos = m.end()

            if m.group("bi"):
                self._insert(m.group("bi"), base_tags + ("bold_italic",))
            elif m.group("b") or m.group("b2"):
                self._insert(m.group("b") or m.group("b2"), base_tags + ("bold",))
            elif m.group("i") or m.group("i2"):
                self._insert(m.group("i") or m.group("i2"), base_tags + ("italic",))
            elif m.group("c"):
                self._insert(m.group("c"), base_tags + ("code",))

        # remaining plain text
        if pos < len(text):
            self._insert(text[pos:], base_tags)

    def _insert(self, text: str, tags: tuple):
        self._t.insert("end", text, tags if tags else "")
