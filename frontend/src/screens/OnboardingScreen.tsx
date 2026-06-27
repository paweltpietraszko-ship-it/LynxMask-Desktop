// Pseudominizer — src/screens/OnboardingScreen.tsx  v1.4
// ============================================================
// ZMIANY W TEJ WERSJI (v1.3):
//   [UI-FONT-01] Czcionki podniesione globalnie
//     Emoji karty: 56px → 64px
//     Tytuł karty: 20px → 22px
//     Treść karty: 14px → 16px
//     Tip box: 13px → 15px
//     Przyciski Dalej/Wstecz: 13px → 15px
//     Ekran hasła — tytuł: 18px → 20px, podpis: 13px → 15px
//     Label uppercase: 11px → 13px
//     Input: 14px → 16px
//     Błąd/info box: 12px → 14px
//     Przycisk Zacznij używać: 13px → 15px
// ============================================================
// ZMIANY W v1.2: [UI-ONB-02] Oczka na ekranie hasła
// ZMIANY W v1.1: [UI-ONB-01] Karta OCR
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

interface Page {
  emoji: string;
  title: string;
  body:  string;
  tip?:  string;
}

const PAGES: Page[] = [
  {
    emoji: "🔒",
    title: "Pseudominizer ukrywa dane osobowe",
    body:  "Zanim wyślesz dokument do modelu AI, aplikacja zastępuje wszystkie wrażliwe dane tokenami — OSOBA_001, FIRMA_001, ADRES_001.\n\nModel widzi treść dokumentu, ale nie widzi żadnych danych osobowych.",
  },
  {
    emoji: "📄",
    title: "Wgraj dokument dwoma sposobami",
    body:  "• Przeciągnij plik na pole wejściowe (DOCX, PDF, TXT, obraz).\n\n• Wklej tekst bezpośrednio — Ctrl+V w polu tekstowym obok.\n\nJeśli jednocześnie wgrasz plik i wpiszesz tekst — plik ma pierwszeństwo.",
    tip:   "Pseudominizer działa w 100% lokalnie. Żaden dokument nie opuszcza Twojego komputera.",
  },
  {
    emoji: "✏️",
    title: "Sprawdź i uzupełnij wynik",
    body:  "Po pseudonimizacji widzisz tekst z tokenami. Jeśli coś zostało pominięte:\n\n1. Zaznacz fragment w podglądzie.\n2. Wybierz typ encji (OSOBA / FIRMA / ADRES / NUMER).\n3. Kliknij \"Dodaj i zakryj\".",
    tip:   "Zaznaczone frazy są zapamiętywane w profilu biura — przy kolejnych dokumentach wykrywane automatycznie.",
  },
  {
    emoji: "🗺️",
    title: "Jak odczytać odpowiedź AI?",
    body:  "Wyślij zanonimizowany tekst do dowolnego modelu AI. Gdy dostaniesz odpowiedź z tokenami, otwórz zakładkę Odmaskuj.\n\nWklej odpowiedź — aplikacja zastąpi tokeny oryginalnymi danymi.",
    tip:   "Kod PSE-XXXX-XXXX w tekście łączy dokument z jego mapą tokenów. Jest wykrywany automatycznie.",
  },
  {
    emoji: "📷",
    title: "Skany i zdjęcia dokumentów",
    body:  "Jakość maskowania zależy od jakości źródła. Skany niskiej rozdzielczości lub zdjęcia dokumentów mogą zawierać błędy odczytu — litery zamienione, słowa połączone lub podzielone.\n\nProgram ostrzeże Cię gdy wykryje słabą jakość materiału.",
    tip:   "Przy wątpliwej jakości OCR zawsze sprawdź wynik ręcznie — zwłaszcza numery (PESEL, NIP, IBAN) i nazwiska.",
  },
];

interface Props {
  onFinished: () => void;
}

