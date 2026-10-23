"""Isolated re-execution of delivery metrics. Prints aggregate counts only.
argv backend output_dir. Uses existing local corpora/cache; never extracts OCR.
GOLD evaluator and owner literal metric reused unchanged, not a new semantic oracle.
"""
import ast, collections, contextlib, difflib, hashlib, io, json, logging, os, re, sys, tempfile, time
from pathlib import Path
backend, out = map(lambda p: Path(p).resolve(), sys.argv[1:3])
out.mkdir(exist_ok=False)
state_root = out/'state'; state_root.mkdir()
for k in ('PROFILE_DIR','ANONYMIZER_PROFILE_DIR','PSE_REGISTRY','ARCHIVE_DIR','HARDWARE_PROFILE'):
    os.environ[k] = str(state_root/k)
os.chdir(backend); sys.path.insert(0,str(backend))
import spacy_ner
from anonymizer import build_anonymizer
from pipeline import AppState, pseudonymize_document
logging.disable(logging.CRITICAL)
repo = Path('C:/Users/p_pie/Desktop/LynxMask-Desktop')
scratch = Path('C:/Users/p_pie/AppData/Local/Temp/claude/C--Users-p-pie-Desktop-LynxMask-Desktop/6fd99904-330e-4b1d-93e7-d4df460463ee/scratchpad')
review = Path('C:/Users/p_pie/AppData/Local/Temp/lynx_cc_review')
TOKEN = re.compile(r'\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)')
ALNUM = re.compile(r'[^\W_]{3,}')
PERSON = ('imie_nazwisko','skarzacy','oskarzony','autor','osoba')
DATES = ('data','data_urodzenia')
hashes={}
def load_functions(path,names):
    source=path.read_text(encoding='utf-8-sig')
    hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    tree=ast.parse(source)
    funcs=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names]
    if len(funcs)!=len(names): raise RuntimeError('Missing evaluator function')
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(path),'exec'),globals())
load_functions(review/'gold/human_view.py',{'char_map','evaluate'})
load_functions(repo/'testset_owner/run_testset.py',{'_kind','_flat','leaks'})
summary={'backend':str(backend),'metric_source_hashes':hashes}
def run(text):
    s=AppState();s.spacy_ner_mod=spacy_ner
    d=tempfile.mkdtemp(dir=state_root)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        s.anonymizer,_,s.anon_map,s.morf_env=build_anonymizer(d,d+'/hw.json')
        return pseudonymize_document(text,s)
def checkpoint(label,counts):
    summary[label]=counts
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(label,json.dumps(counts,ensure_ascii=False),flush=True)
for split in ('dev','test'):
    agg=collections.Counter();types=collections.defaultdict(collections.Counter); warns=[]
    data=repo/'backend/dataset_gold_20261022'/split
    for f in sorted(data.glob('*.txt')):
        orig=f.read_text(encoding='utf-8');gold=json.loads(f.with_suffix('.json').read_text(encoding='utf-8'))
        r=run(orig)
        if r.error: agg['engine_errors']+=1;continue
        warns.append(len(r.guard_warnings))
        for it in evaluate(orig,gold,r.text,r.guard_warnings):
            agg[it['kind']+':'+it['status']]+=1
            if it['kind']=='pii': types[it['type']][it['status']]+=1
    checkpoint('gold_'+split,{'docs':len(warns),'counts':dict(agg),'types':{k:dict(v) for k,v in types.items()},'warnings':sum(warns),'warnings_per_doc':round(sum(warns)/max(1,len(warns)),2)})
for label,root in [('owner',repo/'testset_owner')]:
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    gold={r['id']:r['entities'] for s in ('clean','stress') for r in json.loads((root/('gold_'+s+'.json')).read_text(encoding='utf-8'))}
    counts=collections.defaultdict(collections.Counter)
    for j in manifest:
        c=counts[j['set']];r=run((root/'corpus'/j['id']).read_text(encoding='utf-8',errors='replace'))
        if r.error:c['engine_errors']+=1;continue
        c['docs']+=1;c['warnings']+=len(r.guard_warnings)
        warnings=[w['fragment'] for w in r.guard_warnings]
        for field,kind,frag in leaks(r.text,gold.get(j['id'],{})):
            guarded=any(frag in w or w in frag for w in warnings)
            c[kind+(':warned' if guarded else ':silent')]+=1
        for field,val in gold.get(j['id'],{}).items():c[_kind(field)+':total']+=1
    checkpoint(label,{k:dict(v) for k,v in counts.items()})

