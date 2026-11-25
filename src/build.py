"""Genera la web estática (ES/CA/EN) y la versión artifact.

Uso:  python src/build.py [--artifact RUTA]
Salida: index.html, ca/index.html, en/index.html, sitemap.xml, robots.txt
"""
import html
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data import KARTINGS, EXCLUDED, LEAGUE, CHECKED  # noqa: E402
from i18n import UI, LANGS, LOCALE, LANG_NAME  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://pablomariaarranzpou.github.io/kartings-catalunya/"
REPO = "https://github.com/pablomariaarranzpou/kartings-catalunya"
PATHS = {"es": "", "ca": "ca/", "en": "en/"}
DATE_TXT = {"es": "25 de noviembre de 2026", "ca": "25 de novembre de 2026", "en": "25 November 2026"}
PROV_ORDER = ["B", "T", "G", "L"]
BAD = {"old", "third"}

e = html.escape


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
    parts = []
    for kind, val in struct:
        if kind == "raw":
            parts.append(tx(val, L))
        else:
            parts.append(UI[L]["struct"][kind].format(n=val))
    return " + ".join(parts)


def people_txt(r, L):
    u = UI[L]
    if r["minp"] and r["maxp"]:
        return u["min_people_range"].format(a=r["minp"], b=r["maxp"])
    if r["minp"]:
        return u["min_people"].format(n=r["minp"])
    return u["not_published"]


def link(url, label, cls="src"):
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="noopener nofollow">{e(label)}</a>'


def flag_pills(flags, L):
    u = UI[L]
    out = []
    for f in flags:
        tone = "ok" if f == "iva" else ("info" if f in ("noyear", "season") else "warn")
        out.append(f'<span class="flag flag-{tone}" title="{e(u["flag_long"][f])}">{e(u["flag"][f])}</span>')
    return "".join(out)


def ok_sessions(k):
    return [s for s in k["sessions"] if s["mins"] and not (set(s["flags"]) & BAD)]


def all_offers(k):
    rows = []
    for s in k["sessions"]:
        if s["mins"]:
            rows.append((permin(s["price"], s["mins"]), s))
    for d in k["deals"]:
        rows.append((permin(d["price"], d["mins"]), d))
    return rows


def best_of(k, official_only=True):
    vals = [v for v, x in all_offers(k) if not (official_only and set(x["flags"]) & BAD)]
    return min(vals) if vals else None


def cheapest_race(k):
    rs = [r for r in k["races"] if r["quali"] and r["price"] is not None and not (set(r["flags"]) & BAD)]
    return min(rs, key=lambda r: r["price"]) if rs else None


def ranks(values):
    return [1 + sum(1 for w in values if w < v) for v in values]


OK = [k for k in KARTINGS if k["status"] == "ok"]
BYID = {k["id"]: k for k in KARTINGS}


