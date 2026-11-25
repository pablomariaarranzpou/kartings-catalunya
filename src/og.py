"""Genera las imágenes Open Graph (1200x630) y el favicon. Uso: python src/og.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

TEXT = {
    "es": ("KARTINGS EN CATALUÑA", "Precios 2026 · €/min · carreras con quali", "Barcelona · Girona · Tarragona · Lleida", "Datos consultados el 25/11/2026"),
    "ca": ("KÀRTINGS A CATALUNYA", "Preus 2026 · €/min · curses amb quali", "Barcelona · Girona · Tarragona · Lleida", "Dades consultades el 25/11/2026"),
    "en": ("GO-KARTING IN CATALONIA", "2026 prices · €/min · races with qualifying", "Barcelona · Girona · Tarragona · Lleida", "Data checked on 25/11/2026"),
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
    im = Image.new("RGB", (1200, 630), "#15171a")
    d = ImageDraw.Draw(im)
    for i in range(0, 1200, 60):  # piano rojo/blanco
        d.rectangle([i, 0, i + 30, 22], fill="#d4261c")
        d.rectangle([i + 30, 0, i + 60, 22], fill="#ffffff")
        d.rectangle([i, 608, i + 30, 630], fill="#d4261c")
        d.rectangle([i + 30, 608, i + 60, 630], fill="#ffffff")
    f_title = font(DISPLAY, 96)
    try:
        f_title.set_variation_by_name("Bold Condensed")
    except Exception:
        pass
    d.text((70, 120), title, font=f_title, fill="#f1f2f4")
    d.text((70, 250), sub, font=font(BODY, 44), fill="#c9a3ff")
    d.text((70, 320), provs, font=font(BODY, 34), fill="#a3a9b1")
    # Torre de tiempos mínima
    d.rounded_rectangle([70, 410, 560, 540], 8, fill="#08090a", outline="#2c3035")
    d.rectangle([90, 438, 140, 470], fill="#d4261c")
    d.text((100, 440), "P1", font=font(MONO, 26), fill="#ffffff")
    d.text((160, 438), "1,20 €/min" if lang != "en" else "€1.20/min", font=font(MONO, 34), fill="#c9a3ff")
    d.text((90, 492), date, font=font(MONO, 24), fill="#a3a9b1")
    im.save(OUT / f"og-{lang}.png", optimize=True)

(OUT / "favicon.svg").write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="6" fill="#15171a"/>'
    '<g fill="#fff"><rect x="6" y="6" width="5" height="5"/><rect x="16" y="6" width="5" height="5"/>'
    '<rect x="11" y="11" width="5" height="5"/><rect x="21" y="11" width="5" height="5"/>'
    '<rect x="6" y="16" width="5" height="5"/><rect x="16" y="16" width="5" height="5"/>'
    '<rect x="11" y="21" width="5" height="5"/><rect x="21" y="21" width="5" height="5"/></g>'
    '<rect x="4" y="4" width="3" height="25" fill="#d4261c"/></svg>\n', encoding="utf-8")
print("ok")
