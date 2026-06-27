// Pseudominizer — src/screens/ExpressModeScreen.tsx  v1.0
// Express Mode — bez logowania, bez biblioteki, bez depseudonimizacji.
// Dostępny z LockScreen. Używa /preview-express (pipeline bez SpaCy/NER).
// Ręczne maskowanie: zaznacz tekst w podglądzie → wpisz zastępnik → Zamaskuj.

import { useState, useRef, useEffect } from "react";
import { T } from "../theme";

const API = "http://127.0.0.1:8765";

interface Token {
  token:    string;
  original: string;
  type:     string;
  label:    string;
}

interface PreviewResult {
  pse_code:           string;
  anonymized_preview: string;
  tokens:             Token[];
  total:              number;
  blocked:            boolean;
  error:              string | null;
  ocr:                { quality: string; warning: string; confidence: number } | null;
  express_mode:       boolean;
}

const TOKEN_RE = /\b[A-Z][A-Z_]+_\d{3}\b/g;

function HighlightedText({ text }: { text: string }) {
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  TOKEN_RE.lastIndex = 0;
  while ((m = TOKEN_RE.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(
      <span key={m.index} style={{
        fontFamily: T.mono, fontSize: 14, letterSpacing: "0.06em",
        background: T.blueBg, color: T.blueLight,
        border: `1px solid ${T.borderActive}`,
        padding: "1px 6px", borderRadius: 4,
      }}>
        {m[0]}
      </span>
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

interface Props {
  onExit: () => void;
}

export default function ExpressModeScreen({ onExit }: Props) {
  const [uploading,   setUploading]   = useState(false);
  const [result,      setResult]      = useState<PreviewResult | null>(null);
  const [error,       setError]       = useState("");
  const [pasteText,   setPasteText]   = useState("");
  const [dragOver,    setDragOver]    = useState(false);
  const [copiedText,  setCopiedText]  = useState(false);

  // Ręczne maskowanie
  const [selectedText,  setSelectedText]  = useState("");
  const [maskLabel,     setMaskLabel]     = useState("");
  const [maskedPreview, setMaskedPreview] = useState<string | null>(null);

  const fileRef    = useRef<HTMLInputElement>(null);
  const imgRef     = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection();
      if (!sel || !previewRef.current || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      if (!previewRef.current.contains(range.commonAncestorContainer)) return;
      const text = sel.toString().trim();
      if (text && text.length > 0 && text.length < 300) {
        setSelectedText(text);
        setMaskLabel("");
      }
    };
    document.addEventListener("selectionchange", handler);
    return () => document.removeEventListener("selectionchange", handler);
  }, []);

  async function handleFile(file: File) {
    setUploading(true);
    setError("");
    setResult(null);
    setMaskedPreview(null);
    setSelectedText("");
    const form = new FormData();
    form.append("file", file);

    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res = await fetch(`${API}/preview-express`, { method: "POST", body: form, signal: ctrl.signal });
      clearTimeout(tid);

      if (!res.ok) {
        let errData: any = {};
        try { errData = await res.json(); } catch { /* brak JSON */ }
        setError(errData?.error ?? `Błąd serwera (${res.status})`);
        return;
      }

      const data: PreviewResult = await res.json();
      setResult(data);
      setMaskedPreview(data.anonymized_preview);
      if (data.error) setError(data.error);
    } catch {
      setError("Błąd połączenia. Czy backend :8765 jest uruchomiony?");
    } finally {
      setUploading(false);
    }
  }

  async function handlePasteSubmit() {
    if (!pasteText.trim() || uploading) return;
    const blob = new Blob([pasteText], { type: "text/plain" });
    await handleFile(new File([blob], "wklejony.txt", { type: "text/plain" }));
  }

  function handleManualMask() {
    if (!selectedText.trim() || !maskedPreview) return;
    const replacement = maskLabel.trim() || "█████";
    // Zamień wszystkie wystąpienia zaznaczonego tekstu w podglądzie
    const escaped = selectedText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const updated = maskedPreview.replace(new RegExp(escaped, "g"), replacement);
    setMaskedPreview(updated);
    setSelectedText("");
    setMaskLabel("");
  }

  const displayText = maskedPreview ?? result?.anonymized_preview ?? "";

  return (
    <div style={{
      width: "100vw", height: "100vh", background: T.bg,
      display: "flex", flexDirection: "column",
    }}>

      {/* Nagłówek */}
      <div style={{
        padding: "10px 20px",
        background: T.surface, borderBottom: `1px solid ${T.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{
            fontFamily: T.mono, fontSize: 11, letterSpacing: "0.18em",
            color: T.blue, border: `1px solid ${T.borderActive}`,
            padding: "2px 7px", borderRadius: 4, textTransform: "uppercase",
          }}>PSE</span>
          <span style={{ fontSize: 16, fontWeight: 300, color: T.textPrimary }}>
            LynxMask Express
          </span>
          <span style={{
            fontFamily: T.mono, fontSize: 11, color: T.amber,
            background: T.amberBg, border: `1px solid ${T.amberBorder}`,
            padding: "1px 8px", borderRadius: 4, letterSpacing: "0.1em",
          }}>
            BEZ NER · SZYBKI TRYB
          </span>
        </div>
        <button
          onClick={onExit}
          style={{
            fontSize: 13, padding: "5px 14px",
            background: "none", border: `1px solid ${T.border}`,
            borderRadius: 6, color: T.textMuted, cursor: "pointer",
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.blue; e.currentTarget.style.color = T.blueLight; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; }}
        >
          ← Wróć do logowania
        </button>
      </div>

      {/* Info o trybie */}
      <div style={{
        padding: "8px 20px", flexShrink: 0,
        background: T.amberBg, borderBottom: `1px solid ${T.amberBorder}`,
        fontSize: 13, color: T.amber, fontFamily: T.mono,
        letterSpacing: "0.04em",
      }}>
        ⚠ Express Mode nie rozpoznaje imion, nazwisk ani firm bez profilu biura. Użyj ręcznego maskowania poniżej.
      </div>

      {/* Treść */}
      <div style={{
        flex: 1, padding: 20, display: "flex", flexDirection: "column",
        minHeight: 0, overflowY: "auto",
      }}>

        {/* ── Wejście ── */}
        {!result && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <input
              ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md"
              style={{ display: "none" }}
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            />
            <input
              ref={imgRef} type="file" accept=".png,.jpg,.jpeg,.tiff,.bmp,.webp"
              style={{ display: "none" }}
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            />

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, flex: 1, minHeight: 0 }}>

              {/* Dropzone */}
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{
                  fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
                  letterSpacing: "0.1em", marginBottom: 8,
                }}>Wgraj plik</div>
                <div
                  onClick={() => !uploading && fileRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={e => {
                    e.preventDefault(); setDragOver(false);
                    const f = e.dataTransfer.files[0];
                    if (f && !uploading) handleFile(f);
                  }}
                  style={{
                    border: `2px dashed ${dragOver ? T.blue : (uploading ? T.borderActive : T.border)}`,
                    borderRadius: 8, padding: "28px 20px", textAlign: "center",
                    cursor: uploading ? "wait" : "pointer",
                    background: dragOver ? T.blueBg : T.surface,
                    transition: "border-color 0.15s, background 0.15s",
                    marginBottom: 8, flex: 1,
                  }}
                >
                  <div style={{ fontSize: 32, marginBottom: 10 }}>
                    {uploading ? "⏳" : "📂"}
                  </div>
                  <div style={{ fontSize: 15, color: uploading ? T.blueLight : T.textSecondary, marginBottom: 4 }}>
                    {uploading ? "Maskowanie..." : "Przeciągnij plik lub kliknij"}
                  </div>
                  <div style={{ fontSize: 13, color: T.textMuted, fontFamily: T.mono }}>
                    PDF · DOCX · TXT · MD
                  </div>
                </div>
                <button
                  onClick={() => !uploading && imgRef.current?.click()}
                  disabled={uploading}
                  style={{
                    width: "100%", padding: "9px 0",
                    background: T.surface, border: `1px solid ${T.border}`,
                    borderRadius: 6, cursor: uploading ? "not-allowed" : "pointer",
                    fontSize: 15, color: T.textMuted,
                    transition: "border-color 0.15s, color 0.15s",
                  }}
                  onMouseEnter={e => { if (!uploading) { e.currentTarget.style.borderColor = T.blue; e.currentTarget.style.color = T.blueLight; } }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; }}
                >
                  📷 OCR — Zdjęcie lub skan
                </button>
              </div>

              {/* Paste */}
              <div style={{ display: "flex", flexDirection: "column" }}>
                <div style={{
                  fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
                  letterSpacing: "0.1em", marginBottom: 8,
                  display: "flex", justifyContent: "space-between",
                }}>
                  <span>Lub wklej tekst</span>
                  {pasteText && <span style={{ fontSize: 12, textTransform: "none", letterSpacing: 0 }}>{pasteText.length} znaków</span>}
                </div>
                <textarea
                  value={pasteText}
                  onChange={e => setPasteText(e.target.value)}
                  placeholder={"Ctrl+V — wklej treść dokumentu..."}
                  disabled={uploading}
                  style={{
                    flex: 1, boxSizing: "border-box", padding: "12px 14px",
                    background: T.surface,
                    border: `1px solid ${pasteText ? T.borderActive : T.border}`,
                    borderRadius: 8, color: T.textSecondary,
                    fontSize: 15, lineHeight: 1.6, fontFamily: T.sans,
                    resize: "none", outline: "none", minHeight: 160,
                    transition: "border-color 0.15s",
                  }}
                />
                {pasteText.trim() && !uploading && (
                  <button
                    onClick={handlePasteSubmit}
                    style={{
                      width: "100%", marginTop: 8, padding: "9px",
                      background: T.blue, border: "none", borderRadius: 6,
                      color: "#fff", fontSize: 15, fontWeight: 500, cursor: "pointer",
                    }}
                  >
                    → Zamaskuj tekst (Express)
                  </button>
                )}
              </div>
            </div>

            {error && (
              <div style={{
                background: T.redBg, border: `1px solid ${T.redBorder}`,
                borderRadius: 8, padding: "10px 16px", marginTop: 16,
                fontSize: 15, color: T.red,
              }}>
                ✕ {error}
              </div>
            )}
          </div>
        )}

        {/* ── Wynik ── */}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Pasek wynikowy */}
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "center", flexShrink: 0,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{
                  fontFamily: T.mono, fontSize: 14, color: T.blueLight,
                  background: T.blueBg, border: `1px solid ${T.borderActive}`,
                  padding: "3px 10px", borderRadius: 4, letterSpacing: "0.08em",
                }}>
                  {result.pse_code}
                </span>
                <span style={{ fontSize: 14, color: T.textMuted }}>
                  {result.total} encji (regex)
                </span>
                <button
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(displayText);
                      setCopiedText(true);
                      setTimeout(() => setCopiedText(false), 2000);
                    } catch { /* brak clipboard */ }
                  }}
                  style={{
                    fontSize: 13, padding: "3px 10px",
                    background: copiedText ? T.blueBg : T.surface,
                    border: `1px solid ${copiedText ? T.borderActive : T.border}`,
                    borderRadius: 4,
                    color: copiedText ? T.blueLight : T.textMuted,
                    cursor: "pointer", fontFamily: T.mono, transition: "all 0.15s",
                  }}
                >
                  {copiedText ? "✓ Skopiowany" : "↗ Kopiuj tekst"}
                </button>
              </div>
              <button
                onClick={() => {
                  setResult(null); setError(""); setPasteText("");
                  setMaskedPreview(null); setSelectedText(""); setMaskLabel("");
                  setCopiedText(false);
                }}
                style={{
                  fontSize: 14, background: "none",
                  border: `1px solid ${T.border}`, borderRadius: 6,
                  color: T.textSecondary, cursor: "pointer", padding: "5px 14px",
                  transition: "border-color 0.15s, color 0.15s",
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.blue; e.currentTarget.style.color = T.blueLight; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textSecondary; }}
              >
                ✕ Nowy dokument
              </button>
            </div>

            {/* Podgląd tekstu */}
            <div
              ref={previewRef}
              style={{
                background: T.surface, border: `1px solid ${T.border}`,
                borderLeft: `3px solid ${T.borderActive}`,
                borderRadius: 8, padding: "14px 16px",
                fontSize: 15, lineHeight: 1.8,
                color: T.textSecondary,
                maxHeight: 260, overflowY: "auto",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
                userSelect: "text", cursor: "text",
              }}
            >
              <HighlightedText text={displayText} />
            </div>

            {/* Ręczne maskowanie */}
            <div style={{
              background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: 8, padding: "12px 16px",
            }}>
              <div style={{
                fontSize: 13, color: T.textSecondary,
                textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10,
              }}>
                Ręczne maskowanie — zaznacz tekst powyżej lub wpisz fragment
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  value={selectedText}
                  onChange={e => setSelectedText(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleManualMask()}
                  placeholder="Zaznaczony fragment lub wpisz ręcznie..."
                  style={{
                    flex: 1, padding: "8px 12px",
                    background: T.bg, border: `1px solid ${T.border}`,
                    borderRadius: 6, color: T.textPrimary, fontSize: 15,
                    fontFamily: T.sans, outline: "none", minWidth: 0,
                  }}
                />
                <input
                  value={maskLabel}
                  onChange={e => setMaskLabel(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleManualMask()}
                  placeholder="Zastępnik (opcjonalnie)"
                  style={{
                    width: 180, padding: "8px 12px",
                    background: T.bg, border: `1px solid ${T.border}`,
                    borderRadius: 6, color: T.textPrimary, fontSize: 15,
                    fontFamily: T.sans, outline: "none",
                  }}
                />
                <button
                  onClick={handleManualMask}
                  disabled={!selectedText.trim()}
                  style={{
                    padding: "8px 16px",
                    background: selectedText.trim() ? T.blue : T.surface,
                    border: `1px solid ${selectedText.trim() ? T.blue : T.border}`,
                    borderRadius: 6,
                    color: selectedText.trim() ? "#fff" : T.textMuted,
                    fontSize: 15, cursor: selectedText.trim() ? "pointer" : "not-allowed",
                    fontWeight: 500, whiteSpace: "nowrap",
                    transition: "background 0.15s",
                  }}
                >
                  → Zamaskuj
                </button>
              </div>
              <div style={{ fontSize: 12, color: T.textMuted, marginTop: 6 }}>
                Jeśli pole zastępnika jest puste — fragment zostanie zastąpiony znakami █████
              </div>
            </div>

            {/* Tabela tokenów */}
            {result.tokens.length > 0 && (
              <div style={{
                border: `1px solid ${T.border}`, borderRadius: 8, overflow: "hidden",
              }}>
                <div style={{
                  padding: "8px 16px", background: T.surface,
                  borderBottom: `1px solid ${T.border}`,
                  fontSize: 13, color: T.textSecondary,
                  textTransform: "uppercase", letterSpacing: "0.1em",
                }}>
                  Automatycznie wykryte encje ({result.total})
                </div>
                <div style={{ maxHeight: 180, overflowY: "auto" }}>
                  <table style={{ width: "100%", fontSize: 14, borderCollapse: "collapse", tableLayout: "fixed" }}>
                    <colgroup>
                      <col style={{ width: "30%" }} />
                      <col style={{ width: "42%" }} />
                      <col style={{ width: "28%" }} />
                    </colgroup>
                    <tbody>
                      {result.tokens.map((tok, i) => (
                        <tr key={tok.token} style={{
                          borderTop: `1px solid ${T.border}`,
                          background: i % 2 === 0 ? "transparent" : T.surface,
                        }}>
                          <td style={{ padding: "6px 16px" }}>
                            <span style={{
                              fontFamily: T.mono, fontSize: 12, letterSpacing: "0.06em",
                              background: T.blueBg, color: T.blueLight,
                              border: `1px solid ${T.borderActive}`,
                              padding: "2px 8px", borderRadius: 4,
                            }}>{tok.token}</span>
                          </td>
                          <td style={{
                            padding: "6px 16px", color: T.textSecondary,
                            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                          }}>{tok.original}</td>
                          <td style={{
                            padding: "6px 16px", fontFamily: T.mono,
                            fontSize: 12, color: T.textMuted,
                          }}>{tok.label}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {error && (
              <div style={{
                background: T.redBg, border: `1px solid ${T.redBorder}`,
                borderRadius: 8, padding: "10px 16px",
                fontSize: 15, color: T.red,
              }}>
                ✕ {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
