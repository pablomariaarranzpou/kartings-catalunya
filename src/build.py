"""Genera la web estática (ES/CA/EN) y la versión artifact.

Uso:  python src/build.py [--artifact RUTA]
Salida: index.html, ca/index.html, en/index.html, sitemap.xml, robots.txt
"""
import html
import json
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data import KARTINGS, EXCLUDED, LEAGUE, CHECKED, GEO, ZONES, BARCELONA, MAPS  # noqa: E402
from i18n import UI, LANGS, LOCALE, AREA_TXT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Cambia BASE a "https://kartings.cat/" cuando el dominio apunte a GitHub Pages (pasos en el README).
BASE = "https://pablomariaarranzpou.github.io/kartings-catalunya/"
BRAND = "kartings.cat"
# Google Search Console: pega aquí el valor "content" de la etiqueta HTML de verificación
GOOGLE_VERIFY = "eJjK1eOSUA6XvvRNbV2d2BOVXilws1gfBw6FOxWXxk4"
REPO = "https://github.com/pablomariaarranzpou/kartings-catalunya"
PATHS = {"es": "", "ca": "ca/", "en": "en/"}
DATE_TXT = {"es": "25 de noviembre de 2026", "ca": "25 de novembre de 2026", "en": "25 November 2026"}
BAD = {"old", "third"}
FONTS = "https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800&display=swap"

e = html.escape


# ------------------------------------------------------------------ utilidades
def tx(v, L):
    return v[L] if isinstance(v, dict) and L in v else v


def dec(x):
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def num(x, L, places=2):
    s = f"{x:.{places}f}"
    return s.replace(".", ",") if L != "en" else s


def money(x, L):
    if x is None:
        return UI[L]["not_published"]
    d = dec(x)
    s = num(d, L, 0 if d == d.to_integral() else 2)
    return f"€{s}" if L == "en" else f"{s} €"


def permin(p, m):
    return dec(Decimal(str(p)) / Decimal(m)) if p is not None and m else None


def pm_txt(v, L):
    if v is None:
        return UI[L]["no_data"]
    return f"€{num(v, L)}/min" if L == "en" else f"{num(v, L)} €/min"


def struct_txt(struct, L):
    return " + ".join(tx(v, L) if k == "raw" else UI[L]["struct"][k].format(n=v) for k, v in struct)


TIMED = {"free": 1, "warm": 1, "quali": 1, "race": 1, "prefinal": 1, "final": 1, "total": 1, "endurh": 60}
LAPS = {"qualilaps", "racelaps", "recon", "freelaps", "prefinallaps", "finallaps"}


def track_time(struct):
    """(minutos conocidos, hay fases por vueltas, hay fases sin cifra). Nunca estima la duración de una vuelta."""
    mins, laps, unknown = 0, False, False
    for k, v in struct:
        if k in TIMED:
            mins += v * TIMED[k]
        elif k in LAPS:
            laps = True
        else:
            unknown = True
    return mins, laps, unknown


def track_txt(struct, L):
    u = UI[L]
    mins, laps, unknown = track_time(struct)
    if unknown:
        return u["track_unknown"]
    if laps:
        return u["track_atleast"].format(n=mins) if mins else u["track_laps"]
    return u["track_exact"].format(n=mins)


def phases_html(struct, L):
    u = UI[L]
    out = []
    for k, v in struct:
        if k == "raw":
            out.append(f'<li class="ph ph-raw">{e(tx(v, L))}</li>')
            continue
        val = (u["unit_laps"] if k in LAPS else u["unit_h"] if k == "endurh" else u["unit_min"]).format(n=v)
        kind = {"qualilaps": "quali", "racelaps": "race", "warm": "free", "freelaps": "free", "prefinal": "race", "prefinallaps": "race",
                "final": "race", "finallaps": "race"}.get(k, k)
        out.append(f'<li class="ph ph-{kind}"><b>{e(u["ph"][k])}</b> {e(val)}</li>')
    return f'<ol class="phases">{"".join(out)}</ol>'


def ints(n, L):
    s = f"{n:,}"
    return s if L == "en" else s.replace(",", ".")


def maps_url(k):
    from urllib.parse import quote
    name = MAPS[k["id"]][2]
    town = k["town"].split(" (")[0].split("–")[0]
    return "https://www.google.com/maps/search/?api=1&query=" + quote(f"{name} {town}")


def stars_html(k, L, cls="stars", as_link=True):
    u = UI[L]
    if k["id"] not in MAPS:
        return f'<span class="{cls} none">{e(u["no_rating"])}</span>'
    st, n, _ = MAPS[k["id"]]
    low = " low" if st < 4.0 else ""
    inner = (f'<span aria-hidden="true">★</span> {num(st, L, 1)}'
             f' <small>({e(u["reviews"].format(n=ints(n, L)))})</small>')
    if not as_link:
        return f'<span class="{cls}{low}">{inner}</span>'
    return (f'<a class="{cls}{low}" href="{e(maps_url(k))}" target="_blank" rel="noopener nofollow" '
            f'title="{e(u["maps_open"])}">{inner}</a>')


