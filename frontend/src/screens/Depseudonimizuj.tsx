// Pseudominizer — Depseudonimizuj.tsx  v1.8
// ============================================================
// ZMIANY W TEJ WERSJI (v1.8):
//   [UI-FONT-01] Czcionki podniesione globalnie
// ============================================================
// ZMIANY W v1.7:
//   [UI-DEP-01] Terminologia nagłówka — linia ~115
//     "Depseudonimizuj tekst" → "Odmaskuj tekst"
//     Zgodnie z decyzją UI: Zamaskuj / Odmaskuj jako nazwy interfejsowe.
//     Kod backendowy (funkcje, endpointy) pozostaje bez zmian.
//   [UI-DEP-02] Pola tekstowe — pełna wysokość okna — linia ~125
//     Weryfikacja i upewnienie: grid flex:1, minHeight:0 na obu kolumnach,
//     textarea i div wynikowy mają flex:1 i minHeight:0.
//     Eliminuje czarną pustkę na dole ekranu widoczną na screenshocie.
// ============================================================
// Zachowane bez zmian:
//   - [BUG-P4-03] initialPse prop i useEffect ładujący PSE z Biblioteki
//   - [FIX-TOKEN-API] nagłówek X-Api-Token
//   - [BUG-6] restoreText() przez iterację Object.keys(map) — bez TOKEN_MATCH regex
//   - Cała logika: fetchMapForPse, restoreText, autodetekt PSE, debounce
//   - invoke("decrypt_data") / invoke("save_depseudo_result")
//   - Redesign wizualny z v1.5
// ============================================================

import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";

const API = "http://127.0.0.1:8765";

const PSE_DETECT  = /PSE-\d{4}-\d{4}/g;

interface DocOption {
  pse:        string;
  desc_plain: string;
}

async function decryptFromBase64(b64: string): Promise<string> {
  if (!b64) return "";
  const binary     = atob(b64);
  const ciphertext = Array.from(binary, (c: string) => c.charCodeAt(0));
  const plaintext: number[] = await invoke("decrypt_data", { ciphertext });
  return new TextDecoder().decode(new Uint8Array(plaintext));
}

async function fetchMapForPse(pse: string, token: string): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (token) headers["X-Api-Token"] = token;
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), 30_000);
  const res = await fetch(`${API}/archive/${pse}/blob`, { headers, signal: ctrl.signal });
  clearTimeout(tid);
  if (!res.ok) throw new Error(`Błąd pobierania mapy ${pse} (${res.status})`);
  const data = await res.json();
  const json = await decryptFromBase64(data.enc_blob);

  const parsed = JSON.parse(json);
  const tokens: { token: string; original: string }[] = Array.isArray(parsed)
    ? parsed
    : parsed.tokens;

  const map: Record<string, string> = {};
  for (const t of tokens) map[t.token] = t.original;
  return map;
}

// [BUG-6] Opcja B — iteracja po kluczach mapy zamiast TOKEN_MATCH regex
function restoreText(text: string, map: Record<string, string>): string {
  let result = text;
  for (const token of Object.keys(map)) {
    result = result.replaceAll(token, map[token]);
  }
  return result;
}

interface Props {
  apiToken?:   string;
  initialPse?: string; // [BUG-P4-03]
}

