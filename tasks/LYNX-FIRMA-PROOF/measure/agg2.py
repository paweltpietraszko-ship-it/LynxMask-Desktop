import json,glob,collections,sys
sys.stdout.reconfigure(encoding='utf-8')
d=sys.argv[1]; frag=collections.defaultdict(collections.Counter); ml=collections.Counter(); ctx=collections.defaultdict(list)
for f in glob.glob(d+'/*.json'):
    r=json.load(open(f,encoding='utf-8')); t=r['text']; seen=set()
    for w in r['warnings']:
        k=(w['rule'],w['fragment'].lower())
        if k in seen: continue
        seen.add(k); frag[w['rule']][w['fragment']]+=1
        if w['rule'] in sys.argv[2:]: ctx[w['rule']].append(t[max(0,w['start']-45):w['end']+15].replace('\n',' ').replace('\r',' '))
        if w['rule']=='MAP_LEAK':
            src=[k2 for k2,v in r['tokens'].items() if v.lower()==w['fragment'].lower()]
            ml[(src[0] if src else '?', w['fragment'])]+=1
for k in frag: print('\n==',k,sum(frag[k].values())); print(', '.join(f'{a}×{b}' for a,b in frag[k].most_common(130)))
print('\nMAP_LEAK src:',', '.join(f'{a}:{b}' for (a,b),c in ml.items()))
for k in ctx:
    print('\n--',k); [print('  ',c) for c in ctx[k][:70]]