def people_txt(r, L):
    u = UI[L]
    if r["minp"] and r["maxp"]:
        return u["min_people_range"].format(a=r["minp"], b=r["maxp"])
    if r["minp"]:
        return u["min_people"].format(n=r["minp"])
    return u["min_unknown"]


def link(url, label, cls="src"):
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="noopener nofollow">{e(label)}</a>'


def flag_txt(flags, L, skip=()):
    u = UI[L]
    out = [f'<span class="flag{" ok" if f == "iva" else ""}" title="{e(u["flag_long"][f])}">{e(u["flag"][f])}</span>'
           for f in flags if f not in skip]
    return "".join(out)


def ok_sessions(k):
    return [s for s in k["sessions"] if s["mins"] and not (set(s["flags"]) & BAD)]


def best_deal(k):
    ds = [(permin(d["price"], d["mins"]), d) for d in k["deals"] if not set(d["flags"]) & BAD]
    return min(ds, key=lambda t: t[0]) if ds else (None, None)


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def km_round(d):
    return max(1, round(d)) if d < 20 else int(round(d / 5) * 5)


def ranks(values):
    return [1 + sum(1 for w in values if w < v) for v in values]


OK = [k for k in KARTINGS if k["status"] == "ok"]
BYID = {k["id"]: k for k in KARTINGS}


def geo(k):
    z, la, lo = GEO[k["id"]]
    return z, la, lo, km_round(km(BARCELONA, (la, lo)))


# Zonas de búsqueda: provincias + zonas turísticas o comarcales (un circuito puede estar en varias).
AREA_DEF = {
    "barcelona": "B", "girona": "G", "tarragona": "T", "lleida": "L",
    "costa-brava": ["empuriabrava", "cross", "roses", "palamos", "lescala", "lloret", "blanes", "regencos"],
    "costa-daurada": ["altafulla", "tarraco", "salou", "electricsalou", "vendrell", "comarruga"],
    "delta-ebre": ["calafat"],
    "pirineu": ["elpla"],
    "penedes": ["penedes", "vendrell", "comarruga"],
    "valles": ["cardedeu", "nurburgreen", "kartodrom"],
    "catalunya-central": ["sallent", "osona", "parcmotor"],
    "baix-llobregat": ["ikb", "gene", "minilandia"],
}
PROVS = ["barcelona", "girona", "tarragona", "lleida"]
PROV_OF = {"B": "barcelona", "G": "girona", "T": "tarragona", "L": "lleida"}
AREA_IDS = {a: {k["id"] for k in KARTINGS if (k["prov"] == d if isinstance(d, str) else k["id"] in d)}
            for a, d in AREA_DEF.items()}
CTX = {"area": None, "home": "", "mode": "site"}  # página que se está generando


def areas_of(k):
    return [a for a in AREA_DEF if k["id"] in AREA_IDS[a]]


def page_path(L, area=None):
    return PATHS[L] + (f"karting-{area}/" if area else "")


def rel(L, area=None):
    return "../" * page_path(L, area).count("/")


def href_to(L, area=None):
    """Enlace relativo desde la página actual a otra página del sitio (absoluto en el artifact)."""
    if CTX["mode"] == "artifact":
        return BASE + page_path(L, area)
    return (CTX["rel"] + page_path(L, area)) or "./"


def klink(k, pid):
    if CTX["area"] and k["id"] not in AREA_IDS[CTX["area"]]:
        return f'{CTX["home"]}#k-{k["id"]}'
    return "#" + pid("k-" + k["id"])


def area_stats(a):
    ks = [k for k in OK if k["id"] in AREA_IDS[a]]
    unc = [k for k in KARTINGS if k["id"] in AREA_IDS[a] and k["status"] != "ok"]
    sess = [(permin(s["price"], s["mins"]), k, s) for k in ks for s in ok_sessions(k)]
    best_s = min(sess, key=lambda t: (t[0], t[2]["price"])) if sess else None
    minp = min((s["price"] for k in ks for s in k["sessions"] if s["price"] is not None and not set(s["flags"]) & BAD), default=None)
    races = [(r["price"], k, r) for k in ks for r in k["races"]
             if r["quali"] and r["price"] is not None and not set(r["flags"]) & (BAD | {"junior", "team"})]
    best_r = min(races, key=lambda t: t[0]) if races else None
    return ks, unc, best_s, minp, best_r


def nearby(a, n=3):
    pts = [GEO[i][1:] for i in AREA_IDS[a]]
    c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    out = sorted((km(c, GEO[k["id"]][1:]), k) for k in OK if k["id"] not in AREA_IDS[a])
    return [(km_round(d), k) for d, k in out[:n]]