# ------------------------------------------------------------------ secciones
def hero(L, pid):
    u = UI[L]
    s_rows = [(permin(s["price"], s["mins"]), k, s) for k in OK for s in ok_sessions(k)]
    v, k1, s1 = min(s_rows, key=lambda t: (t[0], t[2]["price"]))
    d_rows = [(v2, k, x) for k in OK for v2, x in all_offers(k) if not set(x["flags"]) & BAD]
    dv, k2, d2 = min(d_rows, key=lambda t: t[0])
    r_rows = [(k, cheapest_race(k)) for k in OK if cheapest_race(k)]
    k3, r3 = min(r_rows, key=lambda t: t[1]["price"])
    g_rows = [(r["price"] * r["minp"], k, r) for k in OK for r in k["races"]
              if r["quali"] and r["price"] and isinstance(r["minp"], int) and not set(r["flags"]) & BAD]
    gv, k4, r4 = min(g_rows, key=lambda t: t[0])
    tower = [
        ("P1", u["t_min"], pm_txt(v, L), f'{k1["name"]} · {money(s1["price"], L)} / {s1["mins"]} min', k1),
        ("P1", u["t_pack"], pm_txt(dv, L), f'{k2["name"]} · {tx(d2["label"], L) if "label" in d2 and d2["label"] else ""}', k2),
        ("P1", u["t_race"], money(r3["price"], L), f'{k3["name"]} · {tx(r3["name"], L)} · {people_txt(r3, L)}', k3),
        ("P1", u["t_group"], money(gv, L), f'{k4["name"]} · {r4["minp"]} × {money(r4["price"], L)}', k4),
        ("P1", u["t_long"], "18 min", "Karting L'Escala", BYID["lescala"]),
    ]
    rows = "".join(
        f'<li><span class="pos">{p}</span><span class="tl">{e(lbl)}<a href="#{pid("k-" + k["id"])}">{e(sub)}</a></span>'
        f'<span class="tv">{e(val)}</span></li>'
        for p, lbl, val, sub, k in tower)
    n_all = len(KARTINGS) + len(EXCLUDED)
    return f'''
<header class="hero">
  <div class="kerb" aria-hidden="true"></div>
  <div class="wrap hero-in">
    <div class="hero-copy">
      <p class="eyebrow">{e(u["eyebrow"])} · <time datetime="{CHECKED}">{e(u["checked"])} {e(DATE_TXT[L])}</time></p>
      <h1>{e(u["h1"])}</h1>
      <p class="lede">{e(u["lede"].format(n_all=n_all, n_ok=len(OK)))}</p>
      <nav class="jump" aria-label="{e(u["nav_compare"])}">
        <a href="#{pid("comparador")}">{e(u["nav_compare"])}</a>
        <a href="#{pid("rankings")}">{e(u["nav_rank"])}</a>
        <a href="#{pid("fichas")}">{e(u["nav_cards"])}</a>
        <a href="#{pid("faq")}">{e(u["nav_faq"])}</a>
        <a href="#{pid("metodo")}">{e(u["nav_method"])}</a>
      </nav>
    </div>
    <aside class="tower" aria-label="{e(u["tower_title"])}">
      <div class="tower-head"><span>{e(u["tower_title"])}</span><span class="live">{e(u["tower_sub"])}</span></div>
      <ol>{rows}</ol>
    </aside>
  </div>
</header>'''


def lang_switch(L, mode):
    items = []
    for x in LANGS:
        href = f"#{x}" if mode == "artifact" else ("../" * (L != "es")) + PATHS[x]
        if mode == "site" and href == "":
            href = "./"
        cur = ' aria-current="true"' if x == L else ""
        items.append(f'<a href="{href}" hreflang="{x}" lang="{x}"{cur}>{x.upper()}</a>')
    return f'<div class="langs" role="navigation" aria-label="Idioma / Language">{"".join(items)}</div>'


def topbar(L, mode):
    return f'''<div class="topbar"><div class="wrap topbar-in"><span class="brand">Kartings<b>CAT</b></span>{lang_switch(L, mode)}</div></div>'''


