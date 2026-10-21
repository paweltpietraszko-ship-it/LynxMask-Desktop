"""Read-only observation of the spaCy candidate filter; synthetic personal name.
Usage: python repro_bill.py <absolute backend path on audited SHA>
Full /preview observation retained in tests_r3.txt and isolated audit artifacts.
"""
import json
import sys
from types import SimpleNamespace

sys.path.insert(0,sys.argv[1])
import ner_layer

result={'candidate':'Bill','kept':[e.text for e in ner_layer._filter_institutions([SimpleNamespace(text='Bill',label='OSOBA')])]}
try:
    import osoba_not_person as onp
    result.update(in_person_forms='bill' in ner_layer._PERSON_FORMS,in_white_lists='bill' in onp.WHITE_LISTS,in_denylist='bill' in onp.OSOBA_DENYLIST)
except ModuleNotFoundError:
    result['new_filter_module']='absent on baseline'
print(json.dumps(result,ensure_ascii=True,indent=2))

