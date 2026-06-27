// Pseudominizer — src/screens/SecurityScreen.tsx  v2.3
// ============================================================
// ZMIANY W TEJ WERSJI (v2.2):
//   - Sekcja "Hasło" — pełna zmiana hasła przez Tauri invoke("change_password")
//     Rust re-szyfruje wszystkie sesje starym→nowym kluczem, aktualizuje State
//   - Sekcja "Słownik biura" — eksport (.lynxdict) i import słownika
//     Eksport: GET /profile/export-dict → <a download> trick
//     Import: <input type="file"> → POST /profile/import-dict
//   - Sekcja "Dane" — reset profilu (POST /profile/reset, dwuetapowe potwierdzenie)
//   - apiToken prop — nagłówek X-Api-Token na każdym żądaniu
// ============================================================
// Zachowane bez zmian:
//   - Sekcje informacyjne (Kryptografia, Sieć i dane, Sesja)
// ============================================================

import { useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";

const API = "http://127.0.0.1:8765";

// ── Pomocnicze ────────────────────────────────────────────────────────────────

function apiFetch(path: string, options: RequestInit, apiToken: string): Promise<Response> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (apiToken) headers["X-Api-Token"] = apiToken;
  return fetch(`${API}${path}`, { ...options, headers });
}

// ── Komponenty UI ─────────────────────────────────────────────────────────────

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

function Btn({ onClick, disabled, variant = "default", children }: {
  onClick: () => void;
  disabled?: boolean;
  variant?: "default" | "destructive";
  children: React.ReactNode;
}) {
  const bg        = variant === "destructive" ? T.redBorder   : T.blue;
  const bgDisabled = variant === "destructive" ? "#2a1010"    : T.surface;
  const color      = disabled ? T.textMuted : "#fff";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "9px 18px",
        background: disabled ? bgDisabled : bg,
        border: `1px solid ${disabled ? T.border : bg}`,
        borderRadius: 6,
        color,
        fontSize: 14, fontWeight: 500,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background 0.15s",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </button>
  );
}

function Alert({ type, children }: { type: "success" | "error"; children: React.ReactNode }) {
  const isOk = type === "success";
  return (
    <div style={{
      marginTop: 12,
      background: isOk ? T.greenBg : T.redBg,
      border: `1px solid ${isOk ? T.greenBorder : T.redBorder}`,
      borderRadius: 6, padding: "8px 14px",
      fontSize: 14, color: isOk ? T.green : T.red, lineHeight: 1.5,
    }}>
      {isOk ? "✓ " : "✕ "}{children}
    </div>
  );
}

// ── Sekcja: Zmiana hasła ──────────────────────────────────────────────────────

function InputPw({ value, onChange, placeholder }: {
  value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <input
      type="password"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        width: "100%", boxSizing: "border-box",
        padding: "9px 12px",
        background: T.bg, border: `1px solid ${T.border}`,
        borderRadius: 6, color: T.textPrimary,
        fontSize: 14, fontFamily: T.sans,
        outline: "none",
      }}
    />
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 12, color: T.textMuted, textTransform: "uppercase",
      letterSpacing: "0.08em", marginBottom: 6, fontFamily: T.mono,
    }}>
      {children}
    </div>
  );
}