def comparator(L, pid):
    u = UI[L]
    rows = []
    for k in sorted(KARTINGS, key=lambda k: (PROV_ORDER.index(k["prov"]), k["status"] != "ok", k["name"])):
        s = k["sessions"][0] if k["sessions"] else None
        sess = f'{money(s["price"], L)} / {s["mins"]} min' if s and s["mins"] else (money(s["price"], L) if s else u["no_data"])
        ev = best_of(k, official_only=True) if k["status"] == "ok" else None
        emin = min([permin(x["price"], x["mins"]) for x in ok_sessions(k)], default=None) if k["status"] == "ok" else None
        if k["status"] != "ok" and s and s["mins"]:
            emin_disp = pm_txt(permin(s["price"], s["mins"]), L) + "*"
        else:
            emin_disp = pm_txt(emin, L)
        r = cheapest_race(k)
        race = f'{money(r["price"], L)} · {people_txt(r, L)}' if r else u["no_data"]
        typ = u["type"][k["type"]] + (f' · {u["electric"]}' if k.get("electric") else "")
        flags = list(k["flags"])
        rows.append(
            f'<tr data-prov="{k["prov"]}" data-type="{k["type"]}" data-el="{1 if k.get("electric") else 0}" class="{"" if k["status"] == "ok" else "unc"}">'
            f'<th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a><small>{e(k["town"])}</small></th>'
            f'<td data-v="{PROV_ORDER.index(k["prov"])}">{e(u["prov"][k["prov"]])}</td>'
            f'<td>{e(typ)}</td>'
            f'<td class="n" data-v="{s["price"] if s else ""}">{e(sess)}</td>'
            f'<td class="n" data-v="{emin if emin is not None else ""}">{e(emin_disp)}</td>'
            f'<td class="n" data-v="{ev if ev is not None else ""}">{e(pm_txt(ev, L))}</td>'
            f'<td class="n" data-v="{r["price"] if r else ""}">{e(race)}</td>'
            f'<td>{flag_pills(flags, L)}</td></tr>')
    heads = [("th_karting", "t"), ("th_prov", "n"), ("th_type", "t"), ("th_session", "n"), ("th_eurmin", "n"),
             ("th_best", "n"), ("th_race", "n"), ("th_status", None)]
    th = "".join(
        f'<th scope="col">{"<button type=button data-sort=" + str(i) + " data-kind=" + kind + ">" + e(u[h]) + "</button>" if kind else e(u[h])}</th>'
        for i, (h, kind) in enumerate(heads))
    chips = (f'<button type="button" class="chip" data-f="prov" data-val="*" aria-pressed="true">{e(u["f_all"])}</button>'
             + "".join(f'<button type="button" class="chip" data-f="prov" data-val="{p}" aria-pressed="false">{e(u["prov"][p])}</button>' for p in PROV_ORDER)
             + '<span class="sep" aria-hidden="true"></span>'
             + f'<button type="button" class="chip" data-f="type" data-val="indoor" aria-pressed="false">{e(u["f_indoor"])}</button>'
             + f'<button type="button" class="chip" data-f="type" data-val="outdoor" aria-pressed="false">{e(u["f_outdoor"])}</button>'
             + f'<button type="button" class="chip" data-f="type" data-val="el" aria-pressed="false">{e(u["f_electric"])}</button>')
    note = {"es": "* Dato antiguo o de terceros: fuera de los rankings.",
            "ca": "* Dada antiga o de tercers: fora dels rànquings.",
            "en": "* Old or third-party figure: not ranked."}[L]
    return f'''
<section id="{pid("comparador")}" class="sec">
  <div class="wrap">
    <h2>{e(u["compare_title"])}</h2>
    <p class="intro">{e(u["compare_intro"])}</p>
    <div class="chips" data-scope="cmp">{chips}</div>
    <div class="scroll"><table class="tbl cmp" data-sortable>
      <thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
    <p class="foot-note">{e(note)}</p>
  </div>
</section>'''


