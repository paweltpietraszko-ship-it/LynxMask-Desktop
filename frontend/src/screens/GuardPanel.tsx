// GuardPanel.tsx — [LYNX-GUARD-B] ostrzeżenia Guarda z decyzją przy każdej pozycji (S4 22.10), układ jak Mobile (Paweł 22.10):
// czerwona sekcja „możliwy wyciek” (RED) i żółta „do sprawdzenia” (YELLOW); pozycja = rodzaj + sama wartość; Maskuj / Zostaw jawne.
// To samo słowo w sekcji = jeden wiersz „×N” (decyzja dotyczy wskazanych wystąpień). Stała wysokość z przewijaniem (U5).
import { useState } from "react";
import { T } from "../theme";
import { GuardWarning, warningKey } from "./guardDecisions";
import { addAllow, removeAllow, ruleLabel, rulesOf } from "./guardAllowlist";

interface Props {
  base:      string;                    // tekst bazowy (pozycje ostrzeżeń)
  warnings:  readonly GuardWarning[];   // wszystkie ostrzeżenia bieżącego wyniku
  pending:   readonly GuardWarning[];   // bez decyzji
  kept:      ReadonlySet<string>;
  onCover:   (ws: GuardWarning[]) => void;
  onKeep:    (keys: string[], keep: boolean) => void;
  remember?: boolean;                   // Maskuj → słownik biura (brak = tryb bez profilu, np. Express)
  onRemember?: (on: boolean) => void;
  allowToken?: string;                  // [S5] „Zawsze jawne” (brak = Express, bez przycisku)
}

const REMEMBER_HELP = "Zamaskowane słowa trafią do słownika biura, więc w następnych dokumentach program zamaskuje je sam. "
  + "Odznacz, jeśli maskujesz tylko w tym dokumencie. Pojedyncze cyfry, inicjały i lata maskujemy tylko tutaj.";

const ALWAYS_HELP = "Program nie będzie pytał o ten fragment w następnych dokumentach. Lista jest zaszyfrowana na tym "
  + "komputerze; wpis usuniesz w Ustawieniach → Wyjątki Guard.";

const kind = (w: GuardWarning) => ruleLabel(w.rule);

interface Row { kind: string; fragment: string; items: GuardWarning[]; red: boolean }

function rows(ws: readonly GuardWarning[]): Row[] {
  const out = new Map<string, Row>();
  for (const w of ws) {
    const k = `${w.level}|${kind(w)}|${w.fragment.toLowerCase()}`;
    const r = out.get(k) ?? { kind: kind(w), fragment: w.fragment, items: [], red: w.level === "RED" };
    r.items.push(w);
    out.set(k, r);
  }
  return [...out.values()];
}

const HELP = { display: "inline-flex", alignItems: "center", justifyContent: "center", width: 16, height: 16, borderRadius: 8,
  border: `1px solid ${T.border}`, fontSize: 11, color: T.textMuted, cursor: "help", flexShrink: 0 } as const;

const btn = (main: boolean, color: string) => ({
  fontSize: 14, padding: main ? "5px 18px" : "5px 10px", background: main ? T.surface : "none",
  border: main ? `1px solid ${color}` : "none", borderRadius: 6, color: main ? color : T.textSecondary,
  cursor: "pointer", flexShrink: 0,
});

