"""Small shared helpers for fast tk-based list rows.

CustomTkinter widgets each draw onto their own canvas, which makes building
hundreds of list rows slow. Plain tk widgets are ~10x cheaper to create, so
the list views use tk.Frame/tk.Label rows and these helpers wire up hover +
click behaviour consistently.

ScrollList is a lightweight replacement for CTkScrollableFrame: that widget
recomputes its scroll region on *every* child insertion (~12x slower to fill),
whereas ScrollList updates the scroll region once via finalize().
"""
import tkinter as tk
import customtkinter as ctk


class ScrollList(tk.Frame):
    """A fast vertically-scrolling container. Pack rows into `.body`,
    then call `finalize()` once after rendering."""

    def __init__(self, parent, bg, accent="#7c5cbf"):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = ctk.CTkScrollbar(self, orientation="vertical",
                                     command=self.canvas.yview, button_color=accent)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        # Keep the inner frame as wide as the canvas (cheap — fires on resize only).
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def finalize(self):
        """Recompute the scroll region once, after all rows are added."""
        self.body.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.yview_moveto(0)


def descendants(widget) -> list:
    out = []
    for child in widget.winfo_children():
        out.append(child)
        out.extend(descendants(child))
    return out


def bind_row(row, on_click, normal_bg: str, hover_bg: str):
    """Make a whole row clickable with a hover highlight."""
    widgets = [row] + descendants(row)

    def enter(_):
        for w in widgets:
            try:
                w.configure(bg=hover_bg)
            except tk.TclError:
                pass

    def leave(_):
        for w in widgets:
            try:
                w.configure(bg=normal_bg)
            except tk.TclError:
                pass

    for w in widgets:
        w.bind("<Button-1>", lambda e: on_click())
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)
