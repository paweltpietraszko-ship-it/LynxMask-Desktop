"""Śledzi tekst po każdej warstwie pipeline_new (NER zmockowany lub prawdziwy).
Użycie: python audyt/trace_layers.py "tekst" [--ner]"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from unittest.mock import patch
import pipeline_new as P
import layers.ner_adapter as N

def trace(text, real_ner=False):
    state = P.PipelineState(text=text, allocator=P.TokenAllocator())
    steps = [("ocr_normalizer", P.apply_ocr_normalizer, ()), ("identity", P.apply_identity_layer, ()),
             ("credentials", P.apply_credentials_layer, ()), ("financial", P.apply_financial_layer, ()),
             ("legal", P.apply_legal_layer, ()), ("numeric", P.apply_numeric_layer, ()),
             ("contact", P.apply_contact_layer, ()), ("amount", P.apply_amount_layer, ()),
             ("verbal_amount", P.apply_verbal_amount_layer, ()), ("extract_ner", None, ()),
             ("address", P.apply_address_layer, ()), ("ner", P.apply_ner_layer, ({},)),
             ("institution", P.apply_institution_layer, ()), ("fallback", P.apply_fallback_layer, ())]
    prev = text
    for name, fn, args in steps:
        if name == "extract_ner":
            P.extract_ner_results(state, {})
            continue
        P._apply(state, fn, *args)
        if state.text != prev:
            print(f"[{name:14}] {state.text!r}")
            prev = state.text
    print("reverse_map:", state.allocator.reverse_map)
    return state

if __name__ == "__main__":
    real = "--ner" in sys.argv
    txt = [a for a in sys.argv[1:] if a != "--ner"][0]
    if real:
        trace(txt, True)
    else:
        with patch.object(N, "process_ner", return_value=({}, {})):
            trace(txt)
