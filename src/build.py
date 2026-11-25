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
from data import KARTINGS, EXCLUDED, LEAGUE, CHECKED, GEO, ZONES, BARCELONA  # noqa: E402
from i18n import UI, LANGS, LOCALE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Cambia BASE cuando el dominio propio (p. ej. https://karting.cat/) apunte a GitHub Pages.
BASE = "https://pablomariaarranzpou.github.io/kartings-catalunya/"
BRAND = "karting.cat"
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


# ------------------------------------------------------------------ cabecera
def header(L, mode, pid):
    u = UI[L]
    langs = []
    for x in LANGS:
        if mode == "artifact":
            href = f"#{x}"
        else:
            href = ("../" if L != "es" else "") + PATHS[x] or "./"
            href = href or "./"
        cur = ' aria-current="page"' if x == L else ""
        langs.append(f'<a href="{href}" hreflang="{x}" lang="{x}"{cur}>{x.upper()}</a>')
    nav = "".join(f'<a href="#{pid(a)}">{e(u[b])}</a>' for a, b in
                  [("buscador", "nav_finder"), ("circuitos", "nav_dir"), ("rankings", "nav_rank"), ("faq", "nav_faq")])
    name, tld = BRAND.split(".", 1)
    return f'''
<header class="site-h"><div class="wrap site-h-in">
  <a class="brand" href="#{pid("top")}">{e(name)}<span>.{e(tld)}</span></a>
  <nav class="site-nav" aria-label="{e(u["nav_finder"])}">{nav}</nav>
  <div class="langs">{"".join(langs)}</div>
</div></header>'''


# ------------------------------------------------------------------ buscador
def session_row(k, L, pid):
    u = UI[L]
    z, la, lo, dkm = geo(k)
    s = (ok_sessions(k) or [s for s in k["sessions"] if not set(s["flags"]) & BAD] or [None])[0]
    if s is None:
        return ""
    v = permin(s["price"], s["mins"])
    dv, d = best_deal(k)
    sub = f'{s["mins"]} min · {pm_txt(v, L)}' if s["mins"] else u["dur_unknown"]
    pack = ""
    if dv is not None and (v is None or dv < v):
        pack = f'<span class="r-pack">{e(u["with_pack"].format(v=pm_txt(dv, L)))}</span>'
    lab = " · ".join(x for x in [tx(s["label"], L) if s["label"] else "", tx(s["cond"], L) if s["cond"] else ""] if x)
    return row_html(k, L, pid, "session", dict(price=s["price"], eurmin=v if v is not None else ""),
                    big=money(s["price"], L), sub=sub, extra=pack, line=lab, flags=[f for f in k["flags"] if f in ("season", "snippet", "unconfirmed")] + list(s["flags"]),
                    src=s["src"], dkm=dkm, zone=z, la=la, lo=lo)


def race_rows(k, L, pid):
    u = UI[L]
    z, la, lo, dkm = geo(k)
    out = []
    for r in k["races"]:
        if not r["quali"] or r["price"] is None or set(r["flags"]) & BAD:
            continue
        minp = r["minp"]
        if isinstance(minp, str):  # p. ej. "2–5": nos quedamos con el mayor por prudencia
            minp = int(minp.split("–")[-1])
        line = " · ".join(x for x in [tx(r["name"], L), struct_txt(r["struct"], L)] if x)
        cond = " · ".join(x for x in [people_txt(r, L), tx(r["cond"], L) if r["cond"] else "",
                                      tx(r["price_note"], L) if r["price_note"] else ""] if x)
        out.append(row_html(k, L, pid, "race", dict(price=r["price"], minp=minp or "", maxp=r["maxp"] or ""),
                            big=money(r["price"], L), sub={"es": "por persona", "ca": "per persona", "en": "per person"}[L], extra='<span class="r-total"></span>',
                            line=line, cond=cond, flags=[f for f in k["flags"] if f in ("season", "snippet", "unconfirmed")] + list(r["flags"]), src=r["src"],
                            dkm=dkm, zone=z, la=la, lo=lo, hidden=True))
    return "".join(out)


def row_html(k, L, pid, mode, data, big, sub, extra, line, flags, src, dkm, zone, la, lo, cond="", hidden=False):
    u = UI[L]
    attrs = "".join(f' data-{a}="{v}"' for a, v in data.items())
    meta = " · ".join(x for x in [k["town"], u["type_short"][k["type"]] + (f' ({u["electric"]})' if k.get("electric") else ""),
                                   tx(k["kart"], L) if k.get("kart") else ""] if x)
    fl = flag_txt(sorted(set(flags)), L, skip=("noyear",))
    return f'''<li class="res" data-mode="{mode}" data-k="{k["id"]}" data-zone="{zone}" data-lat="{la}" data-lon="{lo}"{attrs}{" hidden" if hidden else ""}>
  <div class="r-main">
    <h3><a href="#{pid("k-" + k["id"])}">{e(k["name"])}</a></h3>
    <p class="r-meta">{e(meta)}</p>
    {f'<p class="r-line">{e(line)}</p>' if line else ""}
    {f'<p class="r-cond">{e(cond)}</p>' if cond else ""}
    {f'<p class="r-flags">{fl}</p>' if fl else ""}
  </div>
  <div class="r-price"><span class="badge" hidden></span><strong>{e(big)}</strong><span class="r-sub">{e(sub)}</span>{extra}</div>
  <div class="r-foot"><span class="dist">{e(u["from_bcn"].format(km=dkm))}</span>{link(src, u["see_price"])}</div>
</li>'''


def finder(L, pid):
    u = UI[L]
    rows = "".join(session_row(k, L, pid) for k in OK) + "".join(race_rows(k, L, pid) for k in OK)
    zones = f'<option value="*">{e(u["zone_all"])}</option>' + "".join(
        f'<option value="{z}">{e(u["zones"][z])}</option>' for z in ZONES)
    cfg = dict(lang={"es": "es-ES", "ca": "ca-ES", "en": "en-GB"}[L], count=u["count"], count1=u["count1"],
               total=u["total_for"], from_bcn=u["from_bcn"], from_you=u["from_you"], near_ok=u["near_ok"],
               near_fail=u["near_fail"], badge={"price": u["best_price"], "eurmin": u["best_eurmin"], "dist": u["best_dist"]})
    n_session = sum(1 for k in OK if session_row(k, L, pid))
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
      <label class="ctl"><span>{e(u["sort_label"])}</span><select id="{L}-sort" data-ctl="sort">
        <option value="eurmin" selected>{e(u["sort_eurmin"])}</option><option value="price">{e(u["sort_price"])}</option><option value="dist">{e(u["sort_dist"])}</option></select></label>
      <button type="button" class="near" data-near>{e(u["near_me"])}</button>
    </div>
  </form>
  <div class="res-head"><p class="count" aria-live="polite">{e(u["count"].format(n=n_session))}</p><p class="checked">{e(u["checked_note"])}</p></div>
  <p class="geo-msg" hidden></p>
  <ol class="results">{rows}</ol>
  <p class="empty" hidden>{e(u["none"])}</p>
</section>'''


def intro(L, pid):
    u = UI[L]
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
            small = " · ".join(x for x in [struct_txt(r["struct"], L), people_txt(r, L) if r["minp"] else "",
                                           tx(r["cond"], L) if r["cond"] else "", tx(r["price_note"], L) if r["price_note"] else ""] if x)
            val = money(r["price"], L) + (u["per_person"] if r["price"] is not None else "")
            items.append(li(tx(r["name"], L), small, val, r["flags"], r["src"]))
        parts.append(f'<h4>{e(u["lbl_races"])}</h4><ul class="lines">{"".join(items)}</ul>')
    notes = "".join(f"<li>{e(n)}</li>" for n in tx(k["notes"], L))
    xsrc = f'<p class="xsrc">{link(k["src"], u["source"])}</p>' if k.get("src") else ""
    unc = f'<span class="flag">{e(u["uncertain_tag"])}</span>' if k["status"] != "ok" else ""
    return f'''
<details class="k{" unc" if k["status"] != "ok" else ""}" id="{pid("k-" + k["id"])}">
  <summary><span class="k-name">{e(k["name"])}</span><span class="k-meta">{e(k["town"])} · {e(typ)} · {e(u["from_bcn"].format(km=dkm))}</span><span class="k-from">{e(frm)}</span></summary>
  <div class="k-body">
    <div class="k-flags">{unc}{flag_txt(k["flags"], L)}</div>
    {f'<dl class="meta">{dl}</dl>' if dl else ""}
    <div class="k-cols"><div>{"".join(parts)}</div><div><h4>{e(u["lbl_notes"])}</h4><ul class="notes">{notes}</ul>{xsrc}</div></div>
  </div>
</details>'''


def directory(L, pid):
    u = UI[L]
    groups = []
    for z in ZONES:
        ks = sorted([k for k in KARTINGS if GEO[k["id"]][0] == z], key=lambda k: (k["status"] != "ok", k["name"]))
        groups.append(f'<div class="zone"><h3>{e(u["zones"][z])}</h3>{"".join(entry(k, L, pid) for k in ks)}</div>')
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
                 f'<td class="n hl">{pm_txt(v, L)}</td><td>{flag_txt(s["flags"], L)}{link(s["src"], u["source"])}</td></tr>')
    tb = table([(u["th_rank"], 1), (u["th_karting"], 0), (u["th_price"], 1), (u["th_minutes"], 1), ("€/min", 1), (u["th_source"], 0)], b)
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
    ps = "".join(f"<li>{e(p)}</li>" for p in u["method"])
    fl = "".join(f'<li>{flag_txt([f], L)} {e(u["flag_long"][f])}</li>' for f in u["flag"])
    return f'''
<section class="sec" id="{pid("faq")}">
  <div class="wrap faq-grid">
    <div><h2>{e(u["faq_title"])}</h2>{items}</div>
    <div class="method" id="{pid("metodo")}"><h2 class="h2-sm">{e(u["method_title"])}</h2><ol>{ps}</ol>
      <h3>{e(u["flags_title"])}</h3><ul class="flaglist">{fl}</ul></div>
  </div>
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
    return (header(L, mode, pid) + "<main>" + intro(L, pid) + directory(L, pid) + rankings(L, pid) + faq(L, pid)
            + "</main>" + footer(L))


# ------------------------------------------------------------------ SEO
def jsonld(L):
    u = UI[L]
    url = BASE + PATHS[L]
    items = []
    for i, k in enumerate(OK, 1):
        _, la, lo, _ = geo(k)
        item = {"@type": "SportsActivityLocation", "name": k["name"],
                "address": {"@type": "PostalAddress", "addressLocality": k["town"],
                            "addressRegion": u["prov"][k["prov"]], "addressCountry": "ES"}}
        if k.get("web"):
            item["url"] = k["web"]
        items.append({"@type": "ListItem", "position": i, "item": item})
    graph = [
        {"@type": "WebPage", "@id": url, "url": url, "name": u["seo_title"], "description": u["seo_desc"],
         "inLanguage": L, "datePublished": CHECKED, "dateModified": CHECKED,
         "isPartOf": {"@type": "WebSite", "name": BRAND, "url": BASE}},
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
<meta property="og:site_name" content="{BRAND}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(u["og_title"])}">
<meta name="twitter:description" content="{e(u["seo_desc"])}">
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
    for L in LANGS:
        out = ROOT / PATHS[L] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(head(L) + page_body(L, "site") + f"<script>{JS}</script>\n</body>\n</html>\n", encoding="utf-8")
    alt = "".join(f'<xhtml:link rel="alternate" hreflang="{x}" href="{BASE + PATHS[x]}"/>' for x in LANGS)
    urls = "".join(f"<url><loc>{BASE + PATHS[L]}</loc><lastmod>{CHECKED}</lastmod>{alt}</url>" for L in LANGS)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        f'xmlns:xhtml="http://www.w3.org/1999/xhtml">{urls}</urlset>\n', encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")


def build_artifact(path):
    body = "".join(f'<div class="lang-view" data-lang="{L}" lang="{L}"{"" if L == "es" else " hidden"}>{page_body(L, "artifact")}</div>'
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