# ------------------------------------------------------------------ cabecera
def header(L, mode, pid):
    u = UI[L]
    langs = []
    for x in LANGS:
        href = f"#{x}" if mode == "artifact" else href_to(x, CTX["area"])
        cur = ' aria-current="page"' if x == L else ""
        langs.append(f'<a href="{href}" hreflang="{x}" lang="{x}"{cur}>{x.upper()}</a>')
    home = "" if not CTX["area"] else CTX["home"]
    nav = "".join(f'<a href="{home if a in ("rankings", "faq") else ""}#{pid(a)}">{e(u[b])}</a>' for a, b in
                  [("buscador", "nav_finder"), ("circuitos", "nav_dir"), ("rankings", "nav_rank"), ("faq", "nav_faq")])
    name, tld = BRAND.split(".", 1)
    return f'''
<header class="site-h"><div class="wrap site-h-in">
  <a class="brand" href="{CTX["home"] if CTX["area"] else "#" + pid("top")}">{e(name)}<span>.{e(tld)}</span></a>
  <nav class="site-nav" aria-label="{e(u["nav_finder"])}">{nav}</nav>
  <div class="langs">{"".join(langs)}</div>
</div></header>'''


# ------------------------------------------------------------------ buscador
def session_rows(k, L, pid):
    """Una fila por tanda publicada; el JS se queda con la mejor de cada circuito según filtros y orden."""
    u = UI[L]
    z, la, lo, dkm = geo(k)
    dv, d = best_deal(k)
    out = []
    for s in [s for s in k["sessions"] if s["price"] is not None and not set(s["flags"]) & BAD]:
        v = permin(s["price"], s["mins"])
        sub = f'{s["mins"]} min · {pm_txt(v, L)}' if s["mins"] else u["dur_unknown"]
        pack = ""
        if dv is not None and (v is None or dv < v):
            pack = f'<span class="r-pack">{e(u["with_pack"].format(v=pm_txt(dv, L)))}</span>'
        lab = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
        out.append(row_html(k, L, pid, "session", dict(price=s["price"], eurmin=v if v is not None else "", mins=s["mins"] or ""),
                            big=money(s["price"], L), sub=sub, extra=pack, line=lab,
                            flags=[f for f in k["flags"] if f in ("season", "snippet", "unconfirmed")] + list(s["flags"]),
                            src=s["src"], dkm=dkm, zone=z, la=la, lo=lo, hidden=bool(out)))
    return "".join(out)


def race_rows(k, L, pid):
    u = UI[L]
    z, la, lo, dkm = geo(k)
    out = []
    for r in k["races"]:
        if not r["quali"] or r["price"] is None or set(r["flags"]) & (BAD | {"junior", "team"}):
            continue
        minp = r["minp"]
        if isinstance(minp, str):  # p. ej. "2–5": nos quedamos con el mayor por prudencia
            minp = int(minp.split("–")[-1])
        mins, laps, unknown = track_time(r["struct"])
        exact = mins > 0 and not laps and not unknown
        em = permin(r["price"], mins) if exact else None
        summ = track_txt(r["struct"], L) + (" · " + u["eurmin_track"].format(v=pm_txt(em, L)) if em is not None else "")
        cond = " · ".join(x for x in [people_txt(r, L), tx(r["cond"], L) if r["cond"] else "",
                                      tx(r["price_note"], L) if r["price_note"] else ""] if x)
        out.append(row_html(k, L, pid, "race", dict(price=r["price"], minp=minp or "", maxp=r["maxp"] or "",
                                                    track=mins if not unknown else "", eurmin=em if em is not None else ""),
                            big=money(r["price"], L), sub={"es": "por persona", "ca": "per persona", "en": "per person"}[L], extra='<span class="r-total"></span>',
                            line=tx(r["name"], L), phases=phases_html(r["struct"], L),
                            summary=f'<p class="r-track{" exact" if exact else ""}">{e(summ)}</p>',
                            cond=cond, flags=[f for f in k["flags"] if f in ("season", "snippet", "unconfirmed")] + list(r["flags"]), src=r["src"],
                            dkm=dkm, zone=z, la=la, lo=lo, hidden=True))
    return "".join(out)


def row_html(k, L, pid, mode, data, big, sub, extra, line, flags, src, dkm, zone, la, lo, cond="", hidden=False, phases="", summary=""):
    u = UI[L]
    data = dict(data, stars=MAPS[k["id"]][0] if k["id"] in MAPS else "", reviews=MAPS[k["id"]][1] if k["id"] in MAPS else "")
    attrs = "".join(f' data-{a}="{v}"' for a, v in data.items())
    meta = " · ".join(x for x in [k["town"], u["type_short"][k["type"]] + (f' ({u["electric"]})' if k.get("electric") else ""),
                                   tx(k["kart"], L) if k.get("kart") else ""] if x)
    fl = flag_txt(sorted(set(flags)), L, skip=("noyear",))
    return f'''<li class="res" data-mode="{mode}" data-k="{k["id"]}" data-areas="{" ".join(areas_of(k))}" data-lat="{la}" data-lon="{lo}"{attrs}{" hidden" if hidden else ""}>
  <div class="r-main">
    <span class="badge" hidden></span>
    <h3><a href="{klink(k, pid)}">{e(k["name"])}</a> {stars_html(k, L)}</h3>
    <p class="r-meta">{e(meta)}</p>
    {f'<p class="r-line">{e(line)}</p>' if line else ""}
    {phases}{summary}
    {f'<p class="r-cond">{e(cond)}</p>' if cond else ""}
    {f'<p class="r-flags">{fl}</p>' if fl else ""}
  </div>
  <div class="r-price"><strong>{e(big)}</strong><span class="r-sub">{e(sub)}</span>{extra}</div>
  <div class="r-foot"><span class="dist">{e(u["from_bcn"].format(km=dkm))}</span>{link(src, u["see_price"])}</div>
</li>'''


