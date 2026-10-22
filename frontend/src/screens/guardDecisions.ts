// guardDecisions.ts — [LYNX-GUARD-B] decyzje Zakryj/Zostaw dla ostrzeżeń Guarda (S4 22.10, brief LYNX-GUARD-RESIDUE v2).
// Ostrzeżenia mają pozycje w niezmiennym tekście bazowym (anonymized_preview). Zakryj = token wstawiony w ten tekst
// (wszystkie takie same wystąpienia, wartość z mapy → ten sam token); Zostaw = świadoma akceptacja wystąpienia,
// pamiętana po fragmencie i otoczeniu (U2), tylko w pamięci bieżącego dokumentu — nie trafia do allowlisty ani na dysk.
import { TOKEN_RE } from "./revealText.ts";  // rozszerzenie: testy node --test bez bundlera

export interface GuardWarning {
  id: string; start: number; end: number; fragment: string; rule: string; level: string; reasons: string[];
  utf16?: true;  // pozycje już w jednostkach JS — ustawia wyłącznie at16/toUtf16 (bez znacznika = punkty kodowe z silnika)
}
export interface Cover { start: number; end: number; token: string; original: string }

const CTX = 24;
const norm = (s: string) => s.replace(TOKEN_RE, t => t.replace(/_\d{3}$/, "")).toLowerCase();

/** Klucz decyzji Zostaw: fragment + otoczenie (numery tokenów pominięte — przeżywa ponowne przeliczenie). */
export function warningKey(base: string, raw: GuardWarning): string {
  const w = at16(base, raw);
  return [w.fragment.toLowerCase(), norm(base.slice(Math.max(0, w.start - CTX), w.start)), norm(base.slice(w.end, w.end + CTX))]
    .join("\u0001");
}

/** Tekst bazowy z zakrytymi fragmentami (pozycje bazowe, rozłączne). */
export function applyCovers(base: string, covers: readonly Cover[]): string {
  let out = "", last = 0;
  for (const c of [...covers].sort((a, b) => a.start - b.start)) {
    out += base.slice(last, c.start) + c.token;
    last = c.end;
  }
  return out + base.slice(last);
}

function coverType(w: GuardWarning): string {
  if (w.rule === "R5") return "FIRMA";
  if (w.rule === "R1" || w.rule === "R2") return "OSOBA";
  if (w.rule === "R3" && /\d\d\s?-\s?\d/.test(w.fragment)) return "ADRES";
  return "NUMER";
}

/** Typ tokenu dla Zakryj: typ wartości z mapy albo wg reguły ostrzeżenia. */
export function coverTypeFor(w: GuardWarning, map: Record<string, string>): string {
  const low = w.fragment.toLowerCase();
  const known = Object.entries(map).find(([, v]) => v.toLowerCase() === low)?.[0];
  return known ? known.split("_")[0] : coverType(w);
}

/** Czy Zakryj może trafić do słownika biura: słowo/nazwa (≥3 litery) albo dłuższy identyfikator (≥5 znaków, nie sam rok).
 *  Pojedyncze cyfry, inicjały i lata tylko w tym dokumencie — w słowniku zakrywałyby je w każdym przyszłym piśmie. */
export function rememberable(fragment: string): boolean {
  const f = fragment.trim();
  return /\p{L}{3,}/u.test(f) || (f.replace(/[^\p{L}\d]/gu, "").length >= 5 && /\d/.test(f) && !/^(19|20)\d\d$/.test(f));
}

/** Zakryj: słowo/nazwę we wszystkich wystąpieniach (bez wielkości liter, całe słowa) poza tokenami i zakryciami — jednym tokenem;
 *  wartość obecna w mapie dostaje jej token (jedna wartość = jeden token), inaczej kolejny wolny numer typu. */