function ChangePasswordSection({ apiToken }: { apiToken: string }) {
  const [oldPw,     setOldPw]     = useState("");
  const [newPw,     setNewPw]     = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [loading,   setLoading]   = useState(false);
  const [status,    setStatus]    = useState<{ type: "success" | "error"; msg: string } | null>(null);

  async function handleChange() {
    setStatus(null);
    if (!oldPw || !newPw || !confirmPw) {
      setStatus({ type: "error", msg: "Wypełnij wszystkie pola." });
      return;
    }
    if (newPw !== confirmPw) {
      setStatus({ type: "error", msg: "Nowe hasła nie są identyczne." });
      return;
    }
    if (newPw.length < 8) {
      setStatus({ type: "error", msg: "Nowe hasło musi mieć co najmniej 8 znaków." });
      return;
    }
    setLoading(true);
    try {
      await invoke("change_password", {
        oldPassword: oldPw,
        newPassword: newPw,
        apiToken,
      });
      setStatus({ type: "success", msg: "Hasło zmienione. Wszystkie sesje zostały ponownie zaszyfrowane." });
      setOldPw(""); setNewPw(""); setConfirmPw("");
    } catch (err: unknown) {
      const msg = typeof err === "string" ? err : "Błąd zmiany hasła.";
      if (msg === "WRONG_PASSWORD") {
        setStatus({ type: "error", msg: "Stare hasło jest nieprawidłowe." });
      } else {
        setStatus({ type: "error", msg });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="Hasło">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 14 }}>
        <div>
          <FieldLabel>Stare hasło</FieldLabel>
          <InputPw value={oldPw} onChange={setOldPw} placeholder="••••••••" />
        </div>
        <div>
          <FieldLabel>Nowe hasło</FieldLabel>
          <InputPw value={newPw} onChange={setNewPw} placeholder="••••••••" />
        </div>
        <div>
          <FieldLabel>Potwierdź nowe</FieldLabel>
          <InputPw value={confirmPw} onChange={setConfirmPw} placeholder="••••••••" />
        </div>
      </div>
      <Btn onClick={handleChange} disabled={loading}>
        {loading ? "▸ Zmieniam..." : "Zmień hasło"}
      </Btn>
      {status && <Alert type={status.type}>{status.msg}</Alert>}
      <div style={{ marginTop: 14, fontSize: 12, color: T.textMuted, lineHeight: 1.6 }}>
        Nie pamiętasz starego hasła? Przejdź do sekcji <strong style={{ color: T.textSecondary }}>Dane</strong> poniżej
        i usuń wszystkie dane — profil zostanie zresetowany, a przy następnym uruchomieniu
        ustawisz nowe hasło. Utracisz słownik biura i historię sesji.
      </div>
    </Section>
  );
}

// ── Sekcja: Eksport / Import słownika ────────────────────────────────────────

function DictSection({ apiToken }: { apiToken: string }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [status,    setStatus]    = useState<{ type: "success" | "error"; msg: string } | null>(null);

  async function handleExport() {
    setStatus(null);
    setExporting(true);
    try {
      const res = await apiFetch("/profile/export-dict", { method: "GET" }, apiToken);
      if (!res.ok) {
        let msg = `Błąd serwera (${res.status})`;
        try { const d = await res.json(); msg = d.error ?? msg; } catch { /* brak JSON */ }
        setStatus({ type: "error", msg });
        return;
      }
      const data = await res.json();
      // <a download> trick — tworzy Blob i symuluje kliknięcie linku
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = "lynxmask_slownik.lynxdict";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setStatus({ type: "success", msg: "Słownik wyeksportowany jako lynxmask_slownik.lynxdict" });
    } catch {
      setStatus({ type: "error", msg: "Błąd połączenia z backendem." });
    } finally {
      setExporting(false);
    }
  }

  async function handleImport(file: File) {
    setStatus(null);
    setImporting(true);
    try {
      const text = await file.text();
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        setStatus({ type: "error", msg: "Plik nie jest prawidłowym JSON (.lynxdict)." });
        return;
      }
      // Obsługujemy dwa formaty: tablica wpisów lub obiekt { entries: [...] }
      const entries = Array.isArray(parsed)
        ? parsed
        : (parsed as any)?.entries ?? parsed;

      const res = await apiFetch("/profile/import-dict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries }),
      }, apiToken);
      const data = await res.json();
      if (res.ok && data.ok) {
        const n = data.added ?? data.count ?? "?";
        setStatus({ type: "success", msg: `Dodano ${n} wpisów do słownika.` });
      } else {
        setStatus({ type: "error", msg: data.error ?? `Błąd serwera (${res.status})` });
      }
    } catch {
      setStatus({ type: "error", msg: "Błąd odczytu pliku lub połączenia z backendem." });
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Section title="Słownik biura">
      <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 14, lineHeight: 1.6 }}>
        Eksportuj listę encji biura (nazwy, adresy, osoby) do pliku .lynxdict,
        lub importuj gotowy słownik — np. po reinstalacji aplikacji.
      </div>

      {/* Ukryty input pliku */}
      <input
        ref={fileRef}
        type="file"
        accept=".lynxdict,application/json"
        style={{ display: "none" }}
        onChange={e => {
          const f = e.target.files?.[0];
          if (f) handleImport(f);
        }}
      />

      <div style={{ display: "flex", gap: 10 }}>
        <Btn onClick={handleExport} disabled={exporting}>
          {exporting ? "▸ Eksportuję..." : "Eksportuj słownik (.lynxdict)"}
        </Btn>
        <Btn onClick={() => fileRef.current?.click()} disabled={importing}>
          {importing ? "▸ Importuję..." : "Importuj słownik (.lynxdict)"}
        </Btn>
      </div>
      {status && <Alert type={status.type}>{status.msg}</Alert>}
    </Section>
  );
}

