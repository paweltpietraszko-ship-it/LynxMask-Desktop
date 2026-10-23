// revealText.ts — [LYNX-MANUAL-REVEAL] ręczne odkrycie pojedynczego wystąpienia tokenu w podglądzie (jak Mobile).
// Odkrycie to decyzja użytkownika po zakończonej kontroli Guarda (S4); Guard nie ocenia go ponownie.
// Wystąpienie = pozycja tokenu w niezmiennym tekście bazowym (anonymized_preview), więc dwa identyczne
// tokeny są niezależne; tekst końcowy zawsze liczony od bazy — bez kolejnych zamian i przesunięć offsetów.

export const TOKEN_RE = /\b[A-Z][A-Z_]+_\d{3}(?!\d)/g;  // S2: (?!\d) — LYNX-TOKEN-RE-SPEC

export interface Segment {
  text:     string;
  at?:      number;   // pozycja tokenu w tekście bazowym (tylko dla tokenów)
  token?:   string;
  revealed?: boolean;
}

/** Tekst bazowy pocięty na zwykły tekst i tokeny; odkryte wystąpienia mają wartość z mapy. */
export function segments(base: string, map: Record<string, string>, revealed: ReadonlySet<number>): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of base.matchAll(TOKEN_RE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ text: base.slice(last, at) });
    const open = revealed.has(at) && map[m[0]] !== undefined;
    out.push({ text: open ? map[m[0]] : m[0], at, token: m[0], revealed: open });
    last = at + m[0].length;
  }
  if (last < base.length) out.push({ text: base.slice(last) });
  return out;
}

/** Jedna kanoniczna wartość dla ekranu, „Kopiuj tekst” i zapisu do archiwum. */
export function finalText(base: string, map: Record<string, string>, revealed: ReadonlySet<number>): string {
  return segments(base, map, revealed).map(s => s.text).join("");
}

/** Przełącza odkrycie jednego wystąpienia; bez wartości w mapie nie odkrywa (zwraca ten sam zbiór). */
export function toggleReveal(revealed: ReadonlySet<number>, at: number, token: string,
                             map: Record<string, string>): Set<number> {
  const next = new Set(revealed);
  if (next.has(at)) next.delete(at);
  else if (map[token] !== undefined) next.add(at);
  return next;
}
