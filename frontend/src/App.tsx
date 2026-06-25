// Pseudominizer — App.tsx  v1.4
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
  // [BUG-P4-03] PSE przekazywane z Biblioteki do Depseudonimizuj przy kliknięciu odpowiedzi AI.
  const [demaskPse,    setDemaskPse]    = useState<string | null>(null);

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
      return;
    }
    invoke<string>("read_api_token")
      .then(token => setApiToken(token))
      .catch(err => {
        // Logujemy błąd, ale nie blokujemy UI — backend może jeszcze startować.
        console.error("[TOKEN] Błąd odczytu api_token.txt:", err);
        setApiToken("");
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

  if (!unlocked) {
    return <LockScreen onUnlock={() => setUnlocked(true)} />;
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
