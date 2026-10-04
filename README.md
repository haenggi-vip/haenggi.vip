# haenggi.vip

Portfolio mit Apps und Engineering-Werkzeugen. Statische Website mit scrollgesteuertem Hintergrundvideo.

## Lokal starten

`python3 -m http.server 4173`

## Veröffentlichung

GitHub Pages: Branch `main`, Verzeichnis `/`. Eigene Domain: `haenggi.vip`. Die Datei `CNAME` enthält die Domain.

Die Website benötigt keinen Build-Schritt. App-Inhalte und Links stehen in `index.html`, Darstellung in `styles.css`, Scroll-Steuerung in `app.js`. Die unveränderte Cool-Website-Engine wird mit ihrer Lizenz geliefert.

Standardparts bleibt bis zur Veröffentlichung im HTML auskommentiert.

## Languages
German is served at `/`, English at `/en/`. Both are complete static pages with canonical and reciprocal hreflang links. The DE/EN switch preserves the current section and remembers an explicit choice. The default entry uses browser language only when no choice exists; explicit English URLs always remain English. `?lang=de` allows German even when browser storage is unavailable.

After editing German HTML or translations, regenerate English with:

```sh
python tools/build_english.py
```

Shared CSS, JavaScript and media are loaded from the site root; do not duplicate media in `en/`.
