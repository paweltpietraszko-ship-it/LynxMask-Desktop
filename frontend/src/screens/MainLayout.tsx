// Pseudominizer — MainLayout.tsx  v2.3
// ============================================================
// ZMIANY W TEJ WERSJI (v2.2):
//   [UI-SIDEBAR-04] Logo responsywne na motyw
//     Ciemny: ikona PSE — białe tło, niebieski tekst PSE, nazwa biała/lekka
//     Jasny: ikona PSE — niebieskie tło, biały tekst PSE, nazwa niebieska
//     Efekt: sidebar ciemny jest lekki, jasny ma charakter
//   [UI-SIDEBAR-05] Nav ciemny — kolory lżejsze
//     Nieaktywny: T.textSecondary (jasny, czytelny) nie blueLight
//     Aktywny: #ffffff bold — wyraźny bez dominowania
// ============================================================
// ZMIANY W v2.1: [UI-SIDEBAR-02/03] Brak linii, ikona PSE
// ZMIANY W v2.0: [UI-SIDEBAR-01] Jednolity kolor atramentowy
// ZMIANY W v1.9: [UI-FONT-01] Czcionki sidebar
// ZMIANY W v1.8: [UI-THEME-01] Przełącznik motywu
// ============================================================

import { useState, useEffect, useReducer } from "react";
import { T, applyTheme, type ThemeMode } from "../theme";
import type { Screen } from "../App";
import Pseudonimizuj     from "./Pseudonimizuj";
import Biblioteka        from "./Biblioteka";
import Depseudonimizuj   from "./Depseudonimizuj";
import SecurityScreen    from "./SecurityScreen";

const API = "http://127.0.0.1:8765";
const THEME_KEY = "lynxmask_theme";

const NAV: { id: Screen; label: string }[] = [
  { id: "pseudonimizuj",   label: "Zamaskuj"       },
  { id: "biblioteka",      label: "Biblioteka"     },
  { id: "depseudonimizuj", label: "Odmaskuj"       },
  { id: "security",        label: "Zabezpieczenia" },
];

function NavBtn({ label, active, onClick, isDark, disabled }: {
  label: string; active: boolean; onClick: () => void; isDark: boolean; disabled?: boolean;
}) {
  const colorActive   = isDark ? "#ffffff"       : T.blue;
  const colorInactive = isDark ? T.textSecondary : T.blueLight;
  const colorHover    = isDark ? "#ffffff"       : T.blue;
  const colorDisabled = isDark ? "#3a3f4a"       : "#b0bac8";

  if (disabled) {
    return (
      <div
        title="Dostępne w pełnej wersji — zaloguj się"
        style={{
          display: "block", width: "100%",
          padding: "10px 16px",
          fontSize: 15, fontWeight: 400,
          fontFamily: T.sans,
          color: colorDisabled,
          borderRadius: 6,
          cursor: "not-allowed",
          userSelect: "none",
          boxSizing: "border-box",
        }}
      >
        {label}
        <span style={{
          marginLeft: 6, fontSize: 10, fontFamily: T.mono,
          letterSpacing: "0.06em", color: colorDisabled, opacity: 0.7,
        }}>🔒</span>
      </div>
    );
  }

  return (
    <button
      onClick={onClick}
      style={{
        display: "block", width: "100%",
        padding: "10px 16px",
        border: "none",
        textAlign: "left",
        cursor: "pointer",
        fontSize: 15,
        fontWeight: active ? 600 : 400,
        fontFamily: T.sans,
        color:      active ? colorActive : colorInactive,
        background: active ? T.activeNav : "transparent",
        borderRadius: 6,
        boxShadow:  active ? `inset -3px 0 0 ${T.blue}` : "none",
        transition: "color 0.12s, background 0.12s",
      }}
      onMouseEnter={e => { if (!active) { e.currentTarget.style.color = colorHover; e.currentTarget.style.background = T.activeNav; } }}
      onMouseLeave={e => { if (!active) { e.currentTarget.style.color = colorInactive; e.currentTarget.style.background = "transparent"; } }}
    >
      {label}
    </button>
  );
}

