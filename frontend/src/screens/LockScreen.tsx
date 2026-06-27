// Pseudominizer — src/screens/LockScreen.tsx  v1.5
// ============================================================
// ZMIANY W TEJ WERSJI (v1.5):
//   [EXPR-UI] Przycisk Express Mode na stronie logowania — pomija logowanie.
//             onExpressMode() prop → App.tsx przełącza na ExpressModeScreen.
// ZMIANY W v1.4:
//   [UI-FONT-01] Czcionki podniesione globalnie
//     Logo: 18px → 20px
//     Podpis logo: 12px → 14px
//     Label uppercase: 11px → 13px
//     Input hasło: 14px → 16px
//     Przycisk Odblokuj: 14px → 16px
//     Błąd: 13px → 15px
//     PSE badge mono: 10px → 12px
// ============================================================
// ZMIANY W v1.3:
//   [UI-LOCK-01] Oczko podglądu hasła
// ============================================================

import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";
import OnboardingScreen from "./OnboardingScreen";

interface Props {
  onUnlock:      () => void;
  onExpressMode: () => void;
}

type Mode = "checking" | "onboarding" | "login";

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

export default function LockScreen({ onUnlock, onExpressMode }: Props) {
  const [mode,     setMode]     = useState<Mode>("checking");
  const [password, setPassword] = useState("");
  const [showPw,   setShowPw]   = useState(false);
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  useEffect(() => {
    invoke<boolean>("is_first_run")
      .then(first => setMode(first ? "onboarding" : "login"))
      .catch(() => setMode("login"));
  }, []);

  const handleUnlock = async () => {
    if (!password.trim()) { setError("Wpisz hasło."); return; }
    setLoading(true);
    setError("");
    try {
      await invoke("derive_and_store_key", { password });
      onUnlock();
    } catch (e) {
      const msg = String(e);
      if (msg.includes("WRONG_PASSWORD")) {
        setError("Błędne hasło. Spróbuj ponownie.");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  if (mode === "checking") {
    return (
      <div style={{
        width: "100vw", height: "100vh", background: T.bg,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <div style={{ fontFamily: T.mono, fontSize: 14, color: T.textMuted }}>
          ▸ Ładowanie...
        </div>
      </div>
    );
  }

  if (mode === "onboarding") {
    return <OnboardingScreen onFinished={onUnlock} />;
  }

  return (
    <div style={{
      width: "100vw", height: "100vh", background: T.bg,
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 12, padding: "40px 48px", width: 400,
      }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{
              fontFamily: T.mono, fontSize: 12, letterSpacing: "0.18em",
              color: T.blue, border: `1px solid ${T.borderActive}`,
              padding: "2px 7px", borderRadius: 4, textTransform: "uppercase",
            }}>PSE</span>
            <span style={{ fontSize: 20, fontWeight: 300, color: T.textPrimary }}>
              LynxMask Desktop
            </span>
          </div>
          <div style={{ fontSize: 14, color: T.textMuted }}>
            Pseudonimizacja dokumentów
          </div>
        </div>

        {/* Pole hasła z oczkiem */}
        <div style={{ marginBottom: 16 }}>
          <label style={{
            display: "block", fontSize: 13, color: T.textMuted,
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6,
          }}>
            Hasło główne
          </label>
          <div style={{ position: "relative" }}>
            <input
              type={showPw ? "text" : "password"}
              placeholder="Wpisz hasło..."
              value={password}
              onChange={e => { setPassword(e.target.value); setError(""); }}
              onKeyDown={e => e.key === "Enter" && handleUnlock()}
              autoFocus
              style={{
                width: "100%", padding: "11px 48px 11px 14px",
                background: T.bg,
                border: `1px solid ${error ? T.redBorder : T.border}`,
                borderRadius: 6, color: T.textPrimary,
                fontSize: 16, fontFamily: T.sans,
                outline: "none", boxSizing: "border-box",
                transition: "border-color 0.15s",
              }}
            />
            <button
              type="button"
              onClick={() => setShowPw(v => !v)}
              tabIndex={-1}
              style={{
                position: "absolute", right: 12, top: "50%",
                transform: "translateY(-50%)",
                background: "none", border: "none",
                color: showPw ? T.blueLight : T.textMuted,
                cursor: "pointer", padding: 2, lineHeight: 0,
                transition: "color 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.color = T.blueLight)}
              onMouseLeave={e => (e.currentTarget.style.color = showPw ? T.blueLight : T.textMuted)}
              title={showPw ? "Ukryj hasło" : "Pokaż hasło"}
            >
              {showPw ? <IconEyeOff /> : <IconEye />}
            </button>
          </div>
        </div>

        {/* Błąd */}
        {error && (
          <div style={{
            background: T.redBg, border: `1px solid ${T.redBorder}`,
            borderRadius: 6, padding: "8px 12px", marginBottom: 16,
            fontSize: 15, color: T.red,
          }}>
            ✕ {error}
          </div>
        )}

        {/* Przycisk */}
        <button
          onClick={handleUnlock}
          disabled={loading}
          style={{
            width: "100%", padding: "12px",
            background: loading ? T.blueBg : T.blue,
            border: "none", borderRadius: 6,
            color: "#fff", fontSize: 16, fontWeight: 500,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "background 0.15s",
          }}
        >
          {loading ? "▸ Odblokowanie..." : "Odblokuj"}
        </button>

        {/* Separator */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10, margin: "20px 0 4px",
        }}>
          <div style={{ flex: 1, height: 1, background: T.border }} />
          <span style={{ fontSize: 12, color: T.textMuted, fontFamily: T.mono, letterSpacing: "0.06em" }}>
            lub
          </span>
          <div style={{ flex: 1, height: 1, background: T.border }} />
        </div>

        {/* Express Mode */}
        <button
          onClick={onExpressMode}
          style={{
            width: "100%", padding: "10px",
            background: "none",
            border: `1px solid ${T.border}`,
            borderRadius: 6,
            color: T.textMuted, fontSize: 14,
            cursor: "pointer",
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.amber; e.currentTarget.style.color = T.amber; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; }}
        >
          ⚡ Express Mode — bez logowania
        </button>

      </div>
    </div>
  );
}