def finder(L, pid):
    u = UI[L]
    rows = "".join(session_rows(k, L, pid) for k in OK) + "".join(race_rows(k, L, pid) for k in OK)
    pre = CTX["area"]

    def opt(a):
        return f'<option value="{a}"{" selected" if a == pre else ""}>{e(AREA_TXT[a][L][0])}</option>'
    zones = (f'<option value="*"{"" if pre else " selected"}>{e(u["zone_all"])}</option>'
             f'<optgroup label="{e(u["grp_prov"])}">{"".join(opt(a) for a in PROVS)}</optgroup>'
             f'<optgroup label="{e(u["grp_area"])}">{"".join(opt(a) for a in AREA_DEF if a not in PROVS)}</optgroup>')
    stars = f'<option value="0">{e(u["stars_any"])}</option>' + "".join(
        f'<option value="{v}">{e(u["stars_opt"].format(v=num(v, L, 1)))}</option>' for v in (4.0, 4.3, 4.5))
    durs = f'<option value="0">{e(u["dur_any"])}</option>' + "".join(
        f'<option value="{n}">{e(u["dur_opt"].format(n=n))}</option>'
        for n in sorted({s["mins"] for k in OK for s in k["sessions"] if s["mins"] and s["mins"] > 8 and not set(s["flags"]) & BAD}))
    cfg = dict(lang={"es": "es-ES", "ca": "ca-ES", "en": "en-GB"}[L], count=u["count"], count1=u["count1"],
               total=u["total_for"], from_bcn=u["from_bcn"], from_you=u["from_you"], near_ok=u["near_ok"],
               near_fail=u["near_fail"], eurmin_session=u["sort_eurmin"], eurmin_race=u["sort_eurmin_track"],
               badge={"price": u["best_price"], "eurmin": u["best_eurmin"], "dist": u["best_dist"],
                      "rating": u["best_rating"], "track": u["best_track"]})
    n_session = sum(1 for k in OK if session_rows(k, L, pid) and (not pre or k["id"] in AREA_IDS[pre]))
    return f'''
<section class="finder" id="{pid("buscador")}">
  <script type="application/json" class="cfg">{json.dumps(cfg, ensure_ascii=False)}</script>
  <form class="controls" action="#" novalidate>
    <fieldset class="modes">
      <legend>{e(u["q_mode"])}</legend>
      <label class="mode"><input type="radio" id="{L}-m-s" name="mode-{L}" value="session" checked><span><b>{e(u["mode_session"])}</b><small>{e(u["mode_session_sub"])}</small></span></label>
      <label class="mode"><input type="radio" id="{L}-m-r" name="mode-{L}" value="race"><span><b>{e(u["mode_race"])}</b><small>{e(u["mode_race_sub"])}</small></span></label>
    </fieldset>
    <div class="ctl-row">
      <label class="ctl"><span>{e(u["zone_label"])}</span><select id="{L}-zone" data-ctl="zone">{zones}</select></label>
      <label class="ctl ppl" hidden><span>{e(u["people_label"])}</span>
        <span class="stepper"><button type="button" data-step="-1" aria-label="−1">−</button><input id="{L}-n" type="number" inputmode="numeric" min="1" max="40" value="6" data-ctl="n"><button type="button" data-step="1" aria-label="+1">+</button></span></label>
      <label class="ctl dur"><span>{e(u["dur_label"])}</span><select id="{L}-dur" data-ctl="dur">{durs}</select></label>
      <label class="ctl"><span>{e(u["stars_label"])}</span><select id="{L}-stars" data-ctl="stars">{stars}</select></label>
      <label class="ctl"><span>{e(u["sort_label"])}</span><select id="{L}-sort" data-ctl="sort">
        <option value="eurmin" selected>{e(u["sort_eurmin"])}</option><option value="price">{e(u["sort_price"])}</option><option value="track" hidden disabled>{e(u["sort_track"])}</option><option value="rating">{e(u["sort_rating"])}</option><option value="dist">{e(u["sort_dist"])}</option></select></label>
      <button type="button" class="near" data-near>{e(u["near_me"])}</button>
    </div>
  </form>
  <div class="res-head"><p class="count" aria-live="polite">{e(u["count"].format(n=n_session))}</p><p class="checked">{e(u["checked_note"])}</p></div>
  <p class="geo-msg" hidden></p>
  <ol class="results">{rows}</ol>
  <p class="empty" hidden>{e(u["none"])}</p>
  {areas_nav(L)}
</section>'''


def areas_nav(L):
    u = UI[L]
    cur = CTX["area"]
    links = "".join(f'<a href="{href_to(L, a)}"{" aria-current=page" if a == cur else ""}>{e(AREA_TXT[a][L][0])}</a>'
                    for a in AREA_DEF)
    return f'<nav class="areas" aria-label="{e(u["areas_title"])}"><h2>{e(u["other_areas"] if cur else u["areas_title"])}</h2><p>{links}</p></nav>'


