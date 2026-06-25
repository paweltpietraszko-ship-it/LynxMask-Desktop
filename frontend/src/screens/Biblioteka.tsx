// Pseudominizer — Biblioteka.tsx  v1.6
// ============================================================
// ZMIANY W TEJ WERSJI: Potok 4 Biblioteka — drzewko odpowiedzi AI
// ============================================================
// Dodane stany (linie ~75–82):
//   expandedPse    — który PSE ma rozwinięte drzewko odpowiedzi
//   responsesCache — Record<pse, string[]> cache plików per PSE
//   responsesError — Record<pse, boolean> flaga błędu odczytu
//   respLoading    — który PSE jest w trakcie ładowania listy
//   activeRespKey  — klucz "pse/filename" aktywnego menu inline
//   actionLoading  — blokada podczas Kopiuj/Drukuj
//
// Dodane funkcje (linie ~116–185):
//   handleExpandPse(pse)          — toggle drzewka + lazy load przez
//                                   invoke("list_depseudo_responses")
//   handleRespCopy(pse, filename) — invoke("read_depseudo_response") → clipboard
//   handleRespPrint(pse, filename)— invoke("read_depseudo_response") → iframe.print()
//   handleRespDemask(pse)         — callback onDemask(pse) → nawigacja
//
// Zmieniony render (linie ~320–400):
//   Każdy wiersz dokumentu dostał chevron ▶/▼ w pierwszej kolumnie.
//   Pod wierszem: sekcja drzewka odpowiedzi (jeśli expandedPse === doc.pse).
//   Kolejność sekcji per dokument: wiersz → drzewko → podgląd tekstu.
//   Drzewko i podgląd mogą być otwarte jednocześnie.
//
// Zmieniony Props (linia ~70):
//   Dodano onDemask?: (pse: string) => void
//
// Zachowane bez zmian:
//   [FIX-TOKEN-API] nagłówek X-Api-Token
//   [FIX-DELETE-CONFIRM] modal potwierdzenia przed usunięciem
//   Cała logika: loadDocs, handlePreview, handleCopy, handleDelete,
//   handleAskDocSelect, handleAskCopy, filtered
//   GET /archive, DELETE /archive/{pse} — nie dotknięte
//
// Poprzednia wersja: v1.5 [redesign wizualny]
// ============================================================

import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";

const API = "http://127.0.0.1:8765";

interface DocRecord {
  pse:         string;
  token_count: number;
  created_at:  string;
  description: string;
  enc_exists:  boolean;
}

interface DocDisplay extends DocRecord {
  desc_plain: string;
}

async function decryptFromBase64(b64: string): Promise<string> {
  if (!b64) return "";
  try {
    const binary     = atob(b64);
    const ciphertext = Array.from(binary, (c: string) => c.charCodeAt(0));
    const plaintext: number[] = await invoke("decrypt_data", { ciphertext });
    return new TextDecoder().decode(new Uint8Array(plaintext));
  } catch {
    return "(błąd deszyfrowania)";
  }
}

function authHeaders(token: string): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h["X-Api-Token"] = token;
  return h;
}

async function fetchAnonymizedText(pse: string, token: string): Promise<string> {
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), 30_000);
  const res = await fetch(`${API}/archive/${pse}/blob`, {
    headers: authHeaders(token),
    signal: ctrl.signal,
  });
  clearTimeout(tid);
  if (!res.ok) throw new Error(`Błąd pobierania (${res.status})`);
  const data = await res.json();
  const json = await decryptFromBase64(data.enc_blob);
  try {
    const parsed = JSON.parse(json);
    if (Array.isArray(parsed)) return "(stary format — tekst niedostępny)";
    return parsed.anonymized_preview ?? "(brak tekstu)";
  } catch {
    return "(błąd parsowania)";
  }
}

interface Props {
  visible?:   boolean;
  apiToken?:  string;
  onDemask?:  (pse: string) => void;
}

