// Pseudominizer — src/screens/OnboardingScreen.tsx  v2.0
// ============================================================
// ZMIANY W v2.0: [UI-ONB-03] Redesign — jedna karta + "więcej" w stopce
// ZMIANY W v1.5: sync z mobile — LynxMask, strona bezpieczeństwa
// ZMIANY W v1.4: klucz odzyskiwania po ustawieniu hasła
// ============================================================

import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";

function IconEye() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}
function IconEyeOff() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

const HIGHLIGHTS = [
  { emoji: "🔒", text: "Dane zastępowane tokenami zanim trafią do AI" },
  { emoji: "🛡️", text: "Wszystko działa lokalnie — żaden serwer nie widzi Twoich dokumentów" },
  { emoji: "✏️", text: "Zaznacz pominięte fragmenty i zamaskuj ręcznie" },
  { emoji: "🗺️", text: "Wklej odpowiedź AI — aplikacja odtworzy oryginalne dane" },
];

const MORE_INFO = [
  {
    title: "Jak wgrać dokument?",
    body: "Przeciągnij plik (DOCX, PDF, TXT, obraz) na pole wejściowe lub wklej tekst przez Ctrl+V. Jeśli wgrasz plik i wpiszesz tekst jednocześnie — plik ma pierwszeństwo.",
  },
  {
    title: "Zaznaczanie pominięć",
    body: "Po pseudonimizacji zaznacz fragment w podglądzie, wybierz typ (OSOBA / FIRMA / ADRES / NUMER) i kliknij „Dodaj i zakryj". Zaznaczone frazy są zapamiętywane na przyszłość.",
  },
  {
    title: "Jak odczytać odpowiedź AI?",
    body: "Wyślij zanonimizowany tekst do modelu AI. Gdy dostaniesz odpowiedź z tokenami, otwórz zakładkę Odmaskuj i wklej odpowiedź — aplikacja zastąpi tokeny danymi.",
  },
  {
    title: "Skany i zdjęcia",
    body: "Jakość maskowania zależy od jakości źródła. Przy skanach niskiej rozdzielczości zawsze sprawdź wynik ręcznie — zwłaszcza numery (PESEL, NIP, IBAN) i nazwiska.",
  },
  {
    title: "Twarze i podpisy",
    body: "LynxMask przetwarza tekst, ale nie wykrywa twarzy ani podpisów. Zanim zrobisz zdjęcie dokumentu — zakryj twarz, podpis i pieczątkę palcem lub kartką.",
  },
];

interface Props {
  onFinished: () => void;
}

