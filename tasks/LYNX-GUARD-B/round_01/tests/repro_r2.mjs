// LYNX-GUARD-B r2 — retained F1 duplicate-offset counterexample.
// Node 24: node tasks/LYNX-GUARD-B/round_01/tests/repro_r2.mjs
// Real isolated /preview JSON on exact 43dafa4, upstream engine stubbed ONLY to supply synthetic final residues.
// No network, profile, archive or private documents used by this reproducer.
import {toUtf16,warningKey,coverWarning,applyCovers,pendingWarnings}
  from "../../../../frontend/src/screens/guardDecisions.ts";
const fixtures=[
  {
    "emoji": 0,
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0001.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPESEL: 44051401359; PESEL: 44051401359.",
    "warnings": [
      {
        "start": 114,
        "end": 125,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W001"
      },
      {
        "start": 134,
        "end": 145,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W002"
      }
    ]
  },
  {
    "emoji": 1,
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0002.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n📄 PESEL: 44051401359; PESEL: 44051401359.",
    "warnings": [
      {
        "start": 116,
        "end": 127,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W001"
      },
      {
        "start": 136,
        "end": 147,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W002"
      }
    ]
  },
  {
    "emoji": 20,
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0003.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄 PESEL: 44051401359; PESEL: 44051401359.",
    "warnings": [
      {
        "start": 135,
        "end": 146,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W001"
      },
      {
        "start": 155,
        "end": 166,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W002"
      }
    ]
  },
  {
    "emoji": 21,
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0004.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄📄 PESEL: 44051401359; PESEL: 44051401359.",
    "warnings": [
      {
        "start": 136,
        "end": 147,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W001"
      },
      {
        "start": 156,
        "end": 167,
        "fragment": "44051401359",
        "rules": [
          "HIGH PESEL",
          "R4"
        ],
        "reasons": [
          "Wygląda na numer identyfikacyjny",
          "Numer lub data w kontekście danych identyfikujących"
        ],
        "rule": "HIGH PESEL",
        "level": "RED",
        "id": "W002"
      }
    ]
  }
];
let failures=0;
for(const r of fixtures){
  const warnings=toUtf16(r.text,r.warnings);
  // Panel rows group the same kind/level/fragment x2. The normal Maskuj action marks both keys.
  const covered=new Set(warnings.map(w=>warningKey(r.text,w)));
  const covers=warnings.filter(w=>covered.has(warningKey(r.text,w)))
    .reduce((cs,w)=>coverWarning(r.text,w,{},cs),[]);
  const output=applyCovers(r.text,covers);
  const pending=pendingWarnings(r.text,warnings,new Set(),covers);
  const ok=!output.includes("44051401359");
  console.log(JSON.stringify({emoji:r.emoji,ok,starts:warnings.map(w=>w.start),pending:pending.length,output}));
  if(!ok)failures++;
}
console.log("failures="+failures);
process.exitCode=failures?1:0;