export function coverWarning(base: string, raw: GuardWarning, map: Record<string, string>, covers: readonly Cover[]): Cover[] {
  const w = at16(base, raw);  // F1: także gdy wołający poda pozycje z silnika bez przeliczenia
  const low = w.fragment.toLowerCase();
  const known = Object.entries(map).find(([, v]) => v.toLowerCase() === low)?.[0];
  const type = coverTypeFor(w, map);
  const used = new Set([...Object.keys(map), ...covers.map(c => c.token)]);
  let n = 1;
  while (!known && used.has(`${type}_${String(n).padStart(3, "0")}`)) n++;
  const token = known ?? `${type}_${String(n).padStart(3, "0")}`;
  // Codex F2: wskazane miejsce zakrywamy w całości — wcześniejsze zakrycia w jego środku („Rogalik” w „Rogalik i KOWALCZYK sp. k.”)
  // zastępuje jeden token całej wartości
  const kept = covers.filter(c => !(c.start >= w.start && c.end <= w.end));
  const busy: [number, number][] = [...[...base.matchAll(TOKEN_RE)].map(m => [m.index!, m.index! + m[0].length] as [number, number]),
    ...kept.map(c => [c.start, c.end] as [number, number])];
  const added: Cover[] = [];
  const hay = base.toLowerCase();
  const everywhere = /\p{L}{3,}/u.test(w.fragment);  // słowa/nazwy: wszędzie; numery i krótkie resztki: tylko to miejsce
  for (let at = everywhere ? hay.indexOf(low) : w.start; at >= 0 && low; at = everywhere ? hay.indexOf(low, at + low.length) : -1) {
    const end = at + low.length;
    if (busy.some(([s, e]) => s < end && at < e)) continue;
    if (at !== w.start && (WORD.test(base[at - 1] ?? "") || WORD.test(base[end] ?? ""))) continue;  // tylko całe słowa (F3)
    added.push({ start: at, end, token, original: w.fragment });
    busy.push([at, end]);
  }
  return [...kept, ...added];
}

const WORD = /[\p{L}\p{N}_]/u;  // znak słowa także dla polskich liter (Codex F3: „Kawałek”)

/** Ostrzeżenia bez decyzji: nie zostawione i nie zakryte W CAŁOŚCI — częściowe zakrycie (inna pozycja, wspólne słowo) nie
 *  rozstrzyga ostrzeżenia, dopóki w jego zakresie zostaje jawna litera lub cyfra (Codex F2). */
export function pendingWarnings(base: string, ws: readonly GuardWarning[], kept: ReadonlySet<string>,
                                covers: readonly Cover[]): GuardWarning[] {
  const covered = (raw: GuardWarning) => {
    const w = at16(base, raw);
    for (let at = w.start; at < w.end; at++)
      if (WORD.test(base[at]) && !covers.some(c => c.start <= at && at < c.end)) return false;
    return true;
  };
  return ws.filter(w => !kept.has(warningKey(base, w)) && !covered(w));
}

/** Pozycje z silnika (punkty kodowe Pythona) → indeksy JS (UTF-16) ze znacznikiem `utf16`, żeby znaki spoza BMP (np. emoji) nie przesuwały
 *  maskowania (Codex F1). Format tokenów i API bez zmian — przeliczenie raz, po stronie okna. */
export function toUtf16(base: string, ws: readonly GuardWarning[]): GuardWarning[] {
  return ws.map(w => at16(base, w));
}

/** Jedno ostrzeżenie: jednostki rozpoznawane po znaczniku `utf16`, nie po treści (Codex F1 r2: identyczne wartości —
 *  pozycja z silnika mogła trafić w inne wystąpienie). Bez znacznika = punkty kodowe → przeliczenie; ze znacznikiem bez zmian. */
function at16(base: string, w: GuardWarning): GuardWarning {
  if (w.utf16) return w;
  const cps = [...base];
  const start = cps.slice(0, w.start).join("").length;
  return { ...w, start, end: start + cps.slice(w.start, w.end).join("").length, utf16: true };
}