export default function GuardPanel({ base, warnings, pending, kept, onCover, onKeep, remember, onRemember, allowToken }: Props) {
  const [always, setAlways] = useState<Map<string, { value: string; rules: string[] }>>(new Map());
  const [allowError, setAllowError] = useState("");
  if (warnings.length === 0) return null;
  // [S5] Zawsze jawne: zapis (fragment, każda reguła) → jak Zostaw; cofnij usuwa te same pary. Błąd = pozycja bez decyzji.
  const setAlwaysFor = async (keys: string[], r: Row, on: boolean) => {
    const e = always.get(keys[0]) ?? { value: r.fragment.trim(), rules: [...new Set(r.items.flatMap(rulesOf))] };
    try {
      if (on) await addAllow(allowToken!, e.value, e.rules);
      else for (const rule of e.rules) await removeAllow(allowToken!, { value: e.value, rule });
    } catch (err) { setAllowError(String((err as Error).message)); return; }
    setAllowError("");
    setAlways(m => { const n = new Map(m); if (on) n.set(keys[0], e); else n.delete(keys[0]); return n; });
    onKeep(keys, on);
  };
  const open = new Set(pending.map(w => w.id));
  const shown = rows(warnings.filter(w => open.has(w.id) || kept.has(warningKey(base, w))));
  const done = pending.length === 0;
  const section = (red: boolean) => {
    const rs = shown.filter(r => r.red === red);
    if (rs.length === 0) return null;
    const color = red ? T.red : T.amber;
    return (
      <div style={{ marginBottom: 10 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color, margin: "4px 0" }}>
          {red ? "⚠ Możliwy wyciek — zamaskuj albo zostaw jawne" : "Do sprawdzenia"}
        </div>
        {rs.map(r => {
          const keys = r.items.map(w => warningKey(base, w)), isKept = keys.every(k => kept.has(k));
          const ctx = r.items.map(w => "…" + base.slice(Math.max(0, w.start - 40), w.end + 40).replace(/\s+/g, " ") + "…").join("\n");
          return (
            <div key={keys[0]} title={ctx} style={{ display: "flex", alignItems: "center", gap: 12, padding: "6px 0",
              borderTop: `1px solid ${T.border}` }}>
              <div style={{ flex: 1, minWidth: 0, fontSize: 15, color: isKept ? T.textMuted : T.textPrimary,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                <span style={{ color: T.textMuted }}>{r.kind} — </span>
                <b>{r.fragment}</b>{r.items.length > 1 && <span style={{ color: T.textMuted }}> ×{r.items.length}</span>}
              </div>
              {isKept && always.has(keys[0])
                ? <button style={btn(false, color)} onClick={() => setAlwaysFor(keys, r, false)}>Zawsze jawne — cofnij</button>
                : isKept
                ? <button style={btn(false, color)} onClick={() => onKeep(keys, false)}>Zostawione jawne — cofnij</button>
                : <>
                    <button style={btn(true, color)} onClick={() => onCover(r.items)}>Maskuj</button>
                    <button style={btn(false, color)} onClick={() => onKeep(keys, true)}>Zostaw jawne</button>
                    {allowToken && !r.red && <>
                      <button style={btn(false, color)} onClick={() => setAlwaysFor(keys, r, true)}>Zawsze jawne</button>
                      <span title={ALWAYS_HELP} aria-label={ALWAYS_HELP} style={HELP}>?</span>
                    </>}
                  </>}
            </div>
          );
        })}
      </div>
    );
  };
  return (
    <div style={{
      background: T.surface, border: `1px solid ${done ? T.border : pending.some(w => w.level === "RED") ? T.redBorder : T.amber}`,
      borderRadius: 8, marginTop: 12, flexShrink: 0, display: "flex", flexDirection: "column", maxHeight: "38vh",
    }}>
      <div style={{ padding: "10px 16px 4px", fontSize: 14, color: T.textSecondary, flexShrink: 0 }}>
        {done ? "✓ Wszystko sprawdzone — możesz zapisać, skopiować lub wyeksportować dokument."
          : `Zostało do decyzji: ${pending.length}. Zapis, kopiowanie i eksport będą dostępne po decyzji przy każdej pozycji. `
            + "Zostaw jawne = tylko w tym dokumencie."}
        {onRemember && !done && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={!!remember} onChange={e => onRemember(e.target.checked)} />
            Zapamiętaj zamaskowane w słowniku biura
            <span title={REMEMBER_HELP} aria-label={REMEMBER_HELP} style={HELP}>?</span>
          </label>
        )}
        {allowError && <div style={{ color: T.red, fontSize: 13, marginTop: 6 }}>{allowError}</div>}
      </div>
      <div style={{ overflowY: "auto", minHeight: 0, padding: "4px 16px 8px" }}>
        {section(true)}
        {section(false)}
      </div>
    </div>
  );
}
