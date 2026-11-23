"""Generate the complete, independently indexable English page from German HTML."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[1]
s=(root/'index.html').read_text()
translations={
'Öffne eine IDX-Basisdatei und die dazugehörigen Änderungen direkt im Browser. Der 3D-Viewer zeigt die Leiterplatte mit ihren Bauteilen. In der Änderungshistorie prüfst du neue, verschobene und entfernte Komponenten. Bei Bedarf blendest du Bauteiltypen aus, lädst detaillierte OBJ-Modelle und exportierst deine Änderungen oder eine Antwortdatei für die Abstimmung zwischen Elektronik und Mechanik.': 'Open an IDX baseline file and its revisions directly in your browser. The 3D viewer shows the circuit board and its components. Use the change history to review added, moved and removed parts. Hide component types, load detailed OBJ models and export changes or a response file to coordinate between electronics and mechanical design.',
'Mit zwei Dateibereichen hast du Quelle und Ziel gleichzeitig im Blick. Wähle mehrere Dateien aus, kopiere oder verschiebe sie per Drag &amp; Drop, durchsuche ZIP-Archive wie Ordner und erstelle eigene Archive. Unterstützte Aktionen lassen sich über die Historie rückgängig machen. Die mobilen Versionen gibt es für Android, iPhone und iPad. Auf der Projektseite findest du Anleitungen für die Windows- und Linux-Builds sowie den Link zur macOS-Vorschau für Apple Silicon.': 'Two file panes keep the source and destination in view. Select multiple files, copy or move them with drag and drop, browse ZIP archives like folders and create new archives. Use the history to undo supported actions. Mobile versions are available for Android, iPhone and iPad. The project site has guides for the Windows and Linux builds and a link to the macOS preview for Apple silicon.',
'Mit zwei Dateibereichen hast du Quelle und Ziel gleichzeitig im Blick. Wähle mehrere Dateien aus, kopiere oder verschiebe sie per Drag & Drop, durchsuche ZIP-Archive wie Ordner und erstelle eigene Archive. Unterstützte Aktionen lassen sich über die Historie rückgängig machen. Die mobilen Versionen gibt es für Android, iPhone und iPad. Auf der Projektseite findest du Anleitungen für die Windows- und Linux-Builds sowie den Link zur macOS-Vorschau für Apple Silicon.': 'Two file panes keep the source and destination in view. Select multiple files, copy or move them with drag and drop, browse ZIP archives like folders and create new archives. Use the history to undo supported actions. Mobile versions are available for Android, iPhone and iPad. The project site has guides for the Windows and Linux builds and a link to the macOS preview for Apple silicon.',
'Plane deine Reise mit einzelnen Stopps und ergänze unterwegs Fotos und Videos zu jedem Ort. Wechsle zwischen interaktivem 3D-Globus, Karte und Satellitenansicht, um deine Route und die zurückgelegte Strecke nachzuvollziehen. Aus deinen Stopps entsteht eine Reisegeschichte, die du als Slideshow ansehen oder mit anderen teilen kannst.': 'Plan your trip stop by stop and add photos and videos to each place along the way. Switch between an interactive 3D globe, map and satellite view to retrace your route and see how far you traveled. Turn your stops into a travel story you can watch as a slideshow or share with others.',
'Spiele Schach, Dame, Mühle, Reversi, Vier Gewinnt und Tic-Tac-Toe in einer App. Übe offline gegen Bots oder starte eine Online-Partie. Mit einem privaten Raumcode lädst du Freunde gezielt ein. Beim Schach helfen dir markierte gültige Züge beim Einstieg, und mit der Rangliste und den persönlichen Statistiken behältst du deine Ergebnisse im Blick.': 'Play chess, checkers, Nine Men’s Morris, Reversi, Connect Four and tic-tac-toe in one app. Practice offline against bots or start an online match. Use a private room code to invite friends. Highlighted legal moves help you get started in chess, while the leaderboard and personal stats help you keep track of your results.',
'OpenGroove spielt deine eigene Musiksammlung auf Android und iPhone ohne OpenGroove-Konto. Durchsuche lokale Audiodateien nach Titeln, Interpreten, Alben oder Genres und stelle eigene Playlists zusammen. Bereits lokal gespeicherte Musik kannst du offline hören.': 'OpenGroove plays your own music collection on Android and iPhone without an OpenGroove account. Browse local audio files by track, artist, album or genre and make your own playlists. Music already stored on your device plays offline.',
'Lies PDF, TXT, Markdown und HTML oder lass dir eine ausgewählte Textstelle vorlesen. Die Texterkennung macht gescannte Seiten direkt auf dem Gerät für die Sprachausgabe nutzbar. Passe Stimme und Tempo an, lass Dialoge mit wechselnden Stimmen lesen und pausiere die Wiedergabe am Sperrbildschirm. Nach dem Download des Stimmpakets funktioniert das Vorlesen offline.': 'Read PDF, TXT, Markdown and HTML documents or listen from a passage you choose. On-device text recognition prepares scanned pages for narration. Choose a voice and speed, switch voices in dialogue mode and pause from the lock screen. Narration works offline after the voice pack downloads.',
'Schneide Clips, passe Bildformat, Zoom und Tempo an und gib deinen Aufnahmen mit Filtern einen eigenen Look. Markiere ein Motiv, damit der Bildausschnitt seiner Bewegung folgen kann. Speichere ein Projekt zur späteren Bearbeitung oder exportiere das Ergebnis als Video oder Einzelbild. Die Bearbeitung läuft direkt auf deinem Gerät.': 'Trim clips, adjust the aspect ratio, zoom and speed, and give your footage a different look with filters. Select a subject so the crop can follow its movement. Save a project to continue later or export the result as a video or a still frame. Editing runs directly on your device.',
'Lerne eine von neun Sprachen in kurzen Lektionen für Alltag und Reisen. Starte als Anfänger oder finde mit einem Einstufungstest das passende Niveau. Übe mit Hörpassagen und Textaufgaben. Auf fortgeschrittenen Stufen ordnest du Aussagen ein und ziehst Schlussfolgerungen. Die Fehlerwiederholung greift Wörter auf, die du zuvor verwechselt hast.': 'Learn one of nine languages through short lessons for everyday life and travel. Start as a beginner or take a placement test to find the right level. Practice with listening passages and written exercises. At advanced levels, interpret statements and draw conclusions. Review brings back words you previously mixed up.',
'OpenCommander-Website öffnen': 'Open the OpenCommander website',
'OpenCommander-Dokumentation lesen': 'Read the OpenCommander documentation',
'OpenCommander-Dokumentation': 'OpenCommander documentation',
'>Dokumentation<': '>Documentation<',

'>Sprachen lernen<': '>Language learning<',
'Musik hinzufügen:':'Add your music:',
' Android liest freigegebene Audiodateien ein. Auf dem iPhone verbindest du Musikordner oder Apples Musikmediathek und kannst einzelne Dateien importieren.':' Android reads audio files you allow it to access. On iPhone, connect music folders or Apple’s music library, or import individual files.',
'Wiedergabe gestalten:':'Make playback yours:',
' Favoriten markieren, die Abspielliste bearbeiten sowie Zufall und Wiederholung nutzen. Auf dem iPhone hilft zusätzlich ein Sleep-Timer beim Einschlafen.':' Mark favorites, edit the play queue, and use shuffle and repeat. On iPhone, a sleep timer can also stop playback when it is time to rest.',
'Sammlung aufräumen:':'Organize your collection:',
' Korrigiere Titelangaben manuell oder suche online nach Metadaten und Covern. Blende unerwünschte Titel oder Ordner aus. Auf Android kannst du auch doppelte Audiodateien finden und korrigierte Text-Tags in MP3-Dateien speichern.':' Correct track information manually or search online for metadata and cover art. Hide unwanted tracks or folders. On Android you can also find duplicate audio files and write corrected text tags to MP3 files.',
'Sichern und mitnehmen:':'Back up and transfer:',
' Alben, Playlists oder die Bibliothek als OpenGroove-Backup sichern und zwischen Android und iPhone übertragen. Bei Apples Musikmediathek werden Angaben und Zuordnungen gesichert, nicht die Audiodateien.':' Save albums, playlists or your library as an OpenGroove backup and transfer them between Android and iPhone. For Apple’s music library, backups contain information and associations, not the audio files.',

'Entdecke IDX-Viewer, OpenCommander, TravelTrack, OpenGames, OpenGroove, OpenVoice PDF, openVideo und OpenLearn: Apps für Technik und Alltag.': 'Discover IDX-Viewer, OpenCommander, TravelTrack, OpenGames, OpenGroove, OpenVoice PDF, openVideo and OpenLearn: tools for engineering and everyday life.',


'OpenGroove-Handbuch lesen':'Read the OpenGroove manual in German',
'>Handbuch<':'>Manual (DE)<',
'Videoeditor': 'Video editor',
'>8 Apps<': '>8 apps<',
'Apps und PCB-Werkzeuge':'Apps and PCB tools',
'Scroll-Video pausieren':'Pause scroll video',
'>5 Apps<':'>5 apps<',
'Entdecke IDX-Viewer, OpenCommander, TravelTrack, OpenGames und OpenGroove: Werkzeuge für PCB, Dateien, Reisen, Brettspiele und Musik mit direkten App-Links.':'Discover IDX-Viewer, OpenCommander, TravelTrack, OpenGames and OpenGroove: apps for PCBs, files, travel, board games and music, with direct download links.',
'Mechanische Struktur aus dem Hintergrundfilm von haenggi.vip':'Mechanical structure from the haenggi.vip background film',
'Veröffentlichte Apps und Engineering-Werkzeuge':'Published apps and engineering tools',





'Eine App zum Lernen. Weitere Funktionen werden mit der Veröffentlichung vorgestellt.':'An app for learning. More features will be introduced at launch.',
'Eine App rund um PDF-Dokumente, Texterkennung und Sprache.':'An app for PDF documents, text recognition and speech.',
'Ein Videoprojekt in Entwicklung. Details folgen zur Veröffentlichung.':'A video project in development. Details will be shared at launch.',
'3D-Engineering-Tools und native Apps für Alltag, Medien und Lernen.': '3D engineering tools and native apps for everyday life, media, and learning.',
'VON DER LEITERPLATTE BIS ZUR WELTREISE':'FROM CIRCUIT BOARDS TO WORLD TRAVELS',
'Werkzeuge für Technik.<br>Apps für jeden Tag.':'Tools for engineering.<br>Apps for everyday life.',
'Was als Nächstes kommt.':"What’s coming next.",
'Ideen. Als Apps.':'Ideas. Made into apps.',
'Apps nach Plattform filtern':'Filter apps by platform','Direkt zu einer App':'Jump to an app','Hauptnavigation':'Main navigation','Scrollfortschritt':'Scroll progress','PCB und Engineering':'PCB and engineering','Apps für den Alltag':'Everyday apps','Zu den Apps':'Skip to apps','Apps entdecken':'Explore apps','IN ENTWICKLUNG':'IN DEVELOPMENT','In Entwicklung':'In development','Dateimanager':'File manager','Reisetagebuch':'Travel journal','Brettspiele':'Board games','Musikplayer':'Music player','3D-PCB-Viewer':'3D PCB viewer','PDF · OCR · Sprache':'PDF · OCR · Speech','Lernen':'Learning','App öffnen':'Open app','Nach oben':'Back to top','Bewegung reduzieren':'Reduce motion','>Alle<':'>All<',' öffnen"':' — open app"',' auf GitHub"':' on GitHub"',' auf Google Play"':' on Google Play"',' im App Store"':' on the App Store"'
}
for de,en in translations.items():s=s.replace(de,en)
s=s.replace('<html lang="de">','<html lang="en">').replace('"inLanguage": "de"','"inLanguage": "en"').replace('content="de_DE"','content="en_US"')
s=re.sub(r'href="(styles\.css(?:\?[^"]*)?)"',r'href="../\1"',s)
s=re.sub(r'(src|href|poster|data-scroll-src|data-scroll-src-mobile)="(assets/|config.js|app.js|cool-website.js|language.js)',r'\1="../\2',s)
s=s.replace('<link rel="canonical" href="https://haenggi.vip/">','<link rel="canonical" href="https://haenggi.vip/en/">').replace('<meta property="og:url" content="https://haenggi.vip/">','<meta property="og:url" content="https://haenggi.vip/en/">')
s=s.replace('href="./?lang=de" lang="de" hreflang="de" aria-current="page"','href="../?lang=de" lang="de" hreflang="de"').replace('href="en/?lang=en" lang="en" hreflang="en"','href="./?lang=en" lang="en" hreflang="en" aria-current="page"')
s=s.replace('aria-label="Sprache"','aria-label="Language"')
# Stable app IDs identify the same products in both languages; page IDs differ.
m=re.search(r'<script type="application/ld\+json">(.*?)</script>',s,re.S)
data=json.loads(m[1]);page=data['@graph'][1];page['@id']='https://haenggi.vip/en/#page';page['url']='https://haenggi.vip/en/'
s=s[:m.start(1)]+'\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n'+s[m.end(1):]
s=s.replace('href="opengroove/handbuch/"','href="../opengroove/handbuch/"')
(root/'en').mkdir(exist_ok=True);(root/'en/index.html').write_text(s)
