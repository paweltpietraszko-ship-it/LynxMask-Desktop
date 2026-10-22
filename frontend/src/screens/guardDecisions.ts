// guardDecisions.ts — [LYNX-GUARD-B] decyzje Zakryj/Zostaw dla ostrzeżeń Guarda (S4 22.10, brief LYNX-GUARD-RESIDUE v2).
// Ostrzeżenia mają pozycje w niezmiennym tekście bazowym (anonymized_preview). Zakryj = token wstawiony w ten tekst
// (wszystkie takie same wystąpienia, wartość z mapy → ten sam token); Zostaw = świadoma akceptacja wystąpienia,
// pamiętana po fragmencie i otoczeniu (U2), tylko w pamięci bieżącego dokumentu — nie trafia do allowlisty ani na dysk.
import { TOKEN_RE } from "./revealText.ts";  // rozszerzenie: testy node --test bez bundlera

export interface GuardWarning {
  id: string; start: number; end: number; fragment: string; rule: string; level: string; reasons: string[];
}
export interface Cover { start: number; end: number; token: string; original: string }

const CTX = 24;
const norm = (s: string) => s.replace(TOKEN_RE, t => t.replace(/_\d{3}$/, "")).toLowerCase();

/** Klucz decyzji Zostaw: fragment + otoczenie (numery tokenów pominięte — przeżywa ponowne przeliczenie). */
export function warningKey(base: string, w: GuardWarning): string {
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
export function coverWarning(base: string, w: GuardWarning, map: Record<string, string>, covers: readonly Cover[]): Cover[] {
  const low = w.fragment.toLowerCase();
  const known = Object.entries(map).find(([, v]) => v.toLowerCase() === low)?.[0];
  const type = coverTypeFor(w, map);
  const used = new Set([...Object.keys(map), ...covers.map(c => c.token)]);
  let n = 1;
  while (!known && used.has(`${type}_${String(n).padStart(3, "0")}`)) n++;
  const token = known ?? `${type}_${String(n).padStart(3, "0")}`;
  const busy: [number, number][] = [...[...base.matchAll(TOKEN_RE)].map(m => [m.index!, m.index! + m[0].length] as [number, number]),
    ...covers.map(c => [c.start, c.end] as [number, number])];
  const added: Cover[] = [];
  const hay = base.toLowerCase();
  const everywhere = /\p{L}{3,}/u.test(w.fragment);  // słowa/nazwy: wszędzie; numery i krótkie resztki: tylko to miejsce
  for (let at = everywhere ? hay.indexOf(low) : w.start; at >= 0 && low; at = everywhere ? hay.indexOf(low, at + low.length) : -1) {
    const end = at + low.length;
    if (busy.some(([s, e]) => s < end && at < e)) continue;
    if (at !== w.start && (/\w/.test(base[at - 1] ?? "") || /\w/.test(base[end] ?? ""))) continue;  // tylko całe słowa
    added.push({ start: at, end, token, original: w.fragment });
    busy.push([at, end]);
  }
  return [...covers, ...added];
}

/** Ostrzeżenia bez decyzji: nie zakryte i nie zostawione. */
export function pendingWarnings(base: string, ws: readonly GuardWarning[], kept: ReadonlySet<string>,
                                covers: readonly Cover[]): GuardWarning[] {
  return ws.filter(w => !kept.has(warningKey(base, w)) && !covers.some(c => c.start < w.end && w.start < c.end));
}