export default function OnboardingScreen({ onFinished }: Props) {
  const [page,         setPage]         = useState(0);
  const [password,     setPassword]     = useState("");
  const [confirm,      setConfirm]      = useState("");
  const [showPw,       setShowPw]       = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);
  const [pwError,      setPwError]      = useState("");
  const [saving,       setSaving]       = useState(false);
  const [recoveryKey,  setRecoveryKey]  = useState<string | null>(null);
  const [keyCopied,    setKeyCopied]    = useState(false);
  const isLastPage  = page === PAGES.length - 1;
  const isSetupPage = page === PAGES.length;
  const isRecoveryPage = recoveryKey !== null;
  const current = PAGES[page] ?? null;

  async function handleSetPassword() {
    if (password.length < 6) { setPwError("Hasło musi mieć co najmniej 6 znaków."); return; }
    if (password !== confirm) { setPwError("Hasła nie są identyczne."); return; }
    setSaving(true); setPwError("");
    try {
      await invoke("derive_and_store_key", { password });
      const rk = await invoke<string>("generate_recovery_key");
      setRecoveryKey(rk);
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

  if (isRecoveryPage) {
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

          {/* Klucz */}
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

  if (isSetupPage) {
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

          {/* Pole Hasło z oczkiem */}
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
                  cursor: "pointer", padding: 2, lineHeight: 0, transition: "color 0.15s",
                }}
                onMouseEnter={e => (e.currentTarget.style.color = T.blueLight)}
                onMouseLeave={e => (e.currentTarget.style.color = showPw ? T.blueLight : T.textMuted)}
                title={showPw ? "Ukryj hasło" : "Pokaż hasło"}
              >
                {showPw ? <IconEyeOff /> : <IconEye />}
              </button>
            </div>
          </div>

          {/* Pole Powtórz hasło z oczkiem */}
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
                  cursor: "pointer", padding: 2, lineHeight: 0, transition: "color 0.15s",
                }}
                onMouseEnter={e => (e.currentTarget.style.color = T.blueLight)}
                onMouseLeave={e => (e.currentTarget.style.color = showConfirm ? T.blueLight : T.textMuted)}
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
              onClick={() => setPage(PAGES.length - 1)}
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

  // ── Karty onboardingu ─────────────────────────────────────────

  return (
    <div style={{
      width: "100vw", height: "100vh", background: T.bg,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 12, padding: "40px 48px", width: 520,
        display: "flex", flexDirection: "column",
      }}>

        <div style={{ textAlign: "center", fontSize: 64, marginBottom: 24, lineHeight: 1 }}>
          {current.emoji}
        </div>

        <div style={{ fontSize: 22, fontWeight: 600, color: T.textPrimary, textAlign: "center", marginBottom: 20, lineHeight: 1.3 }}>
          {current.title}
        </div>

        <div style={{
          fontSize: 16, color: T.textSecondary, lineHeight: 1.7,
          whiteSpace: "pre-wrap", marginBottom: current.tip ? 20 : 32,
          minHeight: 110,
        }}>
          {current.body}
        </div>

        {current.tip && (
          <div style={{
            background: T.blueBg, border: `1px solid ${T.borderActive}`,
            borderRadius: 8, padding: "12px 16px", marginBottom: 32,
            fontSize: 15, color: T.blueLight, lineHeight: 1.6,
          }}>
            💡 {current.tip}
          </div>
        )}

        {/* Kropki postępu */}
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 24 }}>
          {PAGES.map((_, i) => (
            <div key={i} style={{
              width: i === page ? 22 : 9, height: 9, borderRadius: 5,
              background: i === page ? T.blue : T.border,
              transition: "width 0.2s, background 0.2s",
            }} />
          ))}
        </div>

        {/* Nawigacja */}
        <div style={{ display: "flex", gap: 10 }}>
          {page === 0 ? (
            <button
              onClick={() => setPage(PAGES.length)}
              style={{
                flex: 1, padding: "11px", background: "transparent",
                border: `1px solid ${T.border}`, borderRadius: 6,
                color: T.textMuted, fontSize: 15, cursor: "pointer",
              }}
            >Pomiń</button>
          ) : (
            <button
              onClick={() => setPage(p => p - 1)}
              style={{
                flex: 1, padding: "11px", background: "transparent",
                border: `1px solid ${T.border}`, borderRadius: 6,
                color: T.textMuted, fontSize: 15, cursor: "pointer",
              }}
            >Wstecz</button>
          )}
          <button
            onClick={() => isLastPage ? setPage(PAGES.length) : setPage(p => p + 1)}
            style={{
              flex: 2, padding: "11px", background: T.blue,
              border: "none", borderRadius: 6,
              color: "#fff", fontSize: 15, fontWeight: 500, cursor: "pointer",
            }}
          >{isLastPage ? "Ustaw hasło →" : "Dalej →"}</button>
        </div>

      </div>
    </div>
  );
}
