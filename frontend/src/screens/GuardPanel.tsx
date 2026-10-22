// GuardPanel.tsx — [LYNX-GUARD-B] lista ostrzeżeń Guarda z decyzją przy każdej pozycji (S4 22.10).
// Stała wysokość z własnym przewijaniem (U5: okno jest sztywne, lista na początku pracy bywa długa); licznik zawsze widoczny.
import { T } from "../theme";
import { GuardWarning, warningKey } from "./guardDecisions";

interface Props {
  base:      string;                    // tekst bazowy (pozycje ostrzeżeń)
  warnings:  readonly GuardWarning[];   // wszystkie ostrzeżenia bieżącego wyniku
  pending:   readonly GuardWarning[];   // bez decyzji
  kept:      ReadonlySet<string>;
  onCover:   (w: GuardWarning) => void;
  onKeep:    (key: string, keep: boolean) => void;
}

const btn = (color: string, border: string) => ({
  fontSize: 13, padding: "3px 10px", background: T.surface, border: `1px solid ${border}`,
  borderRadius: 4, color, cursor: "pointer", flexShrink: 0,
});

export default function GuardPanel({ base, warnings, pending, kept, onCover, onKeep }: Props) {
  if (warnings.length === 0) return null;
  const open = new Set(pending.map(w => w.id));
  const shown = warnings.filter(w => open.has(w.id) || kept.has(warningKey(base, w)));
  const done = pending.length === 0;
  return (
    <div style={{
      background: done ? T.surface : T.redBg, border: `1px solid ${done ? T.border : T.redBorder}`,
      borderRadius: 8, marginTop: 12, flexShrink: 0, display: "flex", flexDirection: "column", maxHeight: "38vh",
    }}>
      <div style={{ padding: "10px 16px", fontSize: 15, color: done ? T.textSecondary : T.red, fontWeight: 600, flexShrink: 0 }}>
        {done ? "✓ Wszystkie ostrzeżenia rozstrzygnięte — możesz zapisać, skopiować lub wyeksportować dokument."
          : `⚠ Pozostało ${pending.length} ${pending.length === 1 ? "ostrzeżenie" : "ostrzeżeń"}. Przy każdym wybierz Zakryj albo Zostaw, `
            + "aby zapisać, skopiować lub wyeksportować dokument."}
      </div>
      <div style={{ overflowY: "auto", minHeight: 0, padding: "0 16px 10px" }}>
        {shown.map(w => {
          const key = warningKey(base, w), isKept = kept.has(key);
          return (
            <div key={w.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderTop: `1px solid ${T.border}` }}>
              <span title={w.level === "RED" ? "Wysokie ryzyko" : "Do sprawdzenia"}
                style={{ width: 8, height: 8, borderRadius: 4, flexShrink: 0, background: w.level === "RED" ? T.red : T.amber }} />
              <div style={{ flex: 1, minWidth: 0, fontSize: 14, color: T.textSecondary }}>
                <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  …{base.slice(Math.max(0, w.start - 30), w.start).replace(/\s+/g, " ")}
                  <b style={{ color: isKept ? T.textSecondary : T.red }}>{w.fragment}</b>
                  {base.slice(w.end, w.end + 30).replace(/\s+/g, " ")}…
                </div>
                <div style={{ fontSize: 12, color: T.textMuted }}>{w.reasons.join(" · ")}</div>
              </div>
              {isKept
                ? <button style={btn(T.textMuted, T.border)} onClick={() => onKeep(key, false)}>Zostawione — cofnij</button>
                : <>
                    <button style={btn(T.blueLight, T.borderActive)} onClick={() => onCover(w)}>Zakryj</button>
                    <button style={btn(T.textSecondary, T.border)} onClick={() => onKeep(key, true)}>Zostaw</button>
                  </>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
