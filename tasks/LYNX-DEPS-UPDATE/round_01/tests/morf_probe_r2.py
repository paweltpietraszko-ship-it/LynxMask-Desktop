"""Narrow independent before/after Morfeusz probe. Run before and after changing only morfeusz2.
python morf_probe_r2.py before|after WORKTREE OUTPUT
Synthetic data only, exact-SHA archive, no live owner backend.
"""
import io,json,os,re,socket,subprocess,sys,tarfile,tempfile
from pathlib import Path
mode,root,output=sys.argv[1:]
root,out=Path(root).resolve(),Path(output).resolve()
work=out/mode
work.mkdir(parents=True,exist_ok=False)
sha='5c28eb065fca3b3e86283c21ea56652e51e1797c'
raw=subprocess.run(['git','-C',str(root),'archive',sha,'backend'],capture_output=True,check=True).stdout
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(work,filter='data')
for folder in ('profile','anon','archive','tmp'):(work/folder).mkdir()
os.environ.update(PROFILE_DIR=str(work/'profile'),ANONYMIZER_PROFILE_DIR=str(work/'anon'),
 ARCHIVE_DIR=str(work/'archive'),PSE_REGISTRY=str(work/'registry.json'),HARDWARE_PROFILE=str(work/'hardware.json'),
 LYNX_OCR_MODEL_DIR=str(out.parent/'photo-r2/models'),LYNX_OCR_ENGINE='rapid')
tempfile.tempdir=str(work/'tmp')
os.chdir(work/'backend')
sys.path.insert(0,str(work/'backend'))
real_connect=socket.socket.connect
def protect(sock,address):
 if isinstance(address,tuple) and address[1]==8765:raise ConnectionRefusedError('owner backend isolated')
 return real_connect(sock,address)
socket.socket.connect=protect
import importlib.metadata,morfeusz2
m=morfeusz2.Morfeusz()
texts=[
 'Żaneta Kowalska zawarła umowę z Janem Nowakiem. Podpis Żanety Kowalskiej.',
 'Róża zakwitła na rabacie. Pani Róża Malina odebrała pismo.',
 'Piotr Masłowski\nAnna Jankowska\nPodpisy stron umowy.',
 'Adres: ul. Żółkiewskiego 14/7, 35-001 Rzeszów.',
 'Dokument dla Zofii Kwiatkowskiej oraz Bartłomieja Wójcika.',
 'Nabywca: Róża sp. z o.o. Przedmiot umowy: wyposażenie biura.',
 'Data sporządzenia: 21.10.2026. Opłata wynosi 123 złote.',
 'Oskarżonego Jana Jankowskiego reprezentuje adwokat Grażyna Nowak.'
]
words=sorted(set(re.findall(r'[^\W\d_]{2,}','\n'.join(texts))))
lex={w:sorted(set(str(x[2]) for x in m.analyse(w))) for w in words}
from fastapi.testclient import TestClient
import pseudominizer_api as api
items=[]
with TestClient(api.app,base_url='http://127.0.0.1:8765') as client:
 hdr={'X-Api-Token':api._API_TOKEN}
 health=client.get('/health',headers=hdr).json()
 assert health['status']=='ok' and health['anonymizer'] and health['spacy_ner'] and health['crypto_ok']
 for i,text in enumerate(texts):
  r=client.post('/preview',files={'file':('synthetic.txt',text.encode('utf-8'),'text/plain')},headers=hdr)
  j=r.json();v=j.get('anonymized_preview','')
  if v.startswith('[Dokument pseudonimizowany.'):v=v.split('\n\n',1)[-1]
  items.append({'case':i,'code':r.status_code,'blocked':j.get('blocked'),'text':v,'tokens':j.get('tokens'),'error':j.get('error')})
 image=out.parent/'photo-r2/synthetic_90.png'
 r=client.post('/preview',files={'file':('synthetic.png',image.read_bytes(),'image/png')},headers=hdr)
 j=r.json();v=j.get('anonymized_preview','')
 if v.startswith('[Dokument pseudonimizowany.'):v=v.split('\n\n',1)[-1]
 items.append({'case':'rotated-image','code':r.status_code,'blocked':j.get('blocked'),'text':v,'tokens':j.get('tokens'),'error':j.get('error'),'ocr':j.get('ocr')})
result={'sha':sha,'version':importlib.metadata.version('morfeusz2'),'dict_id':m.dict_id(),'words':lex,'items':items}
(out/(mode+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=1),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('sha','version','dict_id')}),'words',len(words),'api_cases',len(items))
