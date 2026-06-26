// Pseudominizer — CrashScreen.tsx  v1.0
// [CRASH-UX] Ekran wyświetlany gdy smoke test zablokuje start backendu.
// Daje użytkownikowi trzy wyjścia: restart, zgłoszenie błędu przez e-mail, reinstalacja.

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

  const mailSubject = encodeURIComponent(`[LynxMask] Błąd startu: ${code}`);
  const mailBody = encodeURIComponent(
    `Kod błędu: ${code}\nCzas: ${dateStr}\nSzczegóły: ${message}\n\n` +
    `Proszę o pomoc w rozwiązaniu problemu.`
  );
  const mailtoHref = `mailto:support@lynxmask.app?subject=${mailSubject}&body=${mailBody}`;

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
        Test bezpieczeństwa wykrył problem z silnikiem pseudonimizacji.
        Aplikacja nie może działać — dane osobowe nie byłyby odpowiednio chronione.
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
        wordBreak: "break-all",
      }}>
        KOD BŁĘDU: {code}
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
          Uruchom ponownie
        </button>

        {/* Mailto */}
        <a
          href={mailtoHref}
          style={{
            display: "block",
            padding: "11px 0",
            fontFamily: T.mono, fontSize: 11,
            letterSpacing: "0.10em",
            textTransform: "uppercase",
            background: "transparent",
            border: `1px solid ${T.border}`,
            color: T.textSecondary,
            cursor: "pointer",
            borderRadius: 4,
            textAlign: "center",
            textDecoration: "none",
          }}
        >
          Wyślij raport e-mail
        </a>

      </div>

      {/* Reinstalacja */}
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
          Jeśli problem się powtarza:
        </div>
        1. Zamknij aplikację<br />
        2. Pobierz nową wersję instalatora<br />
        3. Zainstaluj ponownie w to samo miejsce<br />
        4. Uruchom aplikację
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
