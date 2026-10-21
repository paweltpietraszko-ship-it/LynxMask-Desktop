"""Independent dependency-environment audit on synthetic data, isolated archive copies.
Usage: python environment_probe_r1.py prepare|api-old|api-new|suite WORKTREE OUTPUT
No connection to the owner's backend; no user profile.
"""
import io, json, os, socket, subprocess, sys, tarfile, tempfile
from pathlib import Path
mode, root, output = sys.argv[1:]
root, out = Path(root).resolve(), Path(output).resolve()
sha='0219ffd01bf3823a2ca7b57154541d8907608c6c'
out.mkdir(parents=True,exist_ok=True)
if mode == 'prepare':
    raw=subprocess.run(['git','-C',str(root),'archive',sha,'backend'],capture_output=True,check=True).stdout
    for name in ('api-old','api-new','suite'):
        target=out/name
        target.mkdir(exist_ok=False)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            tar.extractall(target,filter='data')
    print('Prepared three isolated exact-SHA copies')
    raise SystemExit
work=out/mode
backend=work/'backend'
os.chdir(backend)
sys.path.insert(0,str(backend))
for name in ('profile','anon_profile','archive','tmp'):
    (work/name).mkdir(exist_ok=True)
os.environ.update(PROFILE_DIR=str(work/'profile'),ANONYMIZER_PROFILE_DIR=str(work/'anon_profile'),
                  ARCHIVE_DIR=str(work/'archive'),PSE_REGISTRY=str(work/'registry.json'),
                  HARDWARE_PROFILE=str(work/'hardware.json'),PYTHONIOENCODING='utf-8',
                  PYTHONDONTWRITEBYTECODE='1',LYNX_OCR_ENGINE='rapid',
                  LYNX_OCR_MODEL_DIR=str(out.parent/'photo-r2/models'))
tempfile.tempdir=str(work/'tmp')
real_connect=socket.socket.connect
def local_guard(sock,address):
    if isinstance(address,tuple) and address[1]==8765:
        raise ConnectionRefusedError('audit: owner backend deliberately not contacted')
    return real_connect(sock,address)
socket.socket.connect=local_guard
if mode == 'suite':
    import pytest
    raise SystemExit(pytest.main(['tests','-q','--tb=short','-o','log_file='+str(work/'pytest.log')]))
from fastapi.testclient import TestClient
import pseudominizer_api as api
import benchmark
from PIL import Image
dataset=Path('C:/Users/p_pie/Desktop/LynxMask-Desktop/backend/dataset_20260627_095419')
gold=json.loads((dataset/'ground_truth.json').read_text(encoding='utf-8'))
items=[]
with TestClient(api.app,base_url='http://127.0.0.1:8765') as client:
    hdr={'X-Api-Token':api._API_TOKEN}
    health=client.get('/health',headers=hdr).json()
    assert health['status']=='ok' and health['anonymizer'] and health['spacy_ner'] and health['crypto_ok']
    def post(label,name,data,mime,gt=None):
        response=client.post('/preview',files={'file':(name,data,mime)},headers=hdr)
        body=response.json()
        text=body.get('anonymized_preview','')
        # PSE allocation time/counter is not dependency behavior.
        if text.startswith('[Dokument pseudonimizowany.'):
            text=text.split('\n\n',1)[-1]
        item={'id':label,'code':response.status_code,'blocked':body.get('blocked'),
              'error':bool(body.get('error')),'text':text,'tokens':body.get('tokens'),
              'ocr':body.get('ocr')}
        if gt is not None:
            item['benchmark']=benchmark.analyze(gt,body)
        items.append(item)
    for n,g in enumerate(gold):
        post(Path(g['file']).stem,'synthetic.png',(dataset/g['file']).read_bytes(),'image/png',g)
        if (n+1)%10==0:
            print(mode+': '+str(n+1)+' benchmark images',flush=True)
    image=Image.open(dataset/gold[0]['file']).convert('RGB')
    for quality in (70,85,95):
        buffer=io.BytesIO()
        image.save(buffer,format='JPEG',quality=quality)
        post('jpeg-'+str(quality),'synthetic.jpg',buffer.getvalue(),'image/jpeg')
    for i,text in enumerate(('Umowa zawarta przez Żanetę Kowalską. Kontakt test.audit@example.org.',
                             'PESEL 44051401359. Wartość umowy 123 złotych.',
                             'Pani Anna Malina odebrała dokument w dniu dzisiejszym.')):
        post('text-'+str(i),'synthetic.txt',text.encode('utf-8'),'text/plain')
    post('invalid-image','bad.png',b'not an image','image/png')
result={'sha':sha,'health_ok':True,'items':items}
(out/(mode+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=1),encoding='utf-8')
print(mode+': '+str(len(items))+' cases completed; result outside repository')
