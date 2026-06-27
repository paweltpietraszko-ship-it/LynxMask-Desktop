// Pseudominizer — App.tsx  v1.7
// [BUG-10] tokenReady: blokuje MainLayout dopóki apiToken nie załadowany.
//   Poprzednio UI było aktywne z apiToken="" przez chwilę po odblokowaniu → 401.
// [FIX-TOKEN-API] Ładuje api_token.txt przez read_api_token po odblokowaniu.
//   Token przekazywany do MainLayout → ekranów jako prop apiToken.
// Idle timer: ostrzeżenie po 9 min, wylogowanie po 10 min.
// clear_key() przy zamknięciu okna i po idle timeout.
// [BUG-P4-03] demaskPse + onDemask: stan PSE z Biblioteki przekazywany
//   do MainLayout → Depseudonimizuj jako initialPse.

import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import LockScreen from "./screens/LockScreen";
import MainLayout from "./screens/MainLayout";
import CrashScreen from "./screens/CrashScreen";
import ExpressModeScreen from "./screens/ExpressModeScreen";
import { T } from "./theme";

export type Screen = "pseudonimizuj" | "biblioteka" | "depseudonimizuj" | "security";

const IDLE_MS  = 10 * 60 * 1000;  // 10 minut → wylogowanie
const WARN_MS  =  9 * 60 * 1000;  // 9 minut → ostrzeżenie

