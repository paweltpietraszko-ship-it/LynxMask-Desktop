"""Firmy z formą prawną (z bazy): ile razy ich rdzeń jest jawny w tekście bazy vs nowej wersji. Wypisuje pogorszenia."""
import json,glob,os,re,sys
sys.stdout.reconfigure(encoding='utf-8')
a,b=sys.argv[1],sys.argv[2]
FORM=re.compile(r"(?i)[\s,]*(?:sp\.?\s*z\s*o\.?\s*o\.?|sp\.?\s?[jkp]\.?|s\.\s?a\.?|s\.\s?c\.?|spół\w*.*|gmbh|ltd\.?)\s*$")
ROLE=re.compile(r"^(?:(?:\d[\d/]*|[A-Z]\d?)[.)]\s+|(?:Wykonawc|Zamawiając|Odwołując|Przystępując|Konsorcj|Lider|Partner)\w*\s*[:–-]?\s+)+")
worse=better=0
for f in sorted(glob.glob(a+'/*.json')):
    n=os.path.basename(f); A=json.load(open(f,encoding='utf-8')); B=json.load(open(b+'/'+n,encoding='utf-8'))
    for k,v in A['tokens'].items():
        if not k.startswith('FIRMA') or not FORM.search(v): continue
        core=ROLE.sub('',FORM.sub('',v)).strip(' "„”“,.')
        if len(core)<3: continue
        rx=re.compile(r'(?<!\w)'+re.escape(core)+r'(?!\w)',re.I)
        ca,cb=len(rx.findall(A['text'])),len(rx.findall(B['text']))
        if cb>ca: worse+=1; print('GORZEJ',n,repr(core),ca,'->',cb)
        elif cb<ca: better+=1
print('gorzej',worse,'lepiej',better)