def intro(L, pid):
    u = UI[L]
    a = CTX["area"]
    if a:
        name, h1in, in_ = AREA_TXT[a][L]
        ks, unc, best_s, minp, best_r = area_stats(a)
        sub = (u["area_sub1"] if len(ks) == 1 else u["area_sub"]).format(n=len(ks), in_=in_)
        if unc:
            sub += u["area_unc"].format(n=len(unc))
        near = ""
        if len(ks) <= 2:
            lst = ", ".join(f'<a href="{CTX["home"]}#k-{k["id"]}">{e(k["name"])}</a> (≈ {d} km)' for d, k in nearby(a))
            near = f'<p class="near-areas">{u["nearby"].format(list=lst)}</p>'
        return f'''
<div class="intro-block" id="{pid("top")}">
  <div class="wrap">
    <p class="crumbs"><a href="{CTX["home"]}">{e(u["crumb_home"])}</a> <span aria-hidden="true">›</span> {e(name)}</p>
    <h1>{e(u["area_h1"].format(h1in=h1in))}</h1>
    <p class="sub">{e(sub)}</p>
    {near}
    {finder(L, pid)}
  </div>
</div>'''
    return f'''
<div class="intro-block" id="{pid("top")}">
  <div class="wrap">
    <h1>{e(u["h1"])}</h1>
    <p class="sub">{e(u["sub"].format(n_ok=len(OK)))}</p>
    {finder(L, pid)}
  </div>
</div>'''


# ------------------------------------------------------------------ directorio
def entry(k, L, pid):
    u = UI[L]
    z, la, lo, dkm = geo(k)
    typ = u["type_short"][k["type"]] + (f' ({u["electric"]})' if k.get("electric") else "")
    prices = [s["price"] for s in k["sessions"] if not set(s["flags"]) & BAD]
    frm = f'{u["from_"]} {money(min(prices), L)}' if prices else (u["uncertain_tag"] if k["status"] != "ok" else "")
    meta = []
    if k.get("track"):
        meta.append((u["lbl_track"], e(tx(k["track"], L))))
    if k.get("kart"):
        meta.append((u["lbl_kart"], e(tx(k["kart"], L))))
    web = []
    if k.get("web"):
        web.append(link(k["web"], k["web"].split("//")[1].split("/")[0].replace("www.", ""), "web"))
    if k.get("pdf"):
        web.append(link(k["pdf"], u["pdf"], "web"))
    if web:
        meta.append((u["official_web"], " · ".join(web)))
    meta.append((u["lbl_rating"], stars_html(k, L)))
    dl = "".join(f"<div><dt>{e(a)}</dt><dd>{b}</dd></div>" for a, b in meta)

    def li(what, small, val, flags, src, offer=False):
        off = f'<span class="flag offer">{e(u["offer"])}</span>' if offer else ""
        return (f'<li><span class="what">{e(what)}{f"<small>{e(small)}</small>" if small else ""}</span>'
                f'<span class="val">{val}</span><span class="tail">{off}{flag_txt(flags, L)}{link(src, u["source"])}</span></li>')

    parts = []
    if k["sessions"]:
        items = []
        for s in k["sessions"]:
            lbl = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
            dur = f'{s["mins"]} min · {pm_txt(permin(s["price"], s["mins"]), L)}' if s["mins"] else u["dur_unknown"]
            items.append(li(lbl or u["lbl_sessions"], dur, money(s["price"], L), s["flags"], s["src"]))
        parts.append(f'<h4>{e(u["lbl_sessions"])}</h4><ul class="lines">{"".join(items)}</ul>')
    if k["deals"]:
        items = [li(tx(d["label"], L), " · ".join(x for x in [f'{d["mins"]} min · {pm_txt(permin(d["price"], d["mins"]), L)}',
                                                              tx(d["cond"], L) if d["cond"] else ""] if x),
                    money(d["price"], L), d["flags"], d["src"], d["offer"]) for d in k["deals"]]
        parts.append(f'<h4>{e(u["lbl_deals"])}</h4><ul class="lines">{"".join(items)}</ul>')
    if k["races"]:
        items = []
        for r in k["races"]:
            small = " · ".join(x for x in [struct_txt(r["struct"], L), track_txt(r["struct"], L), people_txt(r, L) if r["minp"] else "",
                                           tx(r["cond"], L) if r["cond"] else "", tx(r["price_note"], L) if r["price_note"] else ""] if x)
            val = money(r["price"], L) + (u["per_person"] if r["price"] is not None and "team" not in r["flags"] else "")
            items.append(li(tx(r["name"], L), small, val, r["flags"], r["src"]))
        parts.append(f'<h4>{e(u["lbl_races"])}</h4><ul class="lines">{"".join(items)}</ul>')
    notes = "".join(f"<li>{e(n)}</li>" for n in tx(k["notes"], L))
    xsrc = f'<p class="xsrc">{link(k["src"], u["source"])}</p>' if k.get("src") else ""
    unc = f'<span class="flag">{e(u["uncertain_tag"])}</span>' if k["status"] != "ok" else ""
    return f'''
<details class="k{" unc" if k["status"] != "ok" else ""}" id="{pid("k-" + k["id"])}">
  <summary><span class="k-name">{e(k["name"])}</span><span class="k-meta">{e(k["town"])} · {e(typ)} · {e(u["from_bcn"].format(km=dkm))}</span>{stars_html(k, L, "stars k-stars", as_link=False) if k["id"] in MAPS else "<span class=k-stars></span>"}<span class="k-from">{e(frm)}</span></summary>
  <div class="k-body">
    <div class="k-flags">{unc}{flag_txt(k["flags"], L)}</div>
    {f'<dl class="meta">{dl}</dl>' if dl else ""}
    <div class="k-cols"><div>{"".join(parts)}</div><div><h4>{e(u["lbl_notes"])}</h4><ul class="notes">{notes}</ul>{xsrc}</div></div>
  </div>
</details>'''