function ScreenContent({
  screen, apiToken, demaskPse, onDemask,
}: {
  screen:    Screen;
  apiToken:  string;
  demaskPse: string | null;
  onDemask:  (pse: string) => void;
}) {
  return (
    <>
      <div style={{ display: screen === "pseudonimizuj"   ? "block" : "none", height: "100%" }}>
        <Pseudonimizuj apiToken={apiToken} />
      </div>
      <div style={{ display: screen === "biblioteka"      ? "block" : "none", height: "100%" }}>
        <Biblioteka visible={screen === "biblioteka"} apiToken={apiToken} onDemask={onDemask} />
      </div>
      <div style={{ display: screen === "depseudonimizuj" ? "block" : "none", height: "100%" }}>
        <Depseudonimizuj apiToken={apiToken} initialPse={demaskPse ?? undefined} />
      </div>
      <div style={{ display: screen === "security"        ? "block" : "none", height: "100%" }}>
        <SecurityScreen />
      </div>
    </>
  );
}

interface Props {
  activeScreen:   Screen;
  onNavigate:     (s: Screen) => void;
  idleWarning:    boolean;
  apiToken:       string;
  expressMode?:   boolean;
  onExitExpress?: () => void;
  demaskPse:      string | null;
  onDemask:       (pse: string) => void;
}

