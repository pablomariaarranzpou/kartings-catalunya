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