def directory(L, pid):
    u = UI[L]
    groups = []
    a = CTX["area"]
    for pv in PROVS:
        ks = sorted([k for k in KARTINGS if PROV_OF[k["prov"]] == pv and (not a or k["id"] in AREA_IDS[a])],
                    key=lambda k: (k["status"] != "ok", k["name"]))
        if not ks:
            continue
        head = e(AREA_TXT[pv][L][0]) if a == pv else f'<a href="{href_to(L, pv)}">{e(AREA_TXT[pv][L][0])}</a>'
        groups.append(f'<div class="zone"><h3>{head}</h3>{"".join(entry(k, L, pid) for k in ks)}</div>')
    if a:
        return f'''
<section class="sec" id="{pid("circuitos")}">
  <div class="wrap">
    <h2>{e(u["dir_title_area"].format(in_=AREA_TXT[a][L][2]))}</h2>
    <p class="lead">{e(u["dir_intro"])}</p>
    {"".join(groups)}
  </div>
</section>'''
    exc = "".join(f'<li><b>{e(x["name"])}</b> · {e(x["town"])}. {e(tx(x["why"], L))} {link(x["src"], u["source"])}</li>' for x in EXCLUDED)
    return f'''
<section class="sec" id="{pid("circuitos")}">
  <div class="wrap">
    <h2>{e(u["dir_title"])}</h2>
    <p class="lead">{e(u["dir_intro"])}</p>
    {"".join(groups)}
    <div class="side">
      <div><h3>{e(u["excluded_title"])}</h3><ul class="notes">{exc}</ul></div>
      <div><h3>{e(u["league_title"])}</h3><p>{e(u["league_text"])} {link(LEAGUE["src"], LEAGUE["name"])}</p></div>
    </div>
  </div>
</section>'''


# ------------------------------------------------------------------ rankings
def table(headers, rows):
    th = "".join(f'<th scope="col"{" class=n" if n else ""}>{e(h)}</th>' for h, n in headers)
    return f'<div class="scroll"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def rankings(L, pid):
    u = UI[L]
    srows = sorted([(permin(s["price"], s["mins"]), k, s) for k in OK for s in ok_sessions(k)], key=lambda t: (t[0], t[2]["price"]))
    b = []
    for r, (v, k, s) in zip(ranks([t[0] for t in srows]), srows):
        prod = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
        b.append(f'<tr{" class=best" if r == 1 else ""}><td class="n rk">{r}</td><th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a>'
                 f'{f"<small>{e(prod)}</small>" if prod else ""}</th><td class="n">{money(s["price"], L)}</td><td class="n">{s["mins"]} min</td>'
                 f'<td class="n hl">{pm_txt(v, L)}</td><td>{stars_html(k, L)}</td><td>{flag_txt(s["flags"], L)}{link(s["src"], u["source"])}</td></tr>')
    tb = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_price"], 1), (u["th_minutes"], 1), ("€/min", 1), ("Google", 0), (u["th_source"], 0)], b)
    drows = sorted([(permin(d["price"], d["mins"]), k, d) for k in OK for d in k["deals"] if not set(d["flags"]) & BAD], key=lambda t: t[0])
    c = []
    for r, (v, k, d) in zip(ranks([t[0] for t in drows]), drows):
        off = f'<span class="flag offer">{e(u["offer"])}</span>' if d["offer"] else ""
        c.append(f'<tr{" class=best" if r == 1 else ""}><td class="n rk">{r}</td><th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a>'
                 f'<small>{e(tx(d["label"], L))}</small></th><td class="n">{money(d["price"], L)} / {d["mins"]} min</td><td class="n hl">{pm_txt(v, L)}</td>'
                 f'<td>{off}{e(tx(d["cond"], L)) if d["cond"] else ""}</td><td>{link(d["src"], u["source"])}</td></tr>')
    tc = table([(u["th_rank"], 1), (u["th_product"], 0), (u["th_price"], 1), ("€/min", 1), (u["th_cond"], 0), (u["th_source"], 0)], c)
    lrows = []
    for i, (kid, dur, price, cond, src) in enumerate(u["long_rows"]):
        lrows.append(f'<tr{" class=best" if i == 0 else ""}><td class="n rk">{i + 1}</td><th scope="row"><a href="#{pid("k-" + kid)}">{e(BYID[kid]["name"])}</a></th>'
                     f'<td class="n hl">{e(dur)}</td><td class="n">{e(price)}</td><td>{e(cond)}</td><td>{link(src, u["source"])}</td></tr>')
    td = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_duration"], 1), (u["th_price"], 1), (u["th_cond"], 0), (u["th_source"], 0)], lrows)
    tabs = [("min", u["tab_min"], u["r_min_intro"], tb), ("deal", u["tab_deal"], u["r_deal_intro"], tc), ("long", u["tab_long"], u["r_long_intro"], td)]
    btns = "".join(f'<button type="button" role="tab" id="{L}-tab-{t}" aria-controls="{L}-panel-{t}" aria-selected="{"true" if i == 0 else "false"}">{e(n)}</button>'
                   for i, (t, n, _, _) in enumerate(tabs))
    panels = "".join(f'<div role="tabpanel" id="{L}-panel-{t}" aria-labelledby="{L}-tab-{t}"{"" if i == 0 else " hidden"}><p class="lead">{e(it)}</p>{body}</div>'
                     for i, (t, n, it, body) in enumerate(tabs))
    keys = "".join(f'<div><h3>{e(t)}</h3><p>{e(p)}</p></div>' for t, p in u["keys"])
    return f'''
<section class="sec alt" id="{pid("rankings")}">
  <div class="wrap">
    <h2>{e(u["rank_title"])}</h2>
    <p class="lead">{e(u["rank_intro2"])}</p>
    <div class="tabs" role="tablist">{btns}</div>
    {panels}
    <h2 class="h2-sm">{e(u["keys_title"])}</h2>
    <div class="keys">{keys}</div>
  </div>
</section>'''


