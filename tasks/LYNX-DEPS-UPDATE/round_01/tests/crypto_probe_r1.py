"""Synthetic cross-version map compatibility; no user profile or user keys.
Run with old/new interpreter: crypto_probe_r1.py BACKEND OUTPUT old|new|verify-old
"""
import sys
from pathlib import Path
backend, output, mode = sys.argv[1:]
sys.path.insert(0, backend)
from anonymizer_crypto import encrypt_map, decrypt_map, add_mac_to_entry, verify_entry
out = Path(output)
out.mkdir(parents=True, exist_ok=True)
key, mac = bytes(range(32)), bytes(range(32,64))  # public, synthetic test keys only
data = {'OSOBA_001': add_mac_to_entry('OSOBA_001', {'base':'Żaneta Kowalska','forms':['Żanety Kowalskiej']}, mac)}
if mode in ('old','new'):
    (out / (mode+'.enc')).write_bytes(encrypt_map(data,key))
if mode in ('new','verify-old'):
    source = 'old' if mode == 'new' else 'new'
    got = decrypt_map((out/(source+'.enc')).read_bytes(),key)
    assert got == data
    assert verify_entry('OSOBA_001',got['OSOBA_001'],mac)
    print(source+'->'+('new' if mode=='new' else 'old')+': content, Unicode and MAC OK')
