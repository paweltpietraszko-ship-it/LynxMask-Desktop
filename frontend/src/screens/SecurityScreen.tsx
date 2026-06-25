// Pseudominizer — src/screens/SecurityScreen.tsx  v1.1
// ============================================================
// ZMIANY W TEJ WERSJI:
//   - Redesign wizualny — shadcn/ui dark, czcionki 14px
//   - Karty zamiast płaskich wierszy — lepszy podział informacji
//   - Sekcja "Sesja" z informacją o timeout i wylogowaniu
// ============================================================
// Zachowane bez zmian:
//   - Wszystkie wartości (AES-256-GCM, PBKDF2, ścieżki, opisy)
// ============================================================

import { T } from "../theme";

interface RowProps {
  label: string;
  value: string;
  highlight?: boolean;
}

function Row({ label, value, highlight }: RowProps) {
  return (
    <div style={{
      display: "flex", gap: 20,
      padding: "10px 0",
      borderBottom: `1px solid ${T.border}`,
    }}>
      <span style={{
        fontSize: 12, color: T.textMuted, minWidth: 220,
        fontFamily: T.mono, flexShrink: 0,
      }}>
        {label}
      </span>
      <span style={{
        fontSize: 13, color: highlight ? T.blueLight : T.textSecondary,
        lineHeight: 1.5,
      }}>
        {value}
      </span>
    </div>
  );
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

function Section({ title, children }: SectionProps) {
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 8, padding: "16px 20px", marginBottom: 16,
    }}>
      <div style={{
        fontSize: 11, color: T.blue, textTransform: "uppercase",
        letterSpacing: "0.12em", marginBottom: 12, fontFamily: T.mono,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export default function SecurityScreen() {
  return (
    <div style={{
      padding: 24, height: "100vh", overflowY: "auto",
      boxSizing: "border-box", maxWidth: 700,
    }}>

      <div style={{
        fontSize: 11, letterSpacing: "0.12em", fontFamily: T.mono,
        color: T.blue, textTransform: "uppercase", marginBottom: 20,
      }}>
        Zabezpieczenia
      </div>

      <Section title="Kryptografia">
        <Row label="Szyfrowanie" value="AES-256-GCM" highlight />
        <Row label="Wyprowadzanie klucza" value="PBKDF2-HMAC-SHA256 · 500 000 iteracji" />
        <Row label="Klucz" value="Trzymany wyłącznie w pamięci Rust — TypeScript nigdy nie widzi bajtów" />
        <Row label="Sól" value="%AppData%\Pseudominizer\salt.bin (32 bajty, generowana raz)" />
      </Section>

      <Section title="Sieć i dane">
        <Row label="Dane wychodzące" value="Żadne — aplikacja działa wyłącznie lokalnie" highlight />
        <Row label="Backend" value="FastAPI na 127.0.0.1:8765 · token API w nagłówku X-Api-Token" />
        <Row label="Archiwum" value="SQLite + zaszyfrowane BLOBy (mapy tokenów, opisy dokumentów)" />
        <Row label="Logi audytowe" value="pseudominizer_audit.jsonl — fragmenty tekstu, żadnych pełnych danych" />
      </Section>

      <Section title="Sesja">
        <Row label="Przechowywanie hasła" value="Nigdy — hasło nie jest zapisywane na dysku" highlight />
        <Row label="Automatyczna blokada" value="Po 10 minutach bezczynności — klucz kasowany z pamięci" />
        <Row label="Mapy tokenów (.enc)" value="Czytelne wyłącznie po odblokowaniu — zaszyfrowane kluczem sesyjnym" />
        <Row label="Backend" value="Uruchamiany ręcznie — aplikacja nie autostaruje procesów" />
      </Section>

      <div style={{
        fontSize: 12, color: T.textMuted, lineHeight: 1.7,
        padding: "12px 16px",
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 8,
      }}>
        Zamknięcie aplikacji lub timeout kasuje klucz z pamięci. Dane są bezpieczne nawet jeśli ktoś uzyska dostęp do pliku bazy danych — bez hasła są nieczytelne.
      </div>

    </div>
  );
}