def faq(L, pid):
    u = UI[L]
    items = "".join(f'<details class="qa"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in u["faq"])
    ps = "".join(f"<li>{e(p)}</li>" for p in list(u["method"]) + [u["phases_method"], u["rating_method"]])
    fl = "".join(f'<li>{flag_txt([f], L)} {e(u["flag_long"][f])}</li>' for f in u["flag"])
    return f'''
<section class="sec" id="{pid("faq")}">
  <div class="wrap faq-grid">
    <div><h2>{e(u["faq_title"])}</h2>{items}</div>
    <div class="method" id="{pid("metodo")}"><h2 class="h2-sm">{e(u["method_title"])}</h2><ol>{ps}</ol>
      <h3>{e(u["flags_title"])}</h3><ul class="flaglist">{fl}</ul></div>
  </div>
</section>'''


def area_qa(L, a):
    u = UI[L]
    name, h1in, in_ = AREA_TXT[a][L]
    ks, unc, best_s, minp, best_r = area_stats(a)
    qa = [(u["q_count"].format(in_=in_), u["a_count"].format(n=len(ks), names=", ".join(f'{k["name"]} ({k["town"]})' for k in ks)))]
    if best_s:
        v, k, s = best_s
        qa.append((u["q_cheap"].format(in_=in_), u["a_cheap"].format(k=k["name"], town=k["town"], price=money(s["price"], L),
                                                                     mins=s["mins"], pm=pm_txt(v, L))))
    if best_r:
        price, k, r = best_r
        ppl = u["a_race_people"].format(n=r["minp"]) if r["minp"] else ""
        qa.append((u["q_race"].format(in_=in_), u["a_race"].format(race=tx(r["name"], L), k=k["name"], price=money(price, L),
                                                                   struct=struct_txt(r["struct"], L), people=ppl)))
    return qa


def area_faq(L, pid, a):
    u = UI[L]
    items = "".join(f'<details class="qa" open><summary>{e(q)}</summary><p>{e(x)}</p></details>' for q, x in area_qa(L, a))
    return f'''
<section class="sec alt" id="{pid("faq")}">
  <div class="wrap"><h2>{e(u["faq_title"])}</h2>{items}</div>
</section>'''


def footer(L):
    u = UI[L]
    return f'''
<footer class="foot"><div class="wrap foot-in">
  <p><b>{e(BRAND)}</b> · {e(u["footer_updated"])}: <time datetime="{CHECKED}">{e(DATE_TXT[L])}</time></p>
  <p>{e(u["footer_disclaimer"])}</p>
  <p>{link(REPO, u["footer_repo"], "web")}</p>
</div></footer>'''


def page_body(L, mode):
    pid = (lambda x: x) if mode == "site" else (lambda x: f"{L}-{x}")
    if CTX["area"]:
        return (header(L, mode, pid) + "<main>" + intro(L, pid) + directory(L, pid) + area_faq(L, pid, CTX["area"])
                + "</main>" + footer(L))
    return (header(L, mode, pid) + "<main>" + intro(L, pid) + directory(L, pid) + rankings(L, pid) + faq(L, pid)
            + "</main>" + footer(L))


def set_ctx(L, area=None, mode="site"):
    CTX.update(area=area, mode=mode, rel=rel(L, area) if mode == "site" else "")
    CTX["home"] = (BASE + PATHS[L]) if mode == "artifact" else ((CTX["rel"] + PATHS[L]) or "./")


def seo_txt(L):
    """(url, título, descripción) de la página actual."""
    u = UI[L]
    a = CTX["area"]
    if not a:
        return BASE + PATHS[L], u["seo_title"], u["seo_desc"]
    name, h1in, in_ = AREA_TXT[a][L]
    ks, unc, best_s, minp, best_r = area_stats(a)
    race = u["area_desc_race"].format(r=money(best_r[0], L)) if best_r else ""
    desc = u["area_desc1" if len(ks) == 1 else "area_desc"].format(n=len(ks), in_=in_, p=money(minp, L), race=race)
    return BASE + page_path(L, a), u["area_title"].format(h1in=h1in), desc


# ------------------------------------------------------------------ SEO
def jsonld(L):
    u = UI[L]
    url, title, desc = seo_txt(L)
    a = CTX["area"]
    items = []
    for i, k in enumerate([k for k in OK if not a or k["id"] in AREA_IDS[a]], 1):
        _, la, lo, _ = geo(k)
        item = {"@type": "SportsActivityLocation", "name": k["name"],
                "geo": {"@type": "GeoCoordinates", "latitude": la, "longitude": lo},
                "address": {"@type": "PostalAddress", "addressLocality": k["town"],
                            "addressRegion": u["prov"][k["prov"]], "addressCountry": "ES"}}
        if k.get("web"):
            item["url"] = k["web"]
        items.append({"@type": "ListItem", "position": i, "item": item})
    qa = area_qa(L, a) if a else u["faq"]
    page = {"@type": "WebPage", "@id": url, "url": url, "name": title, "description": desc,
            "inLanguage": L, "datePublished": CHECKED, "dateModified": CHECKED,
            "isPartOf": {"@type": "WebSite", "name": BRAND, "url": BASE}}
    graph = [page,
             {"@type": "ItemList", "name": u["area_h1"].format(h1in=AREA_TXT[a][L][1]) if a else u["h1"],
              "numberOfItems": len(items), "itemListElement": items},
             {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": x}}
                                                 for q, x in qa]}]
    if a:
        page["breadcrumb"] = {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": u["crumb_home"], "item": BASE + PATHS[L]},
            {"@type": "ListItem", "position": 2, "name": AREA_TXT[a][L][0], "item": url}]}
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def head(L):
    u = UI[L]
    url, title, desc = seo_txt(L)
    a = CTX["area"]
    alts = "".join(f'<link rel="alternate" hreflang="{x}" href="{BASE + page_path(x, a)}">' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE + page_path("es", a)}">'
    og_alt = "".join(f'<meta property="og:locale:alternate" content="{LOCALE[x]}">' for x in LANGS if x != L)
    img = f"{BASE}assets/og-{L}.png"
    pre = CTX["rel"]
    gsv = f'<meta name="google-site-verification" content="{e(GOOGLE_VERIFY)}">\n' if GOOGLE_VERIFY else ''
    return f'''<!doctype html>
<html lang="{L}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large">
{gsv}<link rel="canonical" href="{url}">
{alts}
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(title if a else u["og_title"])}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{LOCALE[L]}">
{og_alt}
<meta property="og:site_name" content="{BRAND}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title if a else u["og_title"])}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121212" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<script type="application/ld+json">{jsonld(L)}</script>
<style>{CSS}</style>
</head>
<body>
'''


