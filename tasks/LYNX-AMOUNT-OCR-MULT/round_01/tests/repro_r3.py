"""Independent sibling checks for longest-overlap selection, synthetic input."""
import json,os,re,sys
os.chdir(sys.argv[1]);sys.path.insert(0,sys.argv[1])
from layers.amount import apply_amount_layer
from pipeline_core import PipelineState,TokenAllocator
cases=[
 ('date_and_amount','Data urodzenia: 21.05.1979. Kwota 15 OOO,50 zł.',{'NUMER':['21.05.1979'],'KWOTA':['15 OOO,50 zł']}),
 ('two_amounts_emoji','😀 Kwota 15 OOO,50 zł; druga 15 OOO,50 PLN.',{'KWOTA':['15 OOO,50 zł','15 OOO,50 PLN']}),
 ('no_currency_dot','Kwota 15 OOO.5O bez waluty.',{'KWOTA':['15 OOO.5O']}),
 ('lowercase_o','Kwota 15 ooo,5 zł.',{'KWOTA':['15 ooo,5 zł']}),
]
for name,text,expected in cases:
 s=PipelineState(text=text,allocator=TokenAllocator());apply_amount_layer(s)
 rev=s.allocator.reverse_map
 for typ,vals in expected.items():
  actual=[v for k,v in rev.items() if k.startswith(typ+'_')]
  assert all(any(v in a for a in actual) for v in vals),(name,s.text,rev)
 restored=re.sub(r'\b(?:NUMER|KWOTA)_\d{3}(?!\d)',lambda m:rev[m.group()],s.text)
 assert restored==text,(name,restored,text)
 print(json.dumps({'case':name,'status':'PASS','output':s.text,'map':rev},ensure_ascii=False))

