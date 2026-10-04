"""Generate the complete, independently indexable English page from German HTML."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
s=(root/'index.html').read_text()
translations={
'Apps und PCB-Werkzeuge':'Apps and PCB tools',
'>5 Apps<':'>5 apps<',
'Entdecke IDX-Viewer, OpenCommander, TravelTrack, OpenGames und OpenGroove: Werkzeuge für PCB, Dateien, Reisen, Brettspiele und Musik mit direkten App-Links.':'Discover IDX-Viewer, OpenCommander, TravelTrack, OpenGames and OpenGroove: apps for PCBs, files, travel, board games and music, with direct download links.',
'Mechanische Struktur aus dem Hintergrundfilm von haenggi.vip':'Mechanical structure from the haenggi.vip background film',
'Veröffentlichte Apps und Engineering-Werkzeuge':'Published apps and engineering tools',
'IDX-Viewer ist ein 3D-PCB-Viewer für Leiterplatten im IDX-Format. Änderungen prüfen, bearbeiten und als Antwortdatei exportieren.':'IDX-Viewer is a 3D PCB viewer for circuit boards in IDX format. Review and edit changes, then export them as a response file.',
'OpenCommander ist ein Dateimanager mit zwei Fenstern. Dateien per Drag & Drop verschieben und ZIP-Archive durchsuchen.':'OpenCommander is a dual-pane file manager. Move files with drag and drop and browse ZIP archives.',
'TravelTrack ist ein digitales Reisetagebuch: Stopps, Fotos und Videos festhalten und Reiserouten auf einer interaktiven 3D-Weltkarte erkunden.':'TravelTrack is a digital travel journal. Save stops, photos and videos, and explore your routes on an interactive 3D world map.',
'OpenGames vereint Schach, Dame, Mühle, Reversi, Vier Gewinnt und Tic-Tac-Toe. Die Brettspiele lokal, gegen Bots oder online spielen.':"OpenGames brings together chess, checkers, Nine Men's Morris, Reversi, Connect Four and tic-tac-toe. Play locally, against bots or online.",
'OpenGroove ist ein Musikplayer für lokale Musikdateien und Alben. Die Musiksammlung verwalten und fehlende Metadaten auf Wunsch ergänzen.':'OpenGroove is a music player for local audio files and albums. Organize your music collection and optionally fill in missing metadata.',
'Eine App zum Lernen. Weitere Funktionen werden mit der Veröffentlichung vorgestellt.':'An app for learning. More features will be introduced at launch.',
'Eine App rund um PDF-Dokumente, Texterkennung und Sprache.':'An app for PDF documents, text recognition and speech.',
'Ein Videoprojekt in Entwicklung. Details folgen zur Veröffentlichung.':'A video project in development. Details will be shared at launch.',
'VON DER LEITERPLATTE BIS ZUR WELTREISE':'FROM CIRCUIT BOARDS TO WORLD TRAVELS',
'Werkzeuge für Technik.<br>Apps für jeden Tag.':'Tools for engineering.<br>Apps for everyday life.',
'Was als Nächstes kommt.':"What’s coming next.",
'Ideen. Als Apps.':'Ideas. Made into apps.',
'Apps nach Plattform filtern':'Filter apps by platform','Direkt zu einer App':'Jump to an app','Hauptnavigation':'Main navigation','Scrollfortschritt':'Scroll progress','PCB und Engineering':'PCB and engineering','Apps für den Alltag':'Everyday apps','Zu den Apps':'Skip to apps','Apps entdecken':'Explore apps','IN ENTWICKLUNG':'IN DEVELOPMENT','In Entwicklung':'In development','Dateimanager':'File manager','Reisetagebuch':'Travel journal','Brettspiele':'Board games','Musikplayer':'Music player','3D-PCB-Viewer':'3D PCB viewer','PDF · OCR · Sprache':'PDF · OCR · Speech','Lernen':'Learning','App öffnen':'Open app','Nach oben':'Back to top','Bewegung reduzieren':'Reduce motion','>Alle<':'>All<',' öffnen"':' — open app"',' auf GitHub"':' on GitHub"',' auf Google Play"':' on Google Play"',' im App Store"':' on the App Store"'
}
for de,en in translations.items():s=s.replace(de,en)
s=s.replace('<html lang="de">','<html lang="en">').replace('"inLanguage": "de"','"inLanguage": "en"').replace('content="de_DE"','content="en_US"')
s=s.replace('href="styles.css"','href="../styles.css"').replace('href="cool-website.css"','href="../cool-website.css"')
s=re.sub(r'(src|href|poster|data-scroll-src|data-scroll-src-mobile)="(assets/|config.js|app.js|cool-website.js|language.js)',r'\1="../\2',s)
s=s.replace('<link rel="canonical" href="https://haenggi.vip/">','<link rel="canonical" href="https://haenggi.vip/en/">').replace('<meta property="og:url" content="https://haenggi.vip/">','<meta property="og:url" content="https://haenggi.vip/en/">')
s=s.replace('href="./?lang=de" lang="de" hreflang="de" aria-current="page"','href="../?lang=de" lang="de" hreflang="de"').replace('href="en/?lang=en" lang="en" hreflang="en"','href="./?lang=en" lang="en" hreflang="en" aria-current="page"')
s=s.replace('aria-label="Sprache"','aria-label="Language"')
# Stable app IDs identify the same products in both languages; page IDs differ.
m=re.search(r'<script type="application/ld\+json">(.*?)</script>',s,re.S)
data=json.loads(m[1]);page=data['@graph'][1];page['@id']='https://haenggi.vip/en/#page';page['url']='https://haenggi.vip/en/'
s=s[:m.start(1)]+'\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n'+s[m.end(1):]
(root/'en').mkdir(exist_ok=True);(root/'en/index.html').write_text(s)
