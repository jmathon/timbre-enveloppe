#!/usr/bin/env python3
"""
timbre_dl.py — Met un timbre « Mon Timbre en Ligne » (PDF A4, position 1)
sur une page au format enveloppe DL (220 x 110 mm), avec les adresses
de l'expéditeur (haut gauche) et du destinataire (bas droite, norme La Poste).

Installation :
    pip install pypdf reportlab pypdfium2

Exemples :
    python timbre_dl.py Etiquette.pdf --exp "Julien MATHON|1 rue X|95520 OSNY" --dest @destinataire.txt
    python timbre_dl.py Etiquette.pdf --exp @moi.txt --dest @client.txt -o enveloppe.pdf

Adresses : lignes séparées par « | », ou « @fichier.txt » (une ligne par ligne d'adresse).
Imprimer ensuite en « Enveloppe DL », paysage, échelle 100 %.
"""
import argparse
import io
import sys
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.pdfgen import canvas

MM = 72 / 25.4
DL_W, DL_H = 220 * MM, 110 * MM

# Marges et mise en page (mm)
MARGE = 10                 # marges haut / droite / gauche
STAMP_PAD = 0.7            # marge autour du timbre détecté
EXP_FONT, EXP_SIZE = "Helvetica", 9
DEST_FONT, DEST_SIZE = "Helvetica", 11
DEST_X = 115               # bord gauche du bloc destinataire
DEST_BOTTOM = 18           # dernière ligne (CP + ville) à ≥ 15 mm du bas


def clean_lines(lines) -> list[str]:
    return [l.strip() for l in lines if l.strip()]


def read_address(value: str) -> list[str]:
    if value.startswith("@"):
        return clean_lines(Path(value[1:]).read_text(encoding="utf-8").splitlines())
    return clean_lines(value.split("|"))


def detect_stamp_box(pdf_path: str, page_index: int = 0) -> tuple[float, float, float, float]:
    """Retourne (x0, y0, x1, y1) en points PDF (origine bas-gauche) de la zone imprimée."""
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        page = pdf[page_index]
        w_pt, h_pt = page.get_size()
        scale = 150 / 72
        img = page.render(scale=scale, grayscale=True).to_pil().convert("L")
    finally:
        pdf.close()
    bbox = img.point(lambda v: 255 if v < 235 else 0).getbbox()
    if bbox is None:
        raise ValueError("Aucun timbre trouvé dans le PDF.")
    l, t, r, b = (v / scale for v in bbox)
    pad = STAMP_PAD * MM
    return l - pad, h_pt - b - pad, r + pad, h_pt - t + pad


def build_overlay(exp: list[str], dest: list[str]) -> PdfReader:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(DL_W, DL_H))

    # Expéditeur : haut gauche
    c.setFont(EXP_FONT, EXP_SIZE)
    y = DL_H - MARGE * MM - EXP_SIZE
    for line in exp:
        c.drawString(MARGE * MM, y, line)
        y -= EXP_SIZE * 1.2

    # Destinataire : bloc bas droite, aligné à gauche, dernière ligne en bas
    c.setFont(DEST_FONT, DEST_SIZE)
    lead = DEST_SIZE * 1.25
    y = DEST_BOTTOM * MM + lead * (len(dest) - 1)
    for line in dest:
        c.drawString(DEST_X * MM, y, line)
        y -= lead

    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def compose(timbre_pdf: str, exp: list[str], dest: list[str]) -> tuple[bytes, list[str]]:
    """Construit le PDF DL. Retourne (contenu PDF, avertissements)."""
    warnings = []
    for label, lines in (("expéditeur", exp), ("destinataire", dest)):
        if len(lines) > 6:
            warnings.append(f"Adresse {label} : 6 lignes maximum (norme La Poste).")
    for line in dest:
        if len(line) > 38:
            warnings.append(f"Ligne de plus de 38 caractères : « {line} »")

    x0, y0, x1, y1 = detect_stamp_box(timbre_pdf)

    page = build_overlay(exp, dest).pages[0]
    stamp = PdfReader(timbre_pdf).pages[0]
    stamp.cropbox = RectangleObject([x0, y0, x1, y1])
    tx = DL_W - MARGE * MM - x1
    ty = DL_H - MARGE * MM - y1
    page.merge_transformed_page(stamp, Transformation().translate(tx, ty), over=True, expand=False)

    if (DEST_X * MM) < (x1 + tx) and (DEST_BOTTOM * MM + DEST_SIZE * 1.25 * len(dest)) > (y0 + ty):
        warnings.append("Le bloc destinataire chevauche le timbre.")

    w = PdfWriter()
    w.add_page(page)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue(), warnings


def main() -> None:
    ap = argparse.ArgumentParser(description="Timbre La Poste + adresses sur enveloppe DL")
    ap.add_argument("timbre", help="PDF A4 téléchargé sur Mon Timbre en Ligne")
    ap.add_argument("--exp", required=True, help="Adresse expéditeur (« L1|L2|L3 » ou @fichier.txt)")
    ap.add_argument("--dest", required=True, help="Adresse destinataire (« L1|L2|L3 » ou @fichier.txt)")
    ap.add_argument("-o", "--output", help="PDF de sortie (défaut : <timbre>_DL.pdf)")
    args = ap.parse_args()

    try:
        data, warnings = compose(args.timbre, read_address(args.exp), read_address(args.dest))
    except ValueError as e:
        sys.exit(f"Erreur : {e}")
    for w in warnings:
        print(f"Attention : {w}")

    out = args.output or str(Path(args.timbre).with_name(Path(args.timbre).stem + "_DL.pdf"))
    Path(out).write_bytes(data)
    print(f"OK : {out}  (imprimer en Enveloppe DL, paysage, 100 %)")


if __name__ == "__main__":
    main()
