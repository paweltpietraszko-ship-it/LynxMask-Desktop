// [LYNX-MANUAL-REVEAL] Testy czystej logiki odkrywania wystąpień (syntetyki). Uruchamianie: node --test tests/revealText.test.mjs  (Node 24)
import { test } from "node:test";
import assert from "node:assert/strict";
import { finalText, segments, toggleReveal } from "../src/screens/revealText.ts";

const MAP = { OSOBA_033: "Róża", OSOBA_001: "Anna Malina", NUMER_001: "44051401359" };
const ROSE = "SESJA_PSE-001\n01. OSOBA_033 zakwitła rano na rabacie.\n02. Pani OSOBA_033 odebrała dokument.";
const at = (text, token, nth = 0) => [...text.matchAll(new RegExp(token, "g"))][nth].index;

test("Róża: odkryte tylko kliknięte wystąpienie, drugie zostaje zakryte", () => {
  const r = toggleReveal(new Set(), at(ROSE, "OSOBA_033"), "OSOBA_033", MAP);
  assert.equal(finalText(ROSE, MAP, r),
    "SESJA_PSE-001\n01. Róża zakwitła rano na rabacie.\n02. Pani OSOBA_033 odebrała dokument.");
});

test("trzy wystąpienia: niezależne odkrycia i cofnięcie jednego", () => {
  const t = "OSOBA_033, OSOBA_033 i OSOBA_033.";
  let r = new Set();
  for (const n of [0, 2]) r = toggleReveal(r, at(t, "OSOBA_033", n), "OSOBA_033", MAP);
  assert.equal(finalText(t, MAP, r), "Róża, OSOBA_033 i Róża.");
  r = toggleReveal(r, at(t, "OSOBA_033", 0), "OSOBA_033", MAP);
  assert.equal(finalText(t, MAP, r), "OSOBA_033, OSOBA_033 i Róża.");
});

test("wielowyrazowy token odkrywany w całości; pozostałe tokeny i interpunkcja bez zmian", () => {
  const t = "Pani OSOBA_001, PESEL NUMER_001.";
  const r = toggleReveal(new Set(), at(t, "OSOBA_001"), "OSOBA_001", MAP);
  assert.equal(finalText(t, MAP, r), "Pani Anna Malina, PESEL NUMER_001.");
});

test("brak wartości w mapie: nie odkrywa", () => {
  const t = "Firma FIRMA_007 podpisała.";
  const r = toggleReveal(new Set(), at(t, "FIRMA_007"), "FIRMA_007", MAP);
  assert.equal(r.size, 0);
  assert.equal(finalText(t, MAP, r), t);
});

test("bez odkryć tekst = baza; segmenty składają się z powrotem w bazę", () => {
  assert.equal(finalText(ROSE, MAP, new Set()), ROSE);
  assert.equal(segments(ROSE, MAP, new Set()).map(s => s.text).join(""), ROSE);
  assert.deepEqual(segments(ROSE, MAP, new Set()).filter(s => s.token).map(s => s.at),
    [at(ROSE, "OSOBA_033", 0), at(ROSE, "OSOBA_033", 1)]);
});

test("token z cyfrą za numerem (S2) nie jest tokenem", () => {
  assert.equal(segments("OSOBA_0331 x", MAP, new Set()).filter(s => s.token).length, 0);
});