def table(headers, rows, cls=""):
    th = "".join(f'<th scope="col"{" class=n" if n else ""}>{e(h)}</th>' for h, n in headers)
    return f'<div class="scroll"><table class="tbl {cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def rankings(L, pid):
    u = UI[L]
    # (b) €/min tanda suelta
    srows = sorted([(permin(s["price"], s["mins"]), k, s) for k in OK for s in ok_sessions(k)],
                   key=lambda t: (t[0], t[2]["price"]))
    rk = ranks([t[0] for t in srows])
    b = []
    for r, (v, k, s) in zip(rk, srows):
        prod = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
        b.append(f'<tr{" class=best" if r == 1 else ""}><td class="n rk">{r}</td>'
                 f'<th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a><small>{e(prod)}</small></th>'
                 f'<td class="n">{money(s["price"], L)}</td><td class="n">{s["mins"]} min</td>'
                 f'<td class="n pmv">{pm_txt(v, L)}</td><td>{flag_pills(s["flags"], L)}{link(s["src"], u["source"])}</td></tr>')
    tb = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_price"], 1), (u["th_minutes"], 1), ("€/min", 1), (u["th_source"], 0)], b)
    # (c) packs y ofertas
    drows = sorted([(permin(d["price"], d["mins"]), k, d) for k in OK for d in k["deals"] if not set(d["flags"]) & BAD],
                   key=lambda t: t[0])
    rk = ranks([t[0] for t in drows])
    c = []
    for r, (v, k, d) in zip(rk, drows):
        offer = f'<span class="flag flag-offer">{e(u["offer"])}</span>' if d["offer"] else ""
        c.append(f'<tr{" class=best" if r == 1 else ""}><td class="n rk">{r}</td>'
                 f'<th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a><small>{e(tx(d["label"], L))}</small></th>'
                 f'<td class="n">{money(d["price"], L)} / {d["mins"]} min</td><td class="n pmv">{pm_txt(v, L)}</td>'
                 f'<td>{offer}{e(tx(d["cond"], L)) if d["cond"] else ""}</td><td>{link(d["src"], u["source"])}</td></tr>')
    tc = table([(u["th_rank"], 1), (u["th_product"], 0), (u["th_price"], 1), ("€/min", 1), (u["th_cond"], 0), (u["th_source"], 0)], c)
    # (e) carreras con quali
    rrows = sorted([(k, r) for k in OK for r in k["races"] if r["quali"] and r["price"] is not None and not set(r["flags"]) & BAD],
                   key=lambda t: t[1]["price"])
    rk = ranks([t[1]["price"] for t in rrows])
    g = []
    for r_, (k, r) in zip(rk, rrows):
        outlay = money(r["price"] * r["minp"], L) if isinstance(r["minp"], int) else u["no_data"]
        extra = " · ".join(x for x in [tx(r["cond"], L) if r["cond"] else "", tx(r["price_note"], L) if r["price_note"] else ""] if x)
        g.append(f'<tr{" class=best" if r_ == 1 else ""}><td class="n rk">{r_}</td>'
                 f'<th scope="row"><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a><small>{e(tx(r["name"], L))}</small></th>'
                 f'<td class="n pmv">{money(r["price"], L)}</td><td>{e(people_txt(r, L))}</td><td class="n">{outlay}</td>'
                 f'<td>{e(struct_txt(r["struct"], L)) or u["no_data"]}{("<small>" + e(extra) + "</small>") if extra else ""}</td>'
                 f'<td>{flag_pills(r["flags"], L)}{link(r["src"], u["source"])}</td></tr>')
    te = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_price"] + u["per_person"], 1), (u["th_people"], 0),
                (u["th_outlay"], 1), (u["th_struct"], 0), (u["th_source"], 0)], g)
    # (d) tandas largas
    lrows = []
    for i, (kid, dur, price, cond, src) in enumerate(u["long_rows"]):
        k = BYID[kid]
        lrows.append(f'<tr{" class=best" if i == 0 else ""}><td class="n rk">{i + 1}</td>'
                     f'<th scope="row"><a href="#{pid("k-" + kid)}">{e(k["name"])}</a></th>'
                     f'<td class="n pmv">{e(dur)}</td><td class="n">{e(price)}</td><td>{e(cond)}</td><td>{link(src, u["source"])}</td></tr>')
    td = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_duration"], 1), (u["th_price"], 1), (u["th_cond"], 0), (u["th_source"], 0)], lrows)

    def block(i, t, intro, body):
        return f'<div class="rank"><h3 id="{pid("rank-" + str(i))}">{e(t)}</h3><p class="intro">{e(intro)}</p>{body}</div>'

    return f'''
<section id="{pid("rankings")}" class="sec alt">
  <div class="wrap">
    <h2>{e(u["rank_title"])}</h2>
    <p class="intro">{e(u["rank_intro"])} <span class="legend"><span class="sw" aria-hidden="true"></span>{e(u["purple_legend"])}</span></p>
    {block(1, u["r_min_title"], u["r_min_intro"], tb)}
    {block(2, u["r_deal_title"], u["r_deal_intro"], tc)}
    {block(3, u["r_race_title"], u["r_race_intro"], te)}
    {block(4, u["r_long_title"], u["r_long_intro"], td)}
  </div>
</section>'''