export default function OnboardingScreen({ onFinished }: Props) {
  const [showMore,     setShowMore]     = useState(false);
  const [password,     setPassword]     = useState("");
  const [confirm,      setConfirm]      = useState("");
  const [showPw,       setShowPw]       = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);
  const [pwError,      setPwError]      = useState("");
  const [saving,       setSaving]       = useState(false);
  const [recoveryKey,  setRecoveryKey]  = useState<string | null>(null);
  const [keyCopied,    setKeyCopied]    = useState(false);
  const [screen,       setScreen]       = useState<"intro" | "setup" | "recovery">("intro");

  async function handleSetPassword() {
    if (password.length < 6) { setPwError("Hasło musi mieć co najmniej 6 znaków."); return; }
    if (password !== confirm) { setPwError("Hasła nie są identyczne."); return; }
    setSaving(true); setPwError("");
    try {
      await invoke("derive_and_store_key", { password });
      const rk = await invoke<string>("generate_recovery_key");
      setRecoveryKey(rk);
      setScreen("recovery");
    } catch (e) {
      setPwError(`Błąd: ${String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleCopyRecovery() {
    if (!recoveryKey) return;
    await navigator.clipboard.writeText(recoveryKey);
    setKeyCopied(true);
    setTimeout(() => setKeyCopied(false), 2000);
  }

  // ── Ekran klucza odzyskiwania ─────────────────────────────────

  if (screen === "recovery") {
    return (
      <div style={{
        width: "100vw", height: "100vh", background: T.bg,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 12, padding: "40px 48px", width: 460,
        }}>
          <div style={{ textAlign: "center", fontSize: 52, marginBottom: 24 }}>🗝️</div>
          <div style={{ fontSize: 20, fontWeight: 600, color: T.textPrimary, marginBottom: 8, textAlign: "center" }}>
            Klucz odzyskiwania
          </div>
          <div style={{ fontSize: 15, color: T.textMuted, marginBottom: 24, textAlign: "center", lineHeight: 1.6 }}>
            Jeśli zapomnisz hasła, ten klucz pozwoli Ci ustawić nowe<br />
            bez utraty danych. Zapisz go w bezpiecznym miejscu.
          </div>

          <div style={{
            background: T.bg, border: `1px solid ${T.border}`,
            borderRadius: 8, padding: "16px 20px", marginBottom: 16,
            textAlign: "center",
          }}>
            <div style={{
              fontFamily: T.mono, fontSize: 22, letterSpacing: "0.15em",
              color: T.textPrimary, fontWeight: 600,
            }}>
              {recoveryKey}
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            <button
              onClick={handleCopyRecovery}
              style={{
                flex: 1, padding: "10px 0",
                background: keyCopied ? T.greenBg : T.surface,
                border: `1px solid ${keyCopied ? T.green : T.border}`,
                borderRadius: 6, color: keyCopied ? T.green : T.textSecondary,
                fontSize: 14, cursor: "pointer",
              }}
            >
              {keyCopied ? "✓ Skopiowano" : "Kopiuj"}
            </button>
          </div>

          <div style={{
            background: T.amberBg, border: `1px solid ${T.amberBorder}`,
            borderRadius: 6, padding: "10px 14px", marginBottom: 20,
            fontSize: 13, color: T.amber, lineHeight: 1.6,
          }}>
            ⚠ Ten klucz zostanie pokazany tylko raz. Nie ma możliwości jego odtworzenia.
            Możesz wygenerować nowy klucz w Ustawienia → Zabezpieczenia.
          </div>

          <button
            onClick={onFinished}
            style={{
              width: "100%", padding: "12px 0",
              background: T.blue, border: "none",
              borderRadius: 8, color: "#fff",
              fontSize: 15, fontWeight: 500, cursor: "pointer",
            }}
          >
            Zapisałem klucz — wejdź do aplikacji
          </button>
        </div>
      </div>
    );
  }

  // ── Ekran ustawienia hasła ────────────────────────────────────

  if (screen === "setup") {
    return (
      <div style={{
        width: "100vw", height: "100vh", background: T.bg,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 12, padding: "40px 48px", width: 420,
        }}>
          <div style={{ textAlign: "center", fontSize: 52, marginBottom: 24 }}>🔑</div>

          <div style={{ fontSize: 20, fontWeight: 600, color: T.textPrimary, marginBottom: 8, textAlign: "center" }}>
            Ustaw hasło główne
          </div>
          <div style={{ fontSize: 15, color: T.textMuted, marginBottom: 28, textAlign: "center", lineHeight: 1.6 }}>
            Hasło szyfruje wszystkie dane lokalne.<br />
            Nie jest nigdzie przechowywane — zapisz je w bezpiecznym miejscu.
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{
              display: "block", fontSize: 13, color: T.textMuted,
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
            }}>Hasło</label>
            <div style={{ position: "relative" }}>
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={e => { setPassword(e.target.value); setPwError(""); }}
                onKeyDown={e => e.key === "Enter" && handleSetPassword()}
                autoFocus
                placeholder="Minimum 6 znaków"
                style={{
                  width: "100%", padding: "11px 48px 11px 14px", background: T.bg,
                  border: `1px solid ${T.border}`, borderRadius: 6,
                  color: T.textPrimary, fontSize: 16,
                  fontFamily: T.sans, outline: "none", boxSizing: "border-box",
                }}
              />
              <button type="button" onClick={() => setShowPw(v => !v)} tabIndex={-1}
                style={{
                  position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                  background: "none", border: "none",
                  color: showPw ? T.blueLight : T.textMuted,
                  cursor: "pointer", padding: 2, lineHeight: 0,
                }}
                title={showPw ? "Ukryj hasło" : "Pokaż hasło"}
              >
                {showPw ? <IconEyeOff /> : <IconEye />}
              </button>
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{
              display: "block", fontSize: 13, color: T.textMuted,
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
            }}>Powtórz hasło</label>
            <div style={{ position: "relative" }}>
              <input
                type={showConfirm ? "text" : "password"}
                value={confirm}
                onChange={e => { setConfirm(e.target.value); setPwError(""); }}
                onKeyDown={e => e.key === "Enter" && handleSetPassword()}
                placeholder="Wpisz hasło ponownie"
                style={{
                  width: "100%", padding: "11px 48px 11px 14px", background: T.bg,
                  border: `1px solid ${pwError ? T.redBorder : T.border}`, borderRadius: 6,
                  color: T.textPrimary, fontSize: 16,
                  fontFamily: T.sans, outline: "none", boxSizing: "border-box",
                }}
              />
              <button type="button" onClick={() => setShowConfirm(v => !v)} tabIndex={-1}
                style={{
                  position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                  background: "none", border: "none",
                  color: showConfirm ? T.blueLight : T.textMuted,
                  cursor: "pointer", padding: 2, lineHeight: 0,
                }}
                title={showConfirm ? "Ukryj hasło" : "Pokaż hasło"}
              >
                {showConfirm ? <IconEyeOff /> : <IconEye />}
              </button>
            </div>
          </div>

          {pwError && (
            <div style={{
              background: T.redBg, border: `1px solid ${T.redBorder}`,
              borderRadius: 6, padding: "8px 12px", marginBottom: 16,
              fontSize: 15, color: T.red,
            }}>✕ {pwError}</div>
          )}

          <div style={{
            background: T.blueBg, border: `1px solid ${T.borderActive}`,
            borderRadius: 6, padding: "10px 14px", marginBottom: 20,
            fontSize: 14, color: T.blueLight, lineHeight: 1.5,
          }}>
            💡 Aplikacja blokuje się automatycznie po 10 minutach bezczynności.
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => setScreen("intro")}
              style={{
                flex: 1, padding: "11px", background: "transparent",
                border: `1px solid ${T.border}`, borderRadius: 6,
                color: T.textMuted, fontSize: 15, cursor: "pointer",
              }}
            >Wstecz</button>
            <button
              onClick={handleSetPassword}
              disabled={saving || !password || !confirm}
              style={{
                flex: 2, padding: "11px", background: T.blue,
                border: "none", borderRadius: 6,
                color: "#fff", fontSize: 15, fontWeight: 500,
                cursor: saving || !password || !confirm ? "not-allowed" : "pointer",
                opacity: saving || !password || !confirm ? 0.5 : 1,
              }}
            >{saving ? "Zapisuję..." : "Zacznij używać →"}</button>
          </div>
        </div>
      </div>
    );
  }

  // ── Ekran intro (jedna karta) ─────────────────────────────────

  return (
    <div style={{
      width: "100vw", height: "100vh", background: T.bg,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 12, padding: "40px 48px", width: 480,
        display: "flex", flexDirection: "column",
      }}>

        <div style={{ textAlign: "center", fontSize: 52, marginBottom: 16, lineHeight: 1 }}>🦁</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.textPrimary, textAlign: "center", marginBottom: 6 }}>
          LynxMask
        </div>
        <div style={{ fontSize: 15, color: T.textMuted, textAlign: "center", marginBottom: 28 }}>
          Pseudonimizacja RODO przed wysłaniem do AI
        </div>

        {/* Kluczowe punkty */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 28 }}>
          {HIGHLIGHTS.map((h, i) => (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
              <span style={{ fontSize: 20, lineHeight: 1.4, flexShrink: 0 }}>{h.emoji}</span>
              <span style={{ fontSize: 15, color: T.textSecondary, lineHeight: 1.6 }}>{h.text}</span>
            </div>
          ))}
        </div>

        {/* Rozwiń więcej */}
        {showMore && (
          <div style={{
            borderTop: `1px solid ${T.border}`,
            paddingTop: 20, marginBottom: 20,
            display: "flex", flexDirection: "column", gap: 16,
          }}>
            {MORE_INFO.map((m, i) => (
              <div key={i}>
                <div style={{ fontSize: 13, fontWeight: 600, color: T.textPrimary, marginBottom: 4 }}>{m.title}</div>
                <div style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.6 }}>{m.body}</div>
              </div>
            ))}
          </div>
        )}

        {/* Przycisk główny */}
        <button
          onClick={() => setScreen("setup")}
          style={{
            width: "100%", padding: "13px 0",
            background: T.blue, border: "none",
            borderRadius: 8, color: "#fff",
            fontSize: 15, fontWeight: 500, cursor: "pointer",
            marginBottom: 14,
          }}
        >
          Zacznij — ustaw hasło →
        </button>

        {/* Stopka */}
        <div style={{ textAlign: "center" }}>
          <button
            onClick={() => setShowMore(v => !v)}
            style={{
              background: "none", border: "none",
              color: T.textMuted, fontSize: 13,
              cursor: "pointer", textDecoration: "underline",
              textDecorationStyle: "dotted",
            }}
          >
            {showMore ? "Zwiń" : "Jak to działa? Dowiedz się więcej"}
          </button>
        </div>

      </div>
    </div>
  );
}