CSS = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
JS = (Path(__file__).parent / "app.js").read_text(encoding="utf-8")


def build_site():
    pages = [None] + list(AREA_DEF)
    for a in pages:
        for L in LANGS:
            set_ctx(L, a)
            out = ROOT / page_path(L, a) / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(head(L) + page_body(L, "site") + f"<script>{JS}</script>\n</body>\n</html>\n", encoding="utf-8")
    urls = ""
    for a in pages:
        alt = "".join(f'<xhtml:link rel="alternate" hreflang="{x}" href="{BASE + page_path(x, a)}"/>' for x in LANGS)
        urls += "".join(f"<url><loc>{BASE + page_path(L, a)}</loc><lastmod>{CHECKED}</lastmod>{alt}</url>" for L in LANGS)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        f'xmlns:xhtml="http://www.w3.org/1999/xhtml">{urls}</urlset>\n', encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")


def build_artifact(path):
    body = "".join(set_ctx(L, None, "artifact") or f'<div class="lang-view" data-lang="{L}" lang="{L}"{"" if L == "es" else " hidden"}>{page_body(L, "artifact")}</div>'
                   for L in LANGS)
    doc = (f'<title>Kartings de Cataluña</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
           f'<link rel="stylesheet" href="{FONTS}">\n<style>{CSS}</style>\n{body}\n<script>{JS}</script>\n')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    build_site()
    if "--artifact" in sys.argv:
        build_artifact(sys.argv[sys.argv.index("--artifact") + 1])
    print("ok")