def keys(L, pid):
    u = UI[L]
    items = "".join(f'<div class="key"><h3>{e(t)}</h3><p>{e(p)}</p></div>' for t, p in u["keys"])
    return f'''
<section class="sec" id="{pid("claves")}">
  <div class="wrap"><h2>{e(u["keys_title"])}</h2><div class="keys">{items}</div></div>
</section>'''


def card(k, L, pid):
    u = UI[L]
    typ = u["type"][k["type"]] + (f' · {u["electric"]}' if k.get("electric") else "")
    meta = []
    if k.get("track"):
        meta.append((u["lbl_track"], e(tx(k["track"], L))))
    if k.get("kart"):
        meta.append((u["lbl_kart"], e(tx(k["kart"], L))))
    webline = []
    if k.get("web"):
        webline.append(link(k["web"], k["web"].split("//")[1].split("/")[0].replace("www.", ""), "web"))
    if k.get("pdf"):
        webline.append(link(k["pdf"], u["pdf"], "web"))
    if webline:
        meta.append((u["official_web"], " · ".join(webline)))
    dl = "".join(f"<div><dt>{e(a)}</dt><dd>{b}</dd></div>" for a, b in meta)

    def li_session(s):
        lbl = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
        dur = f' / {s["mins"]} min' if s["mins"] else f' / {u["not_published"]}'
        pmv = f' <span class="pm">{pm_txt(permin(s["price"], s["mins"]), L)}</span>' if s["mins"] else ""
        return (f'<li><span class="what">{e(lbl) if lbl else "&nbsp;"}</span><span class="val">{money(s["price"], L)}{dur}{pmv}</span>'
                f'{flag_pills(s["flags"], L)}{link(s["src"], u["source"])}</li>')

    def li_deal(d):
        offer = f'<span class="flag flag-offer">{e(u["offer"])}</span>' if d["offer"] else ""
        cond = f'<small>{e(tx(d["cond"], L))}</small>' if d["cond"] else ""
        return (f'<li><span class="what">{e(tx(d["label"], L))}{cond}</span><span class="val">{money(d["price"], L)} / {d["mins"]} min '
                f'<span class="pm">{pm_txt(permin(d["price"], d["mins"]), L)}</span></span>{offer}{flag_pills(d["flags"], L)}{link(d["src"], u["source"])}</li>')

    def li_race(r):
        bits = [x for x in [struct_txt(r["struct"], L), people_txt(r, L) if r["minp"] else "",
                            tx(r["cond"], L) if r["cond"] else "", tx(r["price_note"], L) if r["price_note"] else ""] if x]
        return (f'<li><span class="what">{e(tx(r["name"], L))}<small>{e(" · ".join(bits))}</small></span>'
                f'<span class="val">{money(r["price"], L)}</span>{flag_pills(r["flags"], L)}{link(r["src"], u["source"])}</li>')

    parts = []
    if k["sessions"]:
        parts.append(f'<h4>{e(u["lbl_sessions"])}</h4><ul class="lines">{"".join(li_session(s) for s in k["sessions"])}</ul>')
    if k["deals"]:
        parts.append(f'<h4>{e(u["lbl_deals"])}</h4><ul class="lines">{"".join(li_deal(d) for d in k["deals"])}</ul>')
    if k["races"]:
        parts.append(f'<h4>{e(u["lbl_races"])}</h4><ul class="lines">{"".join(li_race(r) for r in k["races"])}</ul>')
    notes = "".join(f"<li>{e(n)}</li>" for n in tx(k["notes"], L))
    extra_src = f'<p class="xsrc">{link(k["src"], u["source"])}</p>' if k.get("src") else ""
    unc = f'<span class="flag flag-warn">{e(u["uncertain_tag"])}</span>' if k["status"] != "ok" else ""
    return f'''
<article class="card{" unc" if k["status"] != "ok" else ""}" id="{pid("k-" + k["id"])}" data-prov="{k["prov"]}" data-type="{k["type"]}" data-el="{1 if k.get("electric") else 0}">
  <header class="card-h">
    <span class="plate" title="{e(u["prov"][k["prov"]])}">{k["prov"]}</span>
    <div><h3>{e(k["name"])}</h3><p class="where">{e(k["town"])} · {e(k["comarca"])} · {e(typ)}</p></div>
  </header>
  <div class="flags">{unc}{flag_pills(k["flags"], L)}</div>
  {f'<dl class="meta">{dl}</dl>' if dl else ""}
  {"".join(parts)}
  <h4>{e(u["lbl_notes"])}</h4><ul class="notes">{notes}</ul>{extra_src}
</article>'''


