// Independent reproducer for LYNX-GUARD-B F1-F3, exact audit b16be398803f298680c600f02bb68518ea297d94.
// Run on task checkout with Node 24: node tasks/LYNX-GUARD-B/round_01/tests/repro_r1.mjs
// Synthetic fixtures from the real isolated /preview, with ONLY upstream engine stubbed to supply final residues.
// Actual pipeline/Guard/PSE offsets; no private documents, credentials, services, storage or network used here.
import {coverWarning, applyCovers, pendingWarnings} from "../../../../frontend/src/screens/guardDecisions.ts";
const fixtures = [
  {
    "case": "unicode",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0005.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n📄📄📄📄📄📄📄📄📄📄📄📄 PESEL: 44051401359.",
    "warnings": [
      {
        "start": 127,
        "end": 138,
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
      }
    ]
  },
  {
    "case": "overlap",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0006.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPan Rogalik podpisał. Sprzedawca: Rogalik i Wspólnicy sp. k.",
    "warnings": [
      {
        "start": 111,
        "end": 118,
        "fragment": "Rogalik",
        "rules": [
          "R1"
        ],
        "reasons": [
          "Możliwe imię lub nazwisko, którego silnik nie zakrył"
        ],
        "rule": "R1",
        "level": "YELLOW",
        "id": "W001"
      },
      {
        "start": 141,
        "end": 167,
        "fragment": "Rogalik i Wspólnicy sp. k.",
        "rules": [
          "R5"
        ],
        "reasons": [
          "Możliwa nazwa firmy, której silnik nie zakrył",
          "Nazwa firmy z formą prawną"
        ],
        "rule": "R5",
        "level": "YELLOW",
        "id": "W002"
      }
    ]
  },
  {
    "case": "polish",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0007.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPan Kawa. Kawałek chleba.",
    "warnings": [
      {
        "start": 111,
        "end": 115,
        "fragment": "Kawa",
        "rules": [
          "R1"
        ],
        "reasons": [
          "Możliwe imię lub nazwisko, którego silnik nie zakrył"
        ],
        "rule": "R1",
        "level": "YELLOW",
        "id": "W001"
      }
    ]
  },
  {
    "case": "control",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0008.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPESEL: 44051401359.",
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
      }
    ]
  },
  {
    "case": "overlap_caps",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0009.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPan Rogalik podpisał. Sprzedawca: Rogalik i KOWALCZYK sp. k.",
    "warnings": [
      {
        "start": 111,
        "end": 118,
        "fragment": "Rogalik",
        "rules": [
          "R1"
        ],
        "reasons": [
          "Możliwe imię lub nazwisko, którego silnik nie zakrył"
        ],
        "rule": "R1",
        "level": "YELLOW",
        "id": "W001"
      },
      {
        "start": 141,
        "end": 167,
        "fragment": "Rogalik i KOWALCZYK sp. k.",
        "rules": [
          "R5"
        ],
        "reasons": [
          "Możliwa nazwa firmy, której silnik nie zakrył",
          "Nazwa firmy z formą prawną"
        ],
        "rule": "R5",
        "level": "YELLOW",
        "id": "W002"
      }
    ]
  },
  {
    "case": "unicode_one",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0010.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\n📄 PESEL: 44051401359.",
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
      }
    ]
  },
  {
    "case": "control_after",
    "text": "[Dokument pseudonimizowany. Kod sesji: PSE-2026-0011.\nW odpowiedzi przepisz ten kod jako pierwsze slowo.]\n\nPESEL: 44051401359. 📄📄📄📄📄📄📄📄📄📄📄📄",
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
      }
    ]
  }
];
let failures=0;
for (const r of fixtures) {
  const covers=coverWarning(r.text,r.warnings[0],{},[]);
  const output=applyCovers(r.text,covers);
  const pending=pendingWarnings(r.text,r.warnings,new Set(),covers);
  let ok;
  if(r.case.startsWith("unicode")) ok=output.includes("PESEL: NUMER_001.") && !output.includes("44051401359");
  else if(r.case.startsWith("overlap")) ok=pending.some(w=>w.rules.includes("R5"));
  else if(r.case==="polish") ok=output.includes("Kawałek") && !output.includes("NUMER_001łek") && !output.includes("OSOBA_001łek");
  else ok=!output.includes("44051401359");
  console.log(JSON.stringify({case:r.case,ok,pending:pending.length,output}));
  if(!ok)failures++;
}
console.log("failures="+failures);
process.exitCode=failures?1:0;
