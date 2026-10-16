"""Reprodukcje Output Guard (BUG-IBAN-LETTERS, BUG-NIP-LEAK). Dane syntetyczne."""
import sys
import os
import logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from output_guard import guard_output, GuardMode
cases = [
 ("GB IBAN spacje",  "Konto: GB29 NWBK 6016 1331 9268 19 dziękuję"),
 ("GB IBAN ciągły",  "Konto: GB29NWBK60161331926819 dziękuję"),
 ("IE IBAN",         "Konto: IE29 AIBK 9311 5212 3456 78 ok"),
 ("MT IBAN",         "Konto: MT84 MALT 0110 0001 2345 MTLC AST0 01S ok"),
 ("PL IBAN",         "Konto: PL61 1090 1014 0000 0712 1981 2874 ok"),
 ("NIP PL ze spacjami (FP?)", "NIP: PL65 51 97 93 13 ok"),
 ("NIP 3-3-2-2",     "NIP 512-345-67-89 ok"),
 ("NIP 3-2-2-3",     "NIP 512-34-56-789 ok"),
 ("NIP 3-2-2-3 sp.", "NIP 512 34 56 789 ok"),
 ("lowercase iban",  "konto gb29 nwbk 6016 1331 9268 19"),
]
for name, t in cases:
    r = guard_output(t, GuardMode.REDACT)
    print(f"{name:26} blocked={r.blocked!s:5} reasons={[x.split('«')[0].strip() for x in r.reasons]} redacted={r.redacted_text!r}")
