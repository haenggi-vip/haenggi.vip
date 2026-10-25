"""Bundle the published reader as a single self-contained HTML download."""
from pathlib import Path
import re,base64,zipfile,mimetypes
root=Path(__file__).resolve().parents[1]/'opengroove/handbuch'
s=(root/'index.html').read_text()
for name in ['manual.css','print.css']:
    s=re.sub(r'<link rel="stylesheet" href="'+name+r'"[^>]*>',lambda m:'<style>\n'+(root/name).read_text()+'\n</style>',s)
s=s.replace('<script src="manual.js" defer></script>','<script>\n'+(root/'manual.js').read_text()+'\n</script>')
def inline(m):
    key,path=m.groups();mime=mimetypes.guess_type(path)[0]
    return f'{key}="data:{mime};base64,'+base64.b64encode((root/path).read_bytes()).decode()+'"'
s=re.sub(r'(src|href)="(images/[^"]+)"',inline,s)
s=s.replace('href="../../?lang=de#opengroove"','href="https://haenggi.vip/?lang=de#opengroove"')
s=s.replace('href="OpenGroove-Handbuch.zip" download','href="https://haenggi.vip/opengroove/handbuch/"').replace('↓ Offline-Handbuch (.zip)','Online-Handbuch öffnen ↗')
with zipfile.ZipFile(root/'OpenGroove-Handbuch.zip','w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('OpenGroove-Handbuch.html',s)
    z.writestr('LIESMICH.txt','ZIP entpacken und OpenGroove-Handbuch.html im Browser öffnen. Text, Suche und Bilder funktionieren offline. Drucken / PDF öffnet den Druckdialog. Externe Links benötigen Internet.\n')
print('Offline package:',(root/'OpenGroove-Handbuch.zip').stat().st_size,'bytes')