export default function Biblioteka({ visible, apiToken = "", onDemask }: Props) {
  const [docs,          setDocs]          = useState<DocDisplay[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [error,         setError]         = useState("");
  const [search,        setSearch]        = useState("");
  const [deleting,      setDeleting]      = useState<string | null>(null);
  const [previewPse,    setPreviewPse]    = useState<string | null>(null);
  const [previewText,   setPreviewText]   = useState("");
  const [previewLoad,   setPreviewLoad]   = useState(false);
  const [copied,        setCopied]        = useState<string | null>(null);
  const [askDoc,        setAskDoc]        = useState("");
  const [askQuestion,   setAskQuestion]   = useState("");
  const [askText,       setAskText]       = useState("");
  const [askLoading,    setAskLoading]    = useState(false);
  const [askCopied,     setAskCopied]     = useState(false);
  const [confirmPse,    setConfirmPse]    = useState<string | null>(null);

  // --- Stany drzewka odpowiedzi ---
  const [expandedPse,    setExpandedPse]    = useState<string | null>(null);
  const [responsesCache, setResponsesCache] = useState<Record<string, string[]>>({});
  const [responsesError, setResponsesError] = useState<Record<string, boolean>>({});
  const [respLoading,    setRespLoading]    = useState<string | null>(null);
  const [activeRespKey,  setActiveRespKey]  = useState<string | null>(null);
  const [actionLoading,  setActionLoading]  = useState(false);

  async function loadDocs() {
    setLoading(true);
    setError("");
    setPreviewPse(null);
    setPreviewText("");
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res  = await fetch(`${API}/archive`, { headers: authHeaders(apiToken), signal: ctrl.signal });
      clearTimeout(tid);
      const data = await res.json();
      const raw: DocRecord[] = data.documents ?? [];
      const decrypted = await Promise.all(
        raw.map(async doc => ({
          ...doc,
          desc_plain: doc.description ? await decryptFromBase64(doc.description) : "",
        }))
      );
      decrypted.sort((a, b) => b.created_at.localeCompare(a.created_at));
      setDocs(decrypted);
    } catch {
      setError("Błąd połączenia z backendem.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (visible !== false) loadDocs();
  }, [visible, apiToken]);

  // --- Obsługa podglądu tekstu (niezmieniona) ---

  async function handlePreview(pse: string) {
    if (previewPse === pse) { setPreviewPse(null); setPreviewText(""); return; }
    setPreviewPse(pse);
    setPreviewText("");
    setPreviewLoad(true);
    try {
      setPreviewText(await fetchAnonymizedText(pse, apiToken));
    } catch (e) {
      setPreviewText(`(${String(e)})`);
    } finally {
      setPreviewLoad(false);
    }
  }

  async function handleCopy(text: string, id: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setError("Błąd kopiowania.");
    }
  }

  function handleDelete(pse: string) {
    if (deleting) return;
    setConfirmPse(pse);
  }

  async function handleDeleteConfirmed() {
    if (!confirmPse || deleting) return;
    const pse = confirmPse;
    setConfirmPse(null);
    setDeleting(pse);
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res  = await fetch(`${API}/archive/${pse}`, {
        method: "DELETE", headers: authHeaders(apiToken), signal: ctrl.signal,
      });
      clearTimeout(tid);
      const data = await res.json();
      if (data.ok) {
        setDocs(prev => prev.filter(d => d.pse !== pse));
        if (previewPse === pse) { setPreviewPse(null); setPreviewText(""); }
        if (expandedPse === pse) setExpandedPse(null);
      } else {
        setError(data.error ?? "Błąd usuwania.");
      }
    } catch {
      setError("Błąd połączenia.");
    } finally {
      setDeleting(null);
    }
  }

  async function handleAskDocSelect(pse: string) {
    setAskDoc(pse);
    setAskText("");
    setAskCopied(false);
    if (!pse) return;
    setAskLoading(true);
    try {
      setAskText(await fetchAnonymizedText(pse, apiToken));
    } catch {
      setAskText("(błąd pobierania tekstu)");
    } finally {
      setAskLoading(false);
    }
  }

  async function handleAskCopy() {
    if (!askDoc || !askQuestion.trim()) return;
    const built = [
      "[PSE: " + askDoc + "]",
      "",
      askQuestion.trim(),
      "",
      "--- Treść dokumentu ---",
      askText || "(ładowanie...)",
    ].join("\n");
    try {
      await navigator.clipboard.writeText(built);
      setAskCopied(true);
      setTimeout(() => setAskCopied(false), 2500);
    } catch {
      setError("Błąd kopiowania.");
    }
  }

  // --- Obsługa drzewka odpowiedzi ---

  async function handleExpandPse(pse: string) {
    if (expandedPse === pse) {
      setExpandedPse(null);
      setActiveRespKey(null);
      return;
    }
    setExpandedPse(pse);
    setActiveRespKey(null);
    // Lazy load: ładuj tylko jeśli nie ma w cache i nie było błędu
    if (responsesCache[pse] !== undefined || responsesError[pse]) return;
    setRespLoading(pse);
    try {
      const files = await invoke<string[]>("list_depseudo_responses", { pse });
      setResponsesCache(prev => ({ ...prev, [pse]: files }));
    } catch {
      setResponsesError(prev => ({ ...prev, [pse]: true }));
    } finally {
      setRespLoading(null);
    }
  }

  async function handleRespCopy(pse: string, filename: string) {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      const text = await invoke<string>("read_depseudo_response", { pse, filename });
      await navigator.clipboard.writeText(text);
      const key = pse + "/" + filename;
      setCopied("resp-" + key);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setError("Błąd kopiowania odpowiedzi.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRespPrint(pse: string, filename: string) {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      const text = await invoke<string>("read_depseudo_response", { pse, filename });
      const safe = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      const iframe = document.createElement("iframe");
      iframe.style.cssText = "position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;";
      document.body.appendChild(iframe);
      const doc = iframe.contentDocument!;
      doc.open();
      doc.write(
        `<!DOCTYPE html><html><head><title>${pse} — ${filename}</title></head>` +
        `<body style="margin:28px;font-family:monospace;font-size:11pt;line-height:1.7">` +
        `<p style="font-size:9pt;color:#888;margin-bottom:16px">${pse} / ${filename}</p>` +
        `<pre style="white-space:pre-wrap;word-break:break-word">${safe}</pre>` +
        `</body></html>`
      );
      doc.close();
      iframe.contentWindow!.focus();
      iframe.contentWindow!.print();
      setTimeout(() => {
        if (document.body.contains(iframe)) document.body.removeChild(iframe);
      }, 4000);
    } catch {
      setError("Błąd drukowania.");
    } finally {
      setActionLoading(false);
    }
  }

  function handleRespDemask(pse: string) {
    setActiveRespKey(null);
    if (onDemask) onDemask(pse);
  }

  const filtered = docs.filter(d =>
    !search ||
    d.desc_plain.toLowerCase().includes(search.toLowerCase()) ||
    d.pse.toLowerCase().includes(search.toLowerCase())
  );

  // ── Render ────────────────────────────────────────────────

  return (
    <div style={{ padding: 24, height: "100vh", overflowY: "auto", boxSizing: "border-box" }}>

      {/* Nagłówek + wyszukiwarka */}
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 20,
      }}>
        <div style={{
          fontSize: 11, letterSpacing: "0.12em", fontFamily: T.mono,
          color: T.blue, textTransform: "uppercase",
        }}>
          Biblioteka ({loading ? "…" : docs.length})
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Szukaj po opisie lub PSE..."
            style={{
              width: 240, padding: "7px 12px",
              background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: 6, color: T.textPrimary,
              fontSize: 13, outline: "none",
            }}
          />
          <button
            onClick={loadDocs}
            style={{
              padding: "7px 14px",
              background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: 6, color: T.textMuted,
              fontSize: 13, cursor: "pointer",
              transition: "border-color 0.15s, color 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = T.blue; e.currentTarget.style.color = T.blueLight; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; }}
          >
            ↺ Odśwież
          </button>
        </div>
      </div>

      {/* Lista dokumentów */}
      <div style={{
        border: `1px solid ${T.border}`, borderRadius: 8,
        overflow: "hidden", marginBottom: 20,
      }}>
        {/* Nagłówek tabeli */}
        <div style={{
          display: "grid", gridTemplateColumns: "28px 1fr 100px 60px 170px",
          gap: 8, padding: "8px 16px",
          background: T.surface, borderBottom: `1px solid ${T.border}`,
          fontSize: 11, color: T.textMuted, textTransform: "uppercase",
          letterSpacing: "0.1em", fontFamily: T.mono,
        }}>
          <span></span>
          <span>Opis dokumentu</span>
          <span>Data</span>
          <span>Tokeny</span>
          <span></span>
        </div>

        {loading ? (
          <div style={{ padding: "24px 16px", fontSize: 13, color: T.textMuted, fontFamily: T.mono }}>
            ▸ Deszyfruje...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "24px 16px", fontSize: 13, color: T.textMuted }}>
            {search ? "Brak wyników." : "Biblioteka jest pusta."}
          </div>
        ) : (
          filtered.map((doc, i) => {
            const isExpanded   = expandedPse === doc.pse;
            const responses    = responsesCache[doc.pse];
            const hasRespError = responsesError[doc.pse];
            const isLoading    = respLoading === doc.pse;

            return (
              <div key={doc.pse}>

                {/* Wiersz dokumentu */}
                <div style={{
                  display: "grid", gridTemplateColumns: "28px 1fr 100px 60px 170px",
                  gap: 8, padding: "10px 16px", alignItems: "center",
                  borderTop: i === 0 ? "none" : `1px solid ${T.border}`,
                  background: isExpanded ? T.activeNav : (previewPse === doc.pse ? T.activeNav : (i % 2 === 0 ? "transparent" : T.surface)),
                }}>

                  {/* Chevron — toggle drzewka odpowiedzi */}
                  <button
                    onClick={() => handleExpandPse(doc.pse)}
                    title={isExpanded ? "Zwiń odpowiedzi" : "Pokaż odpowiedzi AI"}
                    style={{
                      background: "none", border: "none",
                      padding: "2px 0", cursor: "pointer",
                      color: isExpanded ? T.blueLight : T.textMuted,
                      fontSize: 10, lineHeight: 1,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      transition: "color 0.15s",
                    }}
                  >
                    <span style={{
                      display: "inline-block",
                      transform: isExpanded ? "rotate(90deg)" : "none",
                      transition: "transform 0.15s",
                    }}>▶</span>
                  </button>

                  {/* Opis + PSE */}
                  <div style={{ minWidth: 0 }}>
                    <div style={{
                      fontSize: 14, color: T.textPrimary, fontWeight: 500,
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {doc.desc_plain || "(bez opisu)"}
                    </div>
                    <div style={{ fontFamily: T.mono, fontSize: 11, color: T.blueLight, marginTop: 2 }}>
                      {doc.pse}
                    </div>
                  </div>

                  <span style={{ fontFamily: T.mono, fontSize: 12, color: T.textSecondary }}>
                    {doc.created_at?.slice(0, 10) ?? "—"}
                  </span>
                  <span style={{ fontFamily: T.mono, fontSize: 12, color: T.textSecondary }}>
                    {doc.token_count}
                  </span>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      onClick={() => handlePreview(doc.pse)}
                      style={{
                        padding: "4px 10px", fontSize: 12,
                        background: previewPse === doc.pse ? T.activeNav : T.blueBg,
                        border: `1px solid ${T.borderActive}`,
                        color: T.blueLight, cursor: "pointer", borderRadius: 6,
                      }}
                    >
                      {previewPse === doc.pse ? "▲ Zwiń" : "↗ Podgląd"}
                    </button>
                    <button
                      onClick={() => handleDelete(doc.pse)}
                      disabled={!!deleting}
                      style={{
                        padding: "4px 10px", fontSize: 12,
                        background: T.redBg, border: `1px solid ${T.redBorder}`,
                        color: T.red, cursor: deleting ? "not-allowed" : "pointer",
                        borderRadius: 6, opacity: deleting === doc.pse ? 0.5 : 1,
                      }}
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {/* Drzewko odpowiedzi AI — lazy, otwiera się po kliknięciu chevronu */}
                {isExpanded && (
                  <div style={{
                    borderTop: `1px solid ${T.border}`,
                    background: T.surface,
                    padding: "10px 16px 12px 52px",
                  }}>
                    {isLoading ? (
                      <div style={{ fontSize: 12, color: T.textMuted, fontFamily: T.mono }}>
                        ▸ Szukam odpowiedzi...
                      </div>
                    ) : hasRespError ? (
                      <div style={{ fontSize: 12, color: T.red }}>
                        Nie można wczytać odpowiedzi.
                      </div>
                    ) : !responses || responses.length === 0 ? (
                      <div style={{ fontSize: 12, color: T.textMuted }}>
                        Brak odpowiedzi AI dla tego dokumentu.
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                        {responses.map(filename => {
                          const key      = doc.pse + "/" + filename;
                          const isActive = activeRespKey === key;
                          const respCopied = copied === "resp-" + key;

                          return (
                            <div key={filename}>

                              {/* Wiersz odpowiedzi */}
                              <button
                                onClick={() => setActiveRespKey(isActive ? null : key)}
                                style={{
                                  display: "flex", alignItems: "center", gap: 8,
                                  width: "100%", padding: "5px 8px",
                                  background: isActive ? T.activeNav : "transparent",
                                  border: `1px solid ${isActive ? T.borderActive : "transparent"}`,
                                  borderRadius: 6, cursor: "pointer", textAlign: "left",
                                  transition: "background 0.1s, border-color 0.1s",
                                }}
                              >
                                <span style={{
                                  color: T.textMuted, fontSize: 10, fontFamily: T.mono,
                                  flexShrink: 0, userSelect: "none",
                                }}>
                                  └─
                                </span>
                                <span style={{
                                  fontSize: 13, fontFamily: T.mono,
                                  color: isActive ? T.blueLight : T.textSecondary,
                                }}>
                                  {filename}
                                </span>
                                {isActive && (
                                  <span style={{
                                    marginLeft: "auto", fontSize: 10,
                                    color: T.textMuted, flexShrink: 0,
                                  }}>
                                    ▲
                                  </span>
                                )}
                              </button>

                              {/* Menu inline pod aktywną odpowiedzią */}
                              {isActive && (
                                <div style={{
                                  display: "flex", gap: 8,
                                  padding: "7px 8px 7px 30px",
                                  borderLeft: `2px solid ${T.borderActive}`,
                                  marginLeft: 8, marginBottom: 2,
                                }}>
                                  <button
                                    onClick={() => handleRespDemask(doc.pse)}
                                    disabled={!onDemask}
                                    title={onDemask ? "Otwórz w Odmaskuj" : "Brak połączenia z ekranem Odmaskuj"}
                                    style={{
                                      padding: "5px 14px", fontSize: 12, fontWeight: 500,
                                      background: T.blue, border: `1px solid ${T.blue}`,
                                      borderRadius: 6, color: "#fff",
                                      cursor: onDemask ? "pointer" : "not-allowed",
                                      opacity: onDemask ? 1 : 0.45,
                                      transition: "opacity 0.15s",
                                    }}
                                  >
                                    ↺ Odmaskuj
                                  </button>
                                  <button
                                    onClick={() => handleRespCopy(doc.pse, filename)}
                                    disabled={actionLoading}
                                    style={{
                                      padding: "5px 14px", fontSize: 12,
                                      background: T.surface, border: `1px solid ${T.border}`,
                                      borderRadius: 6,
                                      color: respCopied ? T.green : T.textMuted,
                                      cursor: actionLoading ? "not-allowed" : "pointer",
                                      transition: "color 0.15s",
                                    }}
                                  >
                                    {respCopied ? "✓ Skopiowano" : "↗ Kopiuj"}
                                  </button>
                                  <button
                                    onClick={() => handleRespPrint(doc.pse, filename)}
                                    disabled={actionLoading}
                                    style={{
                                      padding: "5px 14px", fontSize: 12,
                                      background: T.surface, border: `1px solid ${T.border}`,
                                      borderRadius: 6, color: T.textMuted,
                                      cursor: actionLoading ? "not-allowed" : "pointer",
                                    }}
                                  >
                                    ⎙ Drukuj
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* Podgląd tekstu pseudonimizowanego (istniejący, niezmieniony) */}
                {previewPse === doc.pse && (
                  <div style={{
                    borderTop: `1px solid ${T.borderActive}`,
                    background: T.blueBg, padding: "14px 16px",
                  }}>
                    {previewLoad ? (
                      <div style={{ fontSize: 13, color: T.textMuted, fontFamily: T.mono }}>
                        ▸ Deszyfruje tekst...
                      </div>
                    ) : (
                      <>
                        <div style={{
                          display: "flex", justifyContent: "space-between",
                          alignItems: "center", marginBottom: 10,
                        }}>
                          <div style={{
                            fontSize: 11, color: T.textMuted,
                            textTransform: "uppercase", letterSpacing: "0.1em",
                          }}>
                            Pseudonimizowany tekst
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button
                              onClick={() => handleCopy(doc.pse, "pse-" + doc.pse)}
                              style={{
                                padding: "4px 12px", fontSize: 12,
                                background: T.surface, border: `1px solid ${T.border}`,
                                color: copied === "pse-" + doc.pse ? T.green : T.textMuted,
                                cursor: "pointer", borderRadius: 6,
                              }}
                            >
                              {copied === "pse-" + doc.pse ? "✓ PSE" : "Kopiuj PSE"}
                            </button>
                            <button
                              onClick={() => handleCopy(previewText, "text-" + doc.pse)}
                              disabled={!previewText || previewText.startsWith("(stary")}
                              style={{
                                padding: "4px 12px", fontSize: 12,
                                background: T.blue, border: `1px solid ${T.blue}`,
                                color: copied === "text-" + doc.pse ? T.green : "#fff",
                                cursor: "pointer", borderRadius: 6, fontWeight: 500,
                              }}
                            >
                              {copied === "text-" + doc.pse ? "✓ Skopiowano" : "↗ Kopiuj tekst"}
                            </button>
                          </div>
                        </div>
                        <div style={{
                          background: T.surface, border: `1px solid ${T.border}`,
                          borderRadius: 8, padding: "12px 14px",
                          fontSize: 13, lineHeight: 1.7, color: T.textSecondary,
                          maxHeight: 200, overflowY: "auto",
                          whiteSpace: "pre-wrap", wordBreak: "break-word",
                          userSelect: "text", fontFamily: T.mono,
                        }}>
                          {previewText}
                        </div>
                      </>
                    )}
                  </div>
                )}

              </div>
            );
          })
        )}
      </div>

      {/* Zadaj pytanie AI */}
      <div style={{
        border: `1px solid ${T.border}`, borderRadius: 8, overflow: "hidden",
      }}>
        <div style={{
          padding: "10px 16px", background: T.surface,
          borderBottom: `1px solid ${T.border}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{
            fontSize: 11, color: T.blue,
            textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: T.mono,
          }}>
            Zadaj pytanie AI
          </span>
          <span style={{ fontSize: 12, color: T.textMuted }}>
            Kopiuje pytanie + dokument + PSE gotowe do wklejenia
          </span>
        </div>

        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}`, background: T.surface }}>
          <div style={{
            fontSize: 11, color: T.textMuted, textTransform: "uppercase",
            letterSpacing: "0.1em", marginBottom: 8,
          }}>
            Dokument
          </div>
          <select
            value={askDoc}
            onChange={e => handleAskDocSelect(e.target.value)}
            style={{
              width: "100%", padding: "8px 12px",
              background: T.bg, border: `1px solid ${askDoc ? T.blue : T.border}`,
              borderRadius: 6,
              color: askDoc ? T.textPrimary : T.textMuted,
              fontSize: 13, cursor: "pointer", outline: "none",
            }}
          >
            <option value="">Wybierz dokument...</option>
            {docs.map(d => (
              <option key={d.pse} value={d.pse}>
                {d.pse}{d.desc_plain ? " — " + d.desc_plain : ""}
              </option>
            ))}
          </select>
          {askLoading && (
            <div style={{ fontSize: 12, color: T.textMuted, marginTop: 6, fontFamily: T.mono }}>
              ▸ Pobieranie tekstu...
            </div>
          )}
        </div>

        <textarea
          value={askQuestion}
          onChange={e => { setAskQuestion(e.target.value); setAskCopied(false); }}
          placeholder="Wpisz pytanie do AI..."
          style={{
            width: "100%", minHeight: 80,
            border: "none", borderTop: `1px solid ${T.border}`,
            padding: "12px 16px", boxSizing: "border-box",
            fontSize: 14, resize: "vertical",
            background: T.bg, color: T.textPrimary, outline: "none",
          }}
        />

        <div style={{
          padding: "10px 16px", borderTop: `1px solid ${T.border}`,
          background: T.surface,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize: 12, color: T.textMuted }}>
            {askDoc && askQuestion.trim()
              ? `Skopiuje: [${askDoc}] + pytanie + treść dokumentu`
              : "Wybierz dokument i wpisz pytanie"}
          </span>
          <button
            onClick={handleAskCopy}
            disabled={!askDoc || !askQuestion.trim() || askLoading}
            style={{
              padding: "7px 18px", fontSize: 13, fontWeight: 500,
              background: askDoc && askQuestion.trim() ? T.blue : T.surface,
              border: `1px solid ${askDoc && askQuestion.trim() ? T.blue : T.border}`,
              borderRadius: 6,
              color: askCopied ? T.green : (askDoc && askQuestion.trim() ? "#fff" : T.textMuted),
              cursor: askDoc && askQuestion.trim() ? "pointer" : "not-allowed",
              whiteSpace: "nowrap", transition: "background 0.15s",
            }}
          >
            {askCopied ? "✓ Skopiowano do schowka" : "↗ Kopiuj pytanie do AI"}
          </button>
        </div>
      </div>

      {/* Błąd */}
      {error && (
        <div style={{
          background: T.redBg, border: `1px solid ${T.redBorder}`,
          borderRadius: 8, padding: "10px 16px", marginTop: 12,
          fontSize: 13, color: T.red,
        }}>
          ✕ {error}
        </div>
      )}

      {/* Modal potwierdzenia usunięcia */}
      {confirmPse && (
        <div style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.6)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 9999,
        }}>
          <div style={{
            background: T.surface, border: `1px solid ${T.redBorder}`,
            borderRadius: 12, padding: "24px 28px",
            minWidth: 320, maxWidth: 440,
          }}>
            <div style={{
              fontSize: 11, color: T.red, textTransform: "uppercase",
              letterSpacing: "0.1em", marginBottom: 12,
            }}>
              Usuń dokument
            </div>
            <div style={{ fontSize: 14, color: T.textPrimary, marginBottom: 8 }}>
              Czy na pewno usunąć{" "}
              <span style={{ fontFamily: T.mono, color: T.blueLight }}>{confirmPse}</span>?
            </div>
            <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 20, lineHeight: 1.5 }}>
              Operacja jest nieodwracalna. Zaszyfrowany blob i wpis w rejestrze zostaną trwale usunięte.
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setConfirmPse(null)}
                style={{
                  padding: "8px 18px", fontSize: 13,
                  background: "transparent", border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textMuted, cursor: "pointer",
                }}
              >
                Anuluj
              </button>
              <button
                onClick={handleDeleteConfirmed}
                style={{
                  padding: "8px 18px", fontSize: 13, fontWeight: 500,
                  background: T.redBg, border: `1px solid ${T.redBorder}`,
                  borderRadius: 6, color: T.red, cursor: "pointer",
                }}
              >
                ✕ Usuń
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
