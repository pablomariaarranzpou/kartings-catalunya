"""Genera las imágenes Open Graph (1200x630) y el favicon. Uso: python src/og.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

TEXT = {
    "es": ("Karting en Cataluña", "Precios 2026 · €/min · carreras con quali", "Barcelona · Girona · Tarragona · Lleida", "Datos consultados el 25/11/2026"),
    "ca": ("Kàrting a Catalunya", "Preus 2026 · €/min · curses amb quali", "Barcelona · Girona · Tarragona · Lleida", "Dades consultades el 25/11/2026"),
    "en": ("Go-karting in Catalonia", "2026 prices · €/min · races with qualifying", "Barcelona · Girona · Tarragona · Lleida", "Data checked on 25/11/2026"),
}


def font(names, size):
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


DISPLAY = ["C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/arialbd.ttf"]
BODY = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
MONO = ["C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/cour.ttf"]

for lang, (title, sub, provs, date) in TEXT.items():
    im = Image.new("RGB", (1200, 630), "#ffffff")
    d = ImageDraw.Draw(im)
    f_brand = font(DISPLAY, 40)
    d.text((80, 70), "karting", font=f_brand, fill="#111111")
    w = d.textlength("karting", font=f_brand)
    d.text((80 + w, 70), ".cat", font=f_brand, fill="#8a8d92")
    f_title = font(DISPLAY, 92)
    t = title
    d.text((80, 190), t, font=f_title, fill="#111111")
    f_sub = font(BODY, 42)
    d.rectangle([80, 330, 80 + d.textlength(sub, font=f_sub), 352 + 28], fill="#ffd84d")
    d.text((80, 318), sub, font=f_sub, fill="#111111")
    d.text((80, 410), provs, font=font(BODY, 34), fill="#5f6368")
    d.line([80, 520, 1120, 520], fill="#111111", width=2)
    d.text((80, 545), date, font=font(BODY, 28), fill="#5f6368")
    im.save(OUT / f"og-{lang}.png", optimize=True)

(OUT / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="6" fill="#111111"/>'
    '<g fill="#fff"><rect x="6" y="6" width="5" height="5"/><rect x="16" y="6" width="5" height="5"/>'
    '<rect x="11" y="11" width="5" height="5"/><rect x="21" y="11" width="5" height="5"/>'
    '<rect x="6" y="16" width="5" height="5"/><rect x="16" y="16" width="5" height="5"/>'
    '<rect x="11" y="21" width="5" height="5"/><rect x="21" y="21" width="5" height="5"/></g>'
    '<rect x="4" y="4" width="3" height="25" fill="#ffd84d"/></svg>\n', encoding="utf-8")
print("ok")