export default function MainLayout({ activeScreen, onNavigate, idleWarning, apiToken, expressMode, onExitExpress, demaskPse, onDemask }: Props) {
  const [apiAlive,   setApiAlive]   = useState(true);
  const [appVersion, setAppVersion] = useState("v1.0-dev");
  const [themeMode,  setThemeMode]  = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return (saved === "light" || saved === "dark") ? saved : "dark";
  });
  const [, forceUpdate] = useReducer(x => x + 1, 0);
  const isDark = themeMode === "dark";

  useEffect(() => {
    applyTheme(themeMode);
    forceUpdate();
  }, [themeMode]);

  function toggleTheme() {
    const next: ThemeMode = isDark ? "light" : "dark";
    localStorage.setItem(THEME_KEY, next);
    setThemeMode(next);
  }

  useEffect(() => {
    fetch(`${API}/version`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d?.version) setAppVersion(d.version); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    async function check() {
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 5_000);
        const res = await fetch(`${API}/health`, { signal: ctrl.signal });
        clearTimeout(tid);
        setApiAlive(res.ok);
      } catch {
        setApiAlive(false);
      }
    }
    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  // [UI-SIDEBAR-04] Kolory logo zależne od motywu
  const logoBadgeBg   = isDark ? "#ffffff"   : T.blue;
  const logoBadgeText = isDark ? T.blue      : "#ffffff";
  const logoNameColor = isDark ? "#ffffff"   : T.blue;
  const logoVerColor  = isDark ? T.textMuted : T.blueLight;
  const navLabelColor = isDark ? T.textSecondary : T.blueLight;

  return (
    <div style={{
      display: "flex", height: "100vh",
      paddingTop: idleWarning ? 36 : 0,
      background: T.bg, transition: "padding-top 0.2s",
    }}>

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <div style={{
        width: 200, background: T.sidebar,
        borderRight: `1px solid ${T.border}`,
        display: "flex", flexDirection: "column", flexShrink: 0,
      }}>

        {/* Logo — przywrócone do oryginalnego stylu */}
        <div style={{ padding: "20px 16px 16px", borderBottom: `1px solid ${T.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{
              fontFamily: T.mono, fontSize: 9, letterSpacing: "0.18em",
              color: T.blue, border: `1px solid ${T.borderActive}`,
              padding: "2px 6px", borderRadius: 4, textTransform: "uppercase",
            }}>PSE</span>
            <span style={{ fontSize: 15, color: isDark ? T.textPrimary : T.blue, fontWeight: 300 }}>
              LynxMask Desktop
            </span>
          </div>
          <div style={{ fontSize: 11, color: T.textDim }}>
            {appVersion}
          </div>
        </div>

        {/* Nawigacja */}
        <div style={{ marginTop: 8, flex: 1, padding: "0 8px" }}>
          {NAV.map(({ id, label }) => {
            const lockedInExpress = expressMode && (id === "biblioteka" || id === "depseudonimizuj");
            return (
              <NavBtn
                key={id} label={label}
                active={activeScreen === id}
                onClick={() => !lockedInExpress && onNavigate(id)}
                isDark={isDark}
                disabled={lockedInExpress}
              />
            );
          })}
        </div>

        {/* Dolna sekcja */}
        <div style={{ borderTop: `1px solid ${T.border}`, padding: "12px 16px 8px" }}>

          {/* Banner Express Mode */}
          {expressMode && (
            <div style={{
              marginBottom: 12,
              background: T.amberBg,
              border: `1px solid ${T.amberBorder}`,
              borderRadius: 6,
              padding: "8px 10px",
            }}>
              <div style={{
                fontSize: 11, fontFamily: T.mono, color: T.amber,
                letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4,
              }}>
                ⚡ Tryb demonstracyjny
              </div>
              <div style={{ fontSize: 11, color: T.amber, lineHeight: 1.4, marginBottom: 6 }}>
                Biblioteka i odmaskowanie dostępne po zalogowaniu.
              </div>
              <button
                onClick={onExitExpress}
                style={{
                  width: "100%", padding: "5px 8px",
                  background: T.amber, border: "none", borderRadius: 4,
                  color: "#000", fontSize: 11, fontWeight: 600,
                  cursor: "pointer", fontFamily: T.mono,
                  letterSpacing: "0.06em",
                }}
              >
                → Zaloguj się
              </button>
            </div>
          )}

          {/* Triangulum */}
          <div style={{ marginBottom: 12 }}>
            <div style={{
              fontSize: 11, color: navLabelColor, textTransform: "uppercase",
              letterSpacing: "0.12em", marginBottom: 6, fontFamily: T.mono,
            }}>
              Powiązane
            </div>
            <button
              onClick={() => window.open("http://127.0.0.1:8000", "_blank")}
              style={{
                width: "100%", padding: "7px 10px",
                background: T.blueBg, border: `1px solid ${T.border}`,
                color: isDark ? T.blueLight : T.blue, fontSize: 13,
                cursor: "pointer", borderRadius: 6, textAlign: "left",
                transition: "border-color 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = T.blue)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = T.border)}
            >
              ↗ Triangulum v3.5
            </button>
            <div style={{ fontSize: 11, color: navLabelColor, marginTop: 3, fontFamily: T.mono }}>
              :8000 · Analiza multi-model
            </div>
          </div>

          {/* Przełącznik motywu */}
          <div style={{ marginBottom: 10 }}>
            <button
              onClick={toggleTheme}
              style={{
                width: "100%", padding: "7px 10px",
                background: "transparent",
                border: `1px solid ${T.border}`,
                borderRadius: 6, cursor: "pointer",
                display: "flex", alignItems: "center", gap: 8,
                fontSize: 13, color: navLabelColor,
                transition: "border-color 0.15s, color 0.15s",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = T.blue;
                e.currentTarget.style.color = isDark ? "#ffffff" : T.blue;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = T.border;
                e.currentTarget.style.color = navLabelColor;
              }}
            >
              <span style={{ fontSize: 14, lineHeight: 1 }}>
                {isDark ? "☀" : "🌙"}
              </span>
              <span>{isDark ? "Jasny motyw" : "Ciemny motyw"}</span>
            </button>
          </div>

          {/* Status API */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "2px 2px 4px" }}>
            <span style={{
              display: "inline-block", width: 7, height: 7,
              borderRadius: "50%",
              background: apiAlive ? T.green : T.red,
              flexShrink: 0, transition: "background 0.3s",
            }} />
            <span style={{ fontSize: 12, color: navLabelColor, fontFamily: T.mono }}>
              API :8765
            </span>
          </div>

        </div>
      </div>

      {/* ── Treść ───────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        <ScreenContent
          screen={activeScreen}
          apiToken={apiToken}
          demaskPse={demaskPse}
          onDemask={onDemask}
        />
      </div>

    </div>
  );
}
