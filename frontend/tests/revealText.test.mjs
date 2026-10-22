// [LYNX-MANUAL-REVEAL] Testy czystej logiki odkrywania wystąpień (syntetyki). Uruchamianie: node --test tests/revealText.test.mjs  (Node 24)
import { test } from "node:test";
import assert from "node:assert/strict";
import { finalText, segments, toggleReveal } from "../src/screens/revealText.ts";
import { applyCovers, coverWarning, pendingWarnings, warningKey } from "../src/screens/guardDecisions.ts";

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

// ── [LYNX-GUARD-B] decyzje Zakryj/Zostaw dla ostrzeżeń Guarda (guardDecisions.ts) ──
const w = (text, fragment, rule, nth = 0, id = "W001") => {
  const start = [...text.matchAll(new RegExp(fragment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g"))][nth].index;
  return { id, start, end: start + fragment.length, fragment, rule, level: "YELLOW", reasons: ["r"] };
};

test("bez decyzji wszystkie ostrzeżenia blokują; Zostaw i Zakryj rozstrzygają po jednym", () => {
  const t = "Świadek Śludkowskiego oraz Kawa zlecił wysyłkę.";
  const ws = [w(t, "Śludkowskiego", "R1"), w(t, "Kawa", "R1", 0, "W002")];
  assert.equal(pendingWarnings(t, ws, new Set(), []).length, 2);
  const kept = new Set([warningKey(t, ws[1])]);
  assert.deepEqual(pendingWarnings(t, ws, kept, []).map(x => x.id), ["W001"]);
  const covers = coverWarning(t, ws[0], {}, []);
  assert.equal(pendingWarnings(t, ws, kept, covers).length, 0);
  assert.equal(applyCovers(t, covers), "Świadek OSOBA_001 oraz Kawa zlecił wysyłkę.");
});

test("Zakryj: wszystkie takie same wystąpienia jednym tokenem, kolejny wolny numer typu", () => {
  const t = "Pan Rogalik przyszedł. Rogalik podpisał, OSOBA_001 też.";
  const covers = coverWarning(t, w(t, "Rogalik", "R1"), { OSOBA_001: "Jan Nowak" }, []);
  assert.equal(applyCovers(t, covers), "Pan OSOBA_002 przyszedł. OSOBA_002 podpisał, OSOBA_001 też.");
});

test("Zakryj wartości z mapy (inna wielkość liter) używa jej tokenu; Przywróć daje postać z mapy", () => {
  const t = "Pismo od OSOBA_001, w stopce KOWALSKI.";
  const map = { OSOBA_001: "Kowalski" };
  const covers = coverWarning(t, { ...w(t, "KOWALSKI", "MAP_LEAK"), level: "RED" }, map, []);
  const base = applyCovers(t, covers);
  assert.equal(base, "Pismo od OSOBA_001, w stopce OSOBA_001.");
  assert.equal(finalText(base, map, new Set([base.lastIndexOf("OSOBA_001")])), "Pismo od OSOBA_001, w stopce Kowalski.");
});

test("Zakryj resztki numeru tylko we wskazanym miejscu (nie każde „7” w dokumencie)", () => {
  const t = "NIP: 7 NUMER_021, art. 7 ustawy.";
  const covers = coverWarning(t, w(t, "7", "R3"), {}, []);
  assert.equal(applyCovers(t, covers), "NIP: NUMER_001 NUMER_021, art. 7 ustawy.");
});

test("Zakryj słowa: całe słowa, bez wnętrza dłuższych słów i tokenów", () => {
  const t = "Kawa zlecił. Kawalerka i Kawa.";
  const covers = coverWarning(t, w(t, "Kawa", "R1"), {}, []);
  assert.equal(applyCovers(t, covers), "OSOBA_001 zlecił. Kawalerka i OSOBA_001.");
});

test("klucz Zostaw przeżywa przenumerowanie tokenów po ponownym przeliczeniu (U2)", () => {
  const a = "Umowa z OSOBA_001 oraz Kawa zlecił.";
  const b = "Umowa z OSOBA_004 oraz Kawa zlecił.";
  assert.equal(warningKey(a, w(a, "Kawa", "R1")), warningKey(b, w(b, "Kawa", "R1")));
  const c = "Inny dokument: Kawa zlecił.";
  assert.notEqual(warningKey(a, w(a, "Kawa", "R1")), warningKey(c, w(c, "Kawa", "R1")));
});

test("Zostaw tylko wskazane wystąpienie: to samo słowo w innym kontekście nadal czeka", () => {
  const t = "Kawa zlecił paczkę. Wczoraj Kawa podpisał umowę.";
  const ws = [w(t, "Kawa", "R1", 0), w(t, "Kawa", "R1", 1, "W002")];
  const kept = new Set([warningKey(t, ws[0])]);
  assert.deepEqual(pendingWarnings(t, ws, kept, []).map(x => x.id), ["W002"]);
});

test("słownik biura: słowa i dłuższe identyfikatory tak; cyfra, inicjał, rok nie", async () => {
  const { rememberable } = await import("../src/screens/guardDecisions.ts");
  for (const f of ["Śludkowskiego", "Biuro Rachunkowe RACHMISTRZ", "AB/123/45"]) assert.equal(rememberable(f), true, f);
  for (const f of ["7", "S.", "2019", "128/7"]) assert.equal(rememberable(f), false, f);
});