export default function App() {
  const [unlocked,     setUnlocked]     = useState(false);
  const [activeScreen, setActiveScreen] = useState<Screen>("pseudonimizuj");
  const [idleWarning,  setIdleWarning]  = useState(false);
  const [countdown,    setCountdown]    = useState(60);
  const [apiToken,     setApiToken]     = useState("");
  const [tokenReady,   setTokenReady]   = useState(false);
  const [crashInfo,    setCrashInfo]    = useState<{code: string; message: string; timestamp?: string} | null>(null);
  // [BUG-P4-03] PSE przekazywane z Biblioteki do Depseudonimizuj przy kliknięciu odpowiedzi AI.
  const [demaskPse,    setDemaskPse]    = useState<string | null>(null);
  const [expressMode,  setExpressMode]  = useState(false);

  // ── Zamknięcie okna → clear key ───────────────────────────────────────────

  useEffect(() => {
    let unsub: (() => void) | undefined;
    getCurrentWindow()
      .onCloseRequested(async () => { await invoke("clear_key").catch(() => {}); })
      .then(fn => { unsub = fn; })
      .catch(() => {});
    return () => unsub?.();
  }, []);

  // ── Sprawdź stan przy hot-reload ──────────────────────────────────────────

  useEffect(() => {
    invoke<boolean>("is_unlocked").then(setUnlocked).catch(() => {});
  }, []);

  // ── Załaduj token API po odblokowaniu ─────────────────────────────────────

  useEffect(() => {
    if (!unlocked) {
      setApiToken("");
      setTokenReady(false);
      return;
    }
    // [BUG-10] tokenReady=false blokuje MainLayout aż token się załaduje.
    setTokenReady(false);
    invoke<string>("read_api_token")
      .then(token => {
        setApiToken(token);
        setTokenReady(true);
      })
      .catch(async () => {
        // Backend może jeszcze startować — poczekaj 4s i spróbuj ponownie.
        await new Promise(r => setTimeout(r, 4000));
        try {
          const token = await invoke<string>("read_api_token");
          setApiToken(token);
          setTokenReady(true);
        } catch {
          // Drugi błąd — sprawdź czy backend zgłosił crash przy starcie.
          try {
            const errorJson = await invoke<string>("read_startup_error");
            const info = JSON.parse(errorJson) as {code: string; message: string; timestamp?: string};
            setCrashInfo(info);
          } catch {
            setCrashInfo({
              code: "STARTUP-NO-RESPONSE",
              message: "Silnik nie odpowiada. Spróbuj uruchomić aplikację ponownie.",
            });
          }
          setTokenReady(true);
        }
      });
  }, [unlocked]);

  // ── Idle timer ────────────────────────────────────────────────────────────

  const resetIdle = useCallback(() => {
    setIdleWarning(false);
    setCountdown(60);
  }, []);

  useEffect(() => {
    if (!unlocked) return;

    let warnTimer:  ReturnType<typeof setTimeout>;
    let logoutTimer: ReturnType<typeof setTimeout>;
    let tickTimer:  ReturnType<typeof setInterval>;

    const reset = () => {
      clearTimeout(warnTimer);
      clearTimeout(logoutTimer);
      clearInterval(tickTimer);
      setIdleWarning(false);
      setCountdown(60);

      warnTimer = setTimeout(() => {
        setIdleWarning(true);
        setCountdown(60);
        tickTimer = setInterval(() => {
          setCountdown(prev => (prev <= 1 ? 1 : prev - 1));
        }, 1000);
      }, WARN_MS);

      logoutTimer = setTimeout(async () => {
        clearInterval(tickTimer);
        await invoke("clear_key").catch(() => {});
        setUnlocked(false);
        setApiToken("");
        setIdleWarning(false);
      }, IDLE_MS);
    };

    const EVENTS = ["mousemove", "keydown", "mousedown", "touchstart", "scroll"];
    EVENTS.forEach(e => window.addEventListener(e, reset, { passive: true }));
    reset();

    return () => {
      clearTimeout(warnTimer);
      clearTimeout(logoutTimer);
      clearInterval(tickTimer);
      EVENTS.forEach(e => window.removeEventListener(e, reset));
    };
  }, [unlocked]);

  // ── Render ────────────────────────────────────────────────────────────────

  if (expressMode) {
    return <ExpressModeScreen onExit={() => setExpressMode(false)} />;
  }

  if (!unlocked) {
    return <LockScreen onUnlock={() => setUnlocked(true)} onExpressMode={() => setExpressMode(true)} />;
  }

  // [CRASH-UX] Jeśli backend zgłosił błąd startu — pokaż ekran awarii.
  if (crashInfo) {
    return <CrashScreen code={crashInfo.code} message={crashInfo.message} timestamp={crashInfo.timestamp} />;
  }

  // [BUG-10] Czekaj na załadowanie tokenu — bez tego UI wysyła żądania z apiToken=""
  if (!tokenReady) {
    return (
      <div style={{
        height: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: T.bg, fontFamily: T.mono, fontSize: 11,
        color: T.muted, letterSpacing: "0.08em",
      }}>
        Ładowanie sesji…
      </div>
    );
  }

  return (
    <div style={{ position: "relative", height: "100vh" }}>

      {/* Idle warning banner */}
      {idleWarning && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, zIndex: 1000,
          background: T.amberBg, borderBottom: `2px solid ${T.amberBorder}`,
          padding: "8px 16px", display: "flex",
          justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontFamily: T.mono, fontSize: 10, color: T.amber, letterSpacing: "0.06em" }}>
            ⚠ Brak aktywności — sesja wygaśnie za {countdown}s · Klucz zostanie usunięty z pamięci
          </span>
          <button
            onClick={resetIdle}
            style={{
              padding: "4px 14px", fontFamily: T.mono, fontSize: 9,
              letterSpacing: "0.12em", textTransform: "uppercase",
              background: T.amberBg, border: `1px solid ${T.amber}`,
              color: T.amber, cursor: "pointer", borderRadius: 2,
            }}
          >
            Przedłuż sesję
          </button>
        </div>
      )}

      <MainLayout
        activeScreen={activeScreen}
        onNavigate={setActiveScreen}
        idleWarning={idleWarning}
        apiToken={apiToken}
        demaskPse={demaskPse}
        onDemask={(pse: string) => {
          setDemaskPse(pse);
          setActiveScreen("depseudonimizuj");
        }}
      />
    </div>
  );
}
