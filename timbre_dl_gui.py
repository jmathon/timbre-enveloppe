#!/usr/bin/env python3
"""
timbre_dl_gui.py — Petite IHM pour timbre_dl.py (à placer dans le même dossier).

    pip install pypdf reportlab pypdfium2 pillow
    pythonw timbre_dl_gui.py

L'adresse de l'expéditeur et le dernier dossier utilisé sont mémorisés
dans ~/.timbre_dl.json.
"""
import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pypdfium2 as pdfium
from PIL import ImageTk

import timbre_dl

CONFIG = Path.home() / ".timbre_dl.json"
PREVIEW_W = 660


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    try:
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def open_file(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Timbre + adresses — enveloppe DL")
        self.resizable(False, False)
        self.cfg = load_config()
        self.pdf_bytes: bytes | None = None
        self.preview_img = None
        self._after_id = None
        self.last_output: str | None = None

        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self, padding=10)
        main.grid(sticky="nsew")

        # Timbre
        row = ttk.Frame(main)
        row.grid(row=0, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(row, text="Timbre (PDF) :").pack(side="left")
        self.timbre_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.timbre_var, width=70).pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(row, text="Parcourir…", command=self.browse).pack(side="left")
        self.timbre_var.trace_add("write", lambda *_: self.schedule_preview())

        # Adresses
        self.exp_txt = self._address_box(main, "Expéditeur (mémorisé)", 1, 0)
        self.dest_txt = self._address_box(main, "Destinataire", 1, 1)
        self.exp_txt.insert("1.0", self.cfg.get("expediteur", ""))

        # Aperçu
        frame = ttk.LabelFrame(main, text="Aperçu (220 × 110 mm)")
        frame.grid(row=2, column=0, columnspan=2, **pad)
        self.canvas = tk.Canvas(frame, width=PREVIEW_W, height=PREVIEW_W // 2,
                                bg="#e9e9e9", highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)

        # Statut + boutons
        self.status = ttk.Label(main, text="Choisis le PDF du timbre.", foreground="#555", wraplength=PREVIEW_W)
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", **pad)
        btns = ttk.Frame(main)
        btns.grid(row=4, column=0, columnspan=2, sticky="e", **pad)
        self.open_btn = ttk.Button(btns, text="Ouvrir le PDF", command=self.open_output, state="disabled")
        self.open_btn.pack(side="right", padx=4)
        ttk.Button(btns, text="Enregistrer le PDF…", command=self.save).pack(side="right", padx=4)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _address_box(self, parent, title, row, col) -> tk.Text:
        f = ttk.LabelFrame(parent, text=title)
        f.grid(row=row, column=col, sticky="nsew", padx=8, pady=4)
        t = tk.Text(f, width=40, height=6, font=("Segoe UI", 10), undo=True)
        t.pack(padx=6, pady=6)
        t.bind("<<Modified>>", self._on_modified)
        return t

    def _on_modified(self, event) -> None:
        event.widget.edit_modified(False)
        self.schedule_preview()

    @staticmethod
    def lines(widget: tk.Text) -> list[str]:
        return timbre_dl.clean_lines(widget.get("1.0", "end").splitlines())

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            title="PDF du timbre (Mon Timbre en Ligne)",
            initialdir=self.cfg.get("dossier", str(Path.home() / "Downloads")),
            filetypes=[("PDF", "*.pdf")],
        )
        if path:
            self.cfg["dossier"] = str(Path(path).parent)
            self.timbre_var.set(path)

    def schedule_preview(self) -> None:
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(350, self.refresh_preview)

    def refresh_preview(self) -> None:
        self._after_id = None
        self.pdf_bytes = None
        timbre = self.timbre_var.get().strip()
        if not timbre or not Path(timbre).is_file():
            self.set_status("Choisis le PDF du timbre.")
            return
        try:
            data, warnings = timbre_dl.compose(timbre, self.lines(self.exp_txt), self.lines(self.dest_txt))
        except Exception as e:  # PDF illisible, pas de timbre…
            self.set_status(f"Erreur : {e}", error=True)
            return
        self.pdf_bytes = data
        doc = pdfium.PdfDocument(data)
        try:
            page = doc[0]
            scale = PREVIEW_W / page.get_size()[0]
            pil = page.render(scale=scale).to_pil()
        finally:
            doc.close()
        self.preview_img = ImageTk.PhotoImage(pil)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.preview_img)
        if warnings:
            self.set_status("⚠ " + "  ·  ".join(warnings), error=True)
        else:
            self.set_status("Prêt. Impression : Enveloppe DL, paysage, échelle 100 %.")

    def set_status(self, text: str, error: bool = False) -> None:
        self.status.configure(text=text, foreground="#b00020" if error else "#555")

    def save(self) -> None:
        self.refresh_preview()
        if not self.pdf_bytes:
            messagebox.showwarning("Timbre", "Choisis d'abord un PDF de timbre valide.")
            return
        if not self.lines(self.dest_txt):
            if not messagebox.askyesno("Timbre", "Pas d'adresse destinataire. Enregistrer quand même ?"):
                return
        src = Path(self.timbre_var.get())
        out = filedialog.asksaveasfilename(
            title="Enregistrer le PDF pour enveloppe DL",
            initialdir=str(src.parent), initialfile=f"{src.stem}_DL.pdf",
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
        )
        if not out:
            return
        try:
            Path(out).write_bytes(self.pdf_bytes)
        except OSError as e:
            messagebox.showerror("Timbre", f"Impossible d'enregistrer :\n{e}")
            return
        self.last_output = out
        self.open_btn.configure(state="normal")
        self.set_status(f"Enregistré : {out}")
        self.persist()

    def open_output(self) -> None:
        if self.last_output:
            open_file(self.last_output)

    def persist(self) -> None:
        self.cfg["expediteur"] = self.exp_txt.get("1.0", "end").strip()
        save_config(self.cfg)

    def on_close(self) -> None:
        self.persist()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