// ── Sekcja: Reset profilu ─────────────────────────────────────────────────────

function ResetSection({ apiToken }: { apiToken: string }) {
  const [step,    setStep]    = useState<"idle" | "confirm1" | "confirm2">("idle");
  const [loading, setLoading] = useState(false);
  const [status,  setStatus]  = useState<{ type: "success" | "error"; msg: string } | null>(null);

  async function handleReset() {
    setStatus(null);
    setLoading(true);
    try {
      const res = await apiFetch("/profile/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      }, apiToken);
      const data = await res.json();
      if (res.ok && data.ok) {
        setStatus({ type: "success", msg: "Profil został wyczyszczony. Wszystkie dane usunięte." });
        setStep("idle");
      } else {
        setStatus({ type: "error", msg: data.error ?? `Błąd serwera (${res.status})` });
        setStep("idle");
      }
    } catch {
      setStatus({ type: "error", msg: "Błąd połączenia z backendem." });
      setStep("idle");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Section title="Dane">
      <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 14, lineHeight: 1.6 }}>
        Usuwa wszystkie dane profilu: słownik biura, archiwum dokumentów i logi audytowe.
        Tej operacji nie można cofnąć.
      </div>

      {step === "idle" && (
        <Btn onClick={() => setStep("confirm1")} variant="destructive">
          Usuń wszystkie dane
        </Btn>
      )}

      {step === "confirm1" && (
        <div style={{
          background: T.redBg, border: `1px solid ${T.redBorder}`,
          borderRadius: 8, padding: "14px 16px",
        }}>
          <div style={{ fontSize: 14, color: T.red, marginBottom: 12, fontWeight: 600 }}>
            Czy na pewno chcesz usunąć wszystkie dane profilu?
          </div>
          <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 14, lineHeight: 1.5 }}>
            Zostanie usunięty słownik biura, całe archiwum dokumentów i logi.
            Operacja jest nieodwracalna.
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Btn onClick={() => setStep("confirm2")} variant="destructive">
              Tak, rozumiem — usuń dane
            </Btn>
            <Btn onClick={() => setStep("idle")}>
              Anuluj
            </Btn>
          </div>
        </div>
      )}

      {step === "confirm2" && (
        <div style={{
          background: T.redBg, border: `1px solid ${T.redBorder}`,
          borderRadius: 8, padding: "14px 16px",
        }}>
          <div style={{ fontSize: 14, color: T.red, marginBottom: 12, fontWeight: 600 }}>
            Ostatnie potwierdzenie — to jest nieodwracalne
          </div>
          <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 14 }}>
            Kliknij poniżej aby trwale usunąć wszystkie dane.
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Btn onClick={handleReset} disabled={loading} variant="destructive">
              {loading ? "▸ Usuwam..." : "Potwierdź usunięcie"}
            </Btn>
            <Btn onClick={() => setStep("idle")}>
              Anuluj
            </Btn>
          </div>
        </div>
      )}

      {status && <Alert type={status.type}>{status.msg}</Alert>}
    </Section>
  );
}

// ── Komponent główny ──────────────────────────────────────────────────────────

interface Props {
  apiToken?: string;
}

export default function SecurityScreen({ apiToken = "" }: Props) {
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

      {/* ── Sekcje akcji ── */}
      <ChangePasswordSection apiToken={apiToken} />
      <DictSection apiToken={apiToken} />

      {/* ── Sekcje informacyjne ── */}
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
        borderRadius: 8, marginBottom: 16,
      }}>
        Zamknięcie aplikacji lub timeout kasuje klucz z pamięci. Dane są bezpieczne nawet jeśli ktoś uzyska dostęp do pliku bazy danych — bez hasła są nieczytelne.
      </div>

      {/* ── Reset — na dole ── */}
      <ResetSection apiToken={apiToken} />

    </div>
  );
}
