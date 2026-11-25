# Kartings de Cataluña · precios 2026

Comparativa de precios de los kartings de alquiler de Cataluña (Barcelona, Girona, Tarragona y Lleida): tandas, € por minuto, bonos, ofertas y carreras con clasificación. Cada cifra enlaza a la web oficial de la que sale.

- Web: https://pablomariaarranzpou.github.io/kartings-catalunya/ (también en [català](https://pablomariaarranzpou.github.io/kartings-catalunya/ca/) e [English](https://pablomariaarranzpou.github.io/kartings-catalunya/en/))
- Datos consultados el **25 de noviembre de 2026**.

## Estructura

| Ruta | Qué es |
|---|---|
| `src/data.py` | Datos de cada karting con su fuente. Es el único sitio donde se tocan precios. |
| `src/i18n.py` | Textos de la web en español, catalán e inglés. |
| `src/build.py` | Genera `index.html`, `ca/`, `en/`, `sitemap.xml` y `robots.txt`. |
| `src/style.css`, `src/app.js` | Estilos y JS (ordenar tablas, filtros), incrustados en cada página. |
| `src/og.py` | Genera las imágenes para redes (`assets/og-*.png`) y el favicon. |

## Actualizar precios

1. Edita `src/data.py` (precio, minutos y URL de la fuente) y cambia `CHECKED` a la fecha de consulta.
2. Cambia también las fechas de `DATE_TXT` en `src/build.py` y de `src/og.py`.
3. Regenera y sube:

```bash
python src/og.py
python src/build.py
git add -A && git commit -m "Actualiza precios" && git push
```

## Aviso

Precios orientativos recopilados de fuentes públicas; pueden cambiar sin aviso. Esta web no tiene relación con ningún karting.

## Indexar en Google (dirección de GitHub Pages)

1. En https://search.google.com/search-console elige **Prefijo de la URL** y pon
   `https://pablomariaarranzpou.github.io/kartings-catalunya/` (la propiedad de dominio no sirve para github.io).
2. Método **Etiqueta HTML**: copia el valor de `content="..."` en `GOOGLE_VERIFY` de `src/build.py`,
   ejecuta `python src/build.py`, haz push y espera a que se publique Pages.
3. Pulsa **Verificar**. Después, en Sitemaps, envía `sitemap.xml`.
4. Opcional: Inspección de URLs → «Solicitar indexación» para la portada y `karting-barcelona/`.

Cuando pases a kartings.cat, GitHub redirige la dirección github.io al dominio y Google sigue esa redirección.

## Cuando compres kartings.cat

No lo actives antes: si el CNAME apunta a un dominio que aún no resuelve, la web deja de verse.

1. En el registrador del dominio (DNS de `kartings.cat`), crea estos registros:
   - `A` @ → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `AAAA` @ → `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`
   - `CNAME` www → `pablomariaarranzpou.github.io`
2. En `src/build.py` cambia `BASE` a `"https://kartings.cat/"`, ejecuta `python src/build.py`
   y crea el archivo `CNAME` en la raíz con una sola línea: `kartings.cat`.
3. Haz commit y push. En GitHub → Settings → Pages, comprueba que el dominio es `kartings.cat`
   y marca **Enforce HTTPS** cuando GitHub termine de emitir el certificado.
4. En Google Search Console añade la propiedad de dominio `kartings.cat` y envía
   `https://kartings.cat/sitemap.xml`.