def cards(L, pid):
    u = UI[L]
    groups = []
    for p in PROV_ORDER:
        ks = sorted([k for k in KARTINGS if k["prov"] == p], key=lambda k: (k["status"] != "ok", k["name"]))
        groups.append(f'<h3 class="prov-h" data-prov="{p}">{e(u["prov"][p])} <span>{len(ks)}</span></h3>'
                      f'<div class="cards">{"".join(card(k, L, pid) for k in ks)}</div>')
    exc = "".join(f'<li><b>{e(x["name"])}</b> ({e(x["town"])}): {e(tx(x["why"], L))} {link(x["src"], u["source"])}</li>' for x in EXCLUDED)
    return f'''
<section id="{pid("fichas")}" class="sec">
  <div class="wrap">
    <h2>{e(u["cards_title"])}</h2>
    <p class="intro">{e(u["cards_intro"])}</p>
    {"".join(groups)}
    <div class="aside-grid">
      <div class="box"><h3>{e(u["excluded_title"])}</h3><ul class="notes">{exc}</ul></div>
      <div class="box"><h3>{e(u["league_title"])}</h3><p>{e(u["league_text"])}</p><p>{link(LEAGUE["src"], LEAGUE["name"])}</p></div>
    </div>
  </div>
</section>'''


def faq(L, pid):
    u = UI[L]
    items = "".join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in u["faq"])
    return f'<section id="{pid("faq")}" class="sec alt"><div class="wrap narrow"><h2>{e(u["faq_title"])}</h2>{items}</div></section>'


def method(L, pid):
    u = UI[L]
    ps = "".join(f"<li>{e(p)}</li>" for p in u["method"])
    fl = "".join(f'<li>{flag_pills([f], L)} {e(u["flag_long"][f])}</li>' for f in u["flag"])
    return f'''
<section id="{pid("metodo")}" class="sec">
  <div class="wrap two">
    <div><h2>{e(u["method_title"])}</h2><ol class="method">{ps}</ol></div>
    <div><h2>{e(u["flags_title"])}</h2><ul class="flaglist">{fl}</ul></div>
  </div>
</section>'''


def footer(L):
    u = UI[L]
    return f'''
<footer class="foot">
  <div class="kerb" aria-hidden="true"></div>
  <div class="wrap foot-in">
    <p><b>{e(u["footer_updated"])}:</b> <time datetime="{CHECKED}">{e(DATE_TXT[L])}</time>. {e(u["checked_long"])}</p>
    <p>{e(u["footer_disclaimer"])}</p>
    <p>{link(REPO, u["footer_repo"], "web")}</p>
  </div>
</footer>'''