export default function Depseudonimizuj({ apiToken = "", initialPse }: Props) {
  const [inputText,    setInputText]    = useState("");
  const [outputText,   setOutputText]   = useState("");
  const [detectedPse,  setDetectedPse]  = useState("");
  const [selectedPse,  setSelectedPse]  = useState("");
  const [processing,   setProcessing]   = useState(false);
  const [error,        setError]        = useState("");
  const [copied,       setCopied]       = useState(false);
  const [savedPath,    setSavedPath]    = useState("");
  const [docs,         setDocs]         = useState<DocOption[]>([]);
  const [docsLoading,  setDocsLoading]  = useState(true);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // [BUG-P4-03] Gdy Biblioteka przekazuje PSE przez onDemask
  useEffect(() => {
    if (!initialPse) return;
    setSelectedPse(initialPse);
    setInputText(prev => {
      if (prev.trim()) {
        process(prev, initialPse);
      }
      return prev;
    });
  }, [initialPse]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    async function loadDocs() {
      try {
        const headers: Record<string, string> = {};
        if (apiToken) headers["X-Api-Token"] = apiToken;
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 30_000);
        const res  = await fetch(`${API}/archive`, { headers, signal: ctrl.signal });
        clearTimeout(tid);
        const data = await res.json();
        const raw  = data.documents ?? [];
        const opts: DocOption[] = await Promise.all(
          raw.map(async (d: { pse: string; description: string }) => ({
            pse:        d.pse,
            desc_plain: d.description
              ? await decryptFromBase64(d.description).catch(() => "")
              : "",
          }))
        );
        opts.sort((a, b) => b.pse.localeCompare(a.pse));
        setDocs(opts);
      } catch {
        // Dropdown będzie pusty
      } finally {
        setDocsLoading(false);
      }
    }
    loadDocs();
  }, [apiToken]);

  async function process(text: string, pse: string) {
    if (!text.trim() || !pse) { setOutputText(""); return; }
    setProcessing(true);
    setError("");
    try {
      const map      = await fetchMapForPse(pse, apiToken);
      const restored = restoreText(text, map);
      setOutputText(restored);
    } catch (e) {
      setError(String(e));
      setOutputText("");
    } finally {
      setProcessing(false);
    }
  }

  function activePse(autodetect: string, manual: string): string {
    return autodetect || manual;
  }

  function handleInput(text: string) {
    setInputText(text);
    setCopied(false);
    setSavedPath("");

    PSE_DETECT.lastIndex = 0;
    const auto = PSE_DETECT.exec(text)?.[0] ?? "";
    setDetectedPse(auto);

    const pse = activePse(auto, selectedPse);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => process(text, pse), 400);
  }

  function handleSelectPse(pse: string) {
    setSelectedPse(pse);
    setCopied(false);
    setSavedPath("");
    const pseToUse = activePse(detectedPse, pse);
    if (inputText.trim() && pseToUse) process(inputText, pseToUse);
  }

  async function handleSave() {
    if (!outputText) return;
    const pse = currentPse;
    if (!pse) { setError("Brak kodu PSE — nie można zapisać."); return; }
    try {
      const path: string = await invoke("save_depseudo_result", { pse, text: outputText });
      setSavedPath(path);
      setTimeout(() => setSavedPath(""), 4000);
    } catch (e) {
      setError(`Błąd zapisu: ${String(e)}`);
    }
  }

  async function handleCopy() {
    if (!outputText) return;
    try {
      await navigator.clipboard.writeText(outputText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Błąd kopiowania.");
    }
  }

  const currentPse = activePse(detectedPse, selectedPse);

  return (
    <div style={{
      padding: 24, height: "100vh", boxSizing: "border-box",
      display: "flex", flexDirection: "column", overflow: "hidden",
    }}>

      {/* [UI-DEP-01] Nagłówek — zaktualizowana terminologia */}
      <div style={{
        fontSize: 13, letterSpacing: "0.12em", fontFamily: T.mono,
        color: T.blue, textTransform: "uppercase", marginBottom: 16, flexShrink: 0,
      }}>
        Odmaskuj tekst
      </div>

      {/* [UI-DEP-02] Dwa pola tekstowe — pełna dostępna wysokość */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16,
        flex: 1, minHeight: 0, marginBottom: 12,
      }}>

        {/* Lewe — tekst z tokenami */}
        <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{
            fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
            letterSpacing: "0.1em", marginBottom: 8, flexShrink: 0,
          }}>
            Tekst z tokenami PSE
          </div>
          <textarea
            value={inputText}
            onChange={e => handleInput(e.target.value)}
            placeholder={"Wklej odpowiedź AI z tokenami FIRMA_001, OSOBA_001...\n\nJeśli tekst zawiera PSE-XXXX-XXXX — dokument\nwykryty automatycznie.\n\nJeśli nie — wybierz dokument ręcznie poniżej."}
            style={{
              flex: 1,
              boxSizing: "border-box",
              padding: "12px 14px",
              fontFamily: T.mono, fontSize: 15, lineHeight: 1.7,
              resize: "none", background: T.surface,
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              color: T.textSecondary, outline: "none",
              minHeight: 0,
            }}
          />
        </div>

        {/* Prawe — tekst odtworzony */}
        <div style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{
            fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
            letterSpacing: "0.1em", marginBottom: 8, flexShrink: 0,
          }}>
            Tekst odtworzony
          </div>
          <div style={{
            flex: 1,
            boxSizing: "border-box",
            padding: "12px 14px",
            fontFamily: T.sans, fontSize: 16, lineHeight: 1.7,
            background: outputText ? T.surface : T.bg,
            border: `1px solid ${outputText ? T.greenBorder : T.border}`,
            borderRadius: 8,
            color: T.textPrimary,
            overflowY: "auto", whiteSpace: "pre-wrap", wordBreak: "break-word",
            userSelect: "text", transition: "border-color 0.2s",
            minHeight: 0,
          }}>
            {processing ? (
              <span style={{ fontFamily: T.mono, fontSize: 13, color: T.textMuted }}>
                ▸ Deszyfruje i podmienia tokeny...
              </span>
            ) : outputText ? outputText : (
              <span style={{ fontFamily: T.mono, fontSize: 13, color: T.textMuted }}>
                // Odtworzony tekst pojawi się tutaj
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Dolny pasek — PSE + przyciski */}
      <div style={{ flexShrink: 0 }}>
        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: 8, padding: "10px 14px",
          display: "flex", alignItems: "center", gap: 12, marginBottom: 0,
        }}>

          {/* PSE info / select */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 0 }}>
            {detectedPse ? (
              <span style={{ fontFamily: T.mono, fontSize: 13, color: T.green, whiteSpace: "nowrap" }}>
                ✓ PSE: <span style={{ color: T.blueLight }}>{detectedPse}</span>
              </span>
            ) : (
              <span style={{ fontFamily: T.mono, fontSize: 13, color: T.amber, whiteSpace: "nowrap" }}>
                Brak PSE —
              </span>
            )}

            {!detectedPse && (
              <select
                value={selectedPse}
                onChange={e => handleSelectPse(e.target.value)}
                style={{
                  flex: 1, background: T.bg,
                  border: `1px solid ${selectedPse ? T.blue : T.border}`,
                  borderRadius: 6,
                  color: selectedPse ? T.textPrimary : T.textMuted,
                  fontSize: 15, padding: "5px 10px",
                  cursor: "pointer", minWidth: 0, outline: "none",
                }}
              >
                <option value="">Wybierz dokument z biblioteki...</option>
                {docsLoading ? (
                  <option disabled>Ładuję...</option>
                ) : docs.length === 0 ? (
                  <option disabled>Brak dokumentów w bibliotece</option>
                ) : (
                  docs.map(d => (
                    <option key={d.pse} value={d.pse}>
                      {d.pse}{d.desc_plain ? ` — ${d.desc_plain}` : ""}
                    </option>
                  ))
                )}
              </select>
            )}
          </div>

          {/* Przyciski akcji */}
          <button
            onClick={handleSave}
            disabled={!outputText || !currentPse}
            style={{
              padding: "6px 16px", fontSize: 13,
              background: outputText && currentPse ? T.surface : T.bg,
              border: `1px solid ${outputText && currentPse ? T.blue : T.border}`,
              borderRadius: 6,
              color: outputText && currentPse ? (savedPath ? T.green : T.blueLight) : T.textMuted,
              cursor: outputText && currentPse ? "pointer" : "not-allowed",
              whiteSpace: "nowrap", transition: "background 0.15s",
            }}
          >
            {savedPath ? "✓ Zapisano" : "↓ Zapisz plik"}
          </button>

          <button
            onClick={handleCopy}
            disabled={!outputText}
            style={{
              padding: "6px 16px", fontSize: 13,
              background: outputText ? T.blue : T.bg,
              border: `1px solid ${outputText ? T.blue : T.border}`,
              borderRadius: 6,
              color: outputText ? (copied ? T.green : "#fff") : T.textMuted,
              cursor: outputText ? "pointer" : "not-allowed",
              fontWeight: 500, whiteSpace: "nowrap", transition: "background 0.15s",
            }}
          >
            {copied ? "✓ Skopiowano" : "↗ Kopiuj"}
          </button>
        </div>

        {/* Status */}
        {savedPath && (
          <div style={{ fontSize: 13, color: T.green, padding: "4px 14px", fontFamily: T.mono }}>
            ✓ Zapisano: {savedPath}
          </div>
        )}
        {!detectedPse && selectedPse && !savedPath && (
          <div style={{ fontSize: 13, color: T.textMuted, padding: "4px 14px", fontFamily: T.mono }}>
            ▸ Używam mapy z {selectedPse} — wskazanego ręcznie
          </div>
        )}

        {/* Błąd */}
        {error && (
          <div style={{
            background: T.redBg, border: `1px solid ${T.redBorder}`,
            borderRadius: 8, padding: "10px 14px", marginTop: 8,
            fontSize: 15, color: T.red,
          }}>
            ✕ {error}
          </div>
        )}
      </div>

    </div>
  );
}
