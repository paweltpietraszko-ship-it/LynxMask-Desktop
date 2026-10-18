// Pseudominizer — CrashScreen.tsx  v1.1
// [CRASH-UX] Ekran wyświetlany gdy próby startowe zablokują start backendu.
// [LYNX-STARTUP-COMPONENTS] Co zrobić dalej: uruchom ponownie albo skontaktuj się z działem obsługi
// (kontakt dojdzie, gdy będzie — tu, w sekcji „Co zrobić”). Komunikat pokazuje, który element zawiódł.
// Przycisk restartuje tylko okno (restart_app), nie silnik — Tauri nie uruchamia backendu; stąd punkt 1 tekstu.

import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";

interface Props {
  code: string;
  message: string;
  timestamp?: string;
}

export default function CrashScreen({ code, message, timestamp }: Props) {
  const dateStr = timestamp
    ? new Date(timestamp).toLocaleString("pl-PL")
    : new Date().toLocaleString("pl-PL");

  return (
    <div style={{
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      background: T.bg,
      padding: "40px 32px",
      boxSizing: "border-box",
      gap: 0,
    }}>

      {/* Ikona ostrzeżenia */}
      <div style={{
        width: 56, height: 56, borderRadius: "50%",
        background: T.redBg,
        border: `2px solid ${T.redBorder}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 26, marginBottom: 24,
      }}>
        ✕
      </div>

      {/* Tytuł */}
      <div style={{
        fontFamily: T.sans, fontSize: 17, fontWeight: 600,
        color: T.red, marginBottom: 10, textAlign: "center",
      }}>
        Silnik nie uruchomił się poprawnie
      </div>

      {/* Opis */}
      <div style={{
        fontFamily: T.sans, fontSize: 12, color: T.textSecondary,
        textAlign: "center", maxWidth: 380, lineHeight: 1.6, marginBottom: 24,
      }}>
        Program nie uruchomił się, bo nie wszystkie zabezpieczenia działają poprawnie.
        Aby nie narazić danych, praca jest zablokowana.
      </div>

      {/* Kod błędu */}
      <div style={{
        background: T.redBg,
        border: `1px solid ${T.redBorder}`,
        borderRadius: 6,
        padding: "10px 18px",
        fontFamily: T.mono, fontSize: 11,
        color: T.red,
        letterSpacing: "0.08em",
        marginBottom: 32,
        textAlign: "center",
        maxWidth: 420,
        wordBreak: "break-word",
      }}>
        KOD BŁĘDU: {code}
        {message && <div style={{ fontFamily: T.sans, letterSpacing: 0, marginTop: 6 }}>{message}</div>}
      </div>

      {/* Przyciski akcji */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 280 }}>

        {/* Restart */}
        <button
          onClick={() => invoke("restart_app").catch(() => window.location.reload())}
          style={{
            padding: "11px 0",
            fontFamily: T.mono, fontSize: 11,
            letterSpacing: "0.10em",
            textTransform: "uppercase",
            background: T.blue,
            border: "none",
            color: "#fff",
            cursor: "pointer",
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          Spróbuj ponownie
        </button>

      </div>

      {/* Co zrobić dalej */}
      <div style={{
        marginTop: 32,
        padding: "14px 20px",
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 6,
        maxWidth: 380,
        fontFamily: T.sans, fontSize: 11,
        color: T.textMuted,
        lineHeight: 1.7,
      }}>
        <div style={{ fontWeight: 600, color: T.textSecondary, marginBottom: 6 }}>
          Co zrobić:
        </div>
        1. Zamknij aplikację i silnik LynxMask, a potem uruchom je ponownie.<br />
        2. Jeśli problem się powtarza, skontaktuj się z działem obsługi
        i podaj kod błędu oraz komunikat powyżej.
      </div>

      {/* Znacznik czasu */}
      <div style={{
        marginTop: 20,
        fontFamily: T.mono, fontSize: 9,
        color: T.textDim,
        letterSpacing: "0.06em",
      }}>
        {dateStr}
      </div>

    </div>
  );
}