def page_body(L, mode):
    pid = (lambda x: x) if mode == "site" else (lambda x: f"{L}-{x}")
    return (topbar(L, mode) + hero(L, pid) + "<main>" + comparator(L, pid) + rankings(L, pid) + keys(L, pid)
            + cards(L, pid) + faq(L, pid) + method(L, pid) + "</main>" + footer(L))


# ------------------------------------------------------------------ SEO
def jsonld(L):
    u = UI[L]
    url = BASE + PATHS[L]
    items = []
    for i, k in enumerate([k for k in KARTINGS if k["status"] == "ok"], 1):
        item = {"@type": "SportsActivityLocation", "name": k["name"],
                "address": {"@type": "PostalAddress", "addressLocality": k["town"],
                            "addressRegion": u["prov"][k["prov"]], "addressCountry": "ES"}}
        if k.get("web"):
            item["url"] = k["web"]
        items.append({"@type": "ListItem", "position": i, "item": item})
    graph = [
        {"@type": "WebPage", "@id": url, "url": url, "name": u["seo_title"], "description": u["seo_desc"],
         "inLanguage": L, "datePublished": CHECKED, "dateModified": CHECKED,
         "about": {"@type": "Thing", "name": "Kart racing"}, "isPartOf": {"@type": "WebSite", "name": "Kartings CAT", "url": BASE}},
        {"@type": "ItemList", "name": u["h1"], "numberOfItems": len(items), "itemListElement": items},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                                            for q, a in u["faq"]]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def head(L):
    u = UI[L]
    url = BASE + PATHS[L]
    alts = "".join(f'<link rel="alternate" hreflang="{x}" href="{BASE + PATHS[x]}">' for x in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE}">'
    og_alt = "".join(f'<meta property="og:locale:alternate" content="{LOCALE[x]}">' for x in LANGS if x != L)
    img = f"{BASE}assets/og-{L}.png"
    pre = "../" if L != "es" else ""
    return f'''<!doctype html>
<html lang="{L}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(u["seo_title"])}</title>
<meta name="description" content="{e(u["seo_desc"])}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">
{alts}
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(u["og_title"])}">
<meta property="og:description" content="{e(u["seo_desc"])}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{LOCALE[L]}">
{og_alt}
<meta property="og:site_name" content="Kartings CAT">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(u["og_title"])}">
<meta name="twitter:description" content="{e(u["seo_desc"])}">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#d4261c">
<link rel="icon" href="{pre}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Barlow:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap">
<script type="application/ld+json">{jsonld(L)}</script>
<style>{CSS}</style>
</head>
<body>
'''


CSS = (Path(__file__).parent / "style.css").read_text(encoding="utf-8")
JS = (Path(__file__).parent / "app.js").read_text(encoding="utf-8")


def build_site():
    for L in LANGS:
        out = ROOT / PATHS[L] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(head(L) + page_body(L, "site") + f"<script>{JS}</script>\n</body>\n</html>\n", encoding="utf-8")
    alt = lambda: "".join(f'<xhtml:link rel="alternate" hreflang="{x}" href="{BASE + PATHS[x]}"/>' for x in LANGS)
    urls = "".join(f"<url><loc>{BASE + PATHS[L]}</loc><lastmod>{CHECKED}</lastmod>{alt()}</url>" for L in LANGS)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        f'xmlns:xhtml="http://www.w3.org/1999/xhtml">{urls}</urlset>\n', encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")


def build_artifact(path):
    body = "".join(f'<div class="lang-view" data-lang="{L}" lang="{L}"{"" if L == "es" else " hidden"}>{page_body(L, "artifact")}</div>'
                   for L in LANGS)
    doc = ('<title>Kartings de Cataluña</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Barlow:wght@400;500;600&family=JetBrains+Mono:wght@500;600&display=swap">\n'
           f"<style>{CSS}</style>\n{body}\n<script>{JS}</script>\n")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    build_site()
    if "--artifact" in sys.argv:
        build_artifact(sys.argv[sys.argv.index("--artifact") + 1])
    print("ok")
