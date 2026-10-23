import ast,collections,difflib,json,re,statistics,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
data=Path(sys.argv[2]).resolve()
source=root/'tasks/LYNX-GOLD-SET/measure/human_view.py'
TOKEN=re.compile(r'\b(?:FIRMA|OSOBA|NUMER|KWOTA|ADRES|INSTYTUCJA|EMAIL)_\d{3}(?!\d)')
ALNUM=re.compile(r'[^\W_]{3,}')
ns={'re':re,'difflib':difflib,'TOKEN':TOKEN,'ALNUM':ALNUM}
tree=ast.parse(source.read_text(encoding='utf-8'))
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('char_map','evaluate'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
word=re.compile(r'\b[^\W\d_]+(?:[-’\x27][^\W\d_]+)*\b')
variants={name:{'counts':[],'groups':[],'new':0,'overlap_gold':0,'overlap_not_pii':0,'pii':collections.Counter(),'osoba':collections.Counter(),'fixed_silent':collections.Counter()} for name in ('line_is_boundary','line_not_boundary')}
baseline=collections.Counter(); base_r1=[]; base_all=[]; reconstruction=collections.Counter()
saved=collections.defaultdict(collections.deque)
for line in (root/'gold_out/items_dev.jsonl').read_text(encoding='utf-8').splitlines():
    item=json.loads(line)
    if item['kind']=='pii': saved[(item['doc'],item['type'],item['text'])].append(item['status'])
for view in sorted((root/'gold_out/views').glob('dev_*.txt')):
    doc=view.stem[4:]
    text,warning_text=view.read_text(encoding='utf-8').split('\n\n=== OSTRZEŻENIA GUARDA ===\n',1)
    orig=(data/(doc+'.txt')).read_text(encoding='utf-8')
    gold=json.loads((data/(doc+'.json')).read_text(encoding='utf-8'))
    old=[]; lines=warning_text.splitlines()
    base_all.append(len(lines)); base_r1.append(sum('R1' in line.split(': ',1)[0] for line in lines))
    for line in lines:
        header,fragment=line.split(': ',1)
        for m in re.finditer(re.escape(fragment),text):
            old.append({'start':m.start(),'end':m.end()})
    old_eval=ns['evaluate'](orig,gold,text,old)
    for it in old_eval:
        if it['kind']=='pii':
            if it['status']!='zakryte': it['status']=saved[(doc,it['type'],it['text'])].popleft()
            reconstruction[it['status']]+=1
    cm=ns['char_map'](orig,text)
    mapped_pii=[]; mapped_not=[]
    for key,target in (('pii',mapped_pii),('not_pii',mapped_not)):
        for it in gold.get(key,[]):
            positions=[cm[k][1] for k in range(it['start'],it['end']) if cm[k][0]=='plain' and cm[k][1] is not None]
            if positions: target.append((min(positions),max(positions)+1))
    for name,v in variants.items():
        boundary=re.compile(r'[.!?\n]+' if name=='line_is_boundary' else r'[.!?]+')
        sentence_start=0; candidates=[]
        for match in list(boundary.finditer(text))+[None]:
            end=match.start() if match else len(text)
            tokens=list(re.finditer(TOKEN.pattern+'|'+word.pattern,text[sentence_start:end]))
            for m in tokens[1:]:
                s,e=sentence_start+m.start(),sentence_start+m.end(); value=m.group(0)
                if value[0].isupper() and not TOKEN.fullmatch(value):
                    candidates.append({'start':s,'end':e,'fragment':value})
            sentence_start=match.end() if match else len(text)
        v['counts'].append(len(candidates)); v['groups'].append(len({w['fragment'].casefold() for w in candidates}))
        v['new']+=sum(not any(o['start']<w['end'] and w['start']<o['end'] for o in old) for w in candidates)
        v['overlap_gold']+=sum(any(s<w['end'] and w['start']<e for s,e in mapped_pii) for w in candidates)
        v['overlap_not_pii']+=sum(any(s<w['end'] and w['start']<e for s,e in mapped_not) for w in candidates)
        combined=ns['evaluate'](orig,gold,text,candidates)
        for before,after in zip(old_eval,combined):
            if after['kind']!='pii': continue
            if before['status']=='wyciek_z_ostrzezeniem': after['status']='wyciek_z_ostrzezeniem'
            v['pii'][after['status']]+=1
            if after['type']=='OSOBA': v['osoba'][after['status']]+=1
            if before['status']=='cichy_wyciek' and after['status']!='cichy_wyciek': v['fixed_silent'][after['type']]+=1
for v in variants.values():
    for key in ('counts','groups'):
        values=v[key]; v[key]={'total':sum(values),'mean':round(statistics.mean(values),2),'median':statistics.median(values),'max':max(values)}
result={'basis':'9f8a07e cached outputs; 40 GOLD dev, no engine rerun; current engine, not redesign','segmentation':'simple .!?; optional newline boundary; first token excluded, masked tokens excluded; no abbreviation model','coverage_method':'actual baseline item statuses from saved items_dev; additional gain counts items fully covered by the new rule alone, hence conservative for mixed coverage; new count is lower bound because saved warning text lacks offsets','baseline':{'all_warnings':sum(base_all),'r1':sum(base_r1),'all_mean':round(statistics.mean(base_all),2),'r1_mean':round(statistics.mean(base_r1),2)},'reconstructed_baseline_pii':dict(reconstruction),'variants':variants}
(root/'capital_whatif.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))

