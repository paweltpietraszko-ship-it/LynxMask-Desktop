// Pseudominizer — src/screens/ExpressModeScreen.tsx  v1.1
// Express Mode — dostępny z LockScreen bez logowania.
// Identyczna użyteczność jak Pseudonimizuj.tsx, z wyjątkiem:
//   - brak zapisu do biblioteki
//   - brak depseudonimizacji
//   - brak profilu biura (add-entity) — zastąpione ręcznym maskowaniem
//   - używa /preview-express (pipeline bez SpaCy/NER)
//   - nie wysyła X-Api-Token (endpoint zwolniony z auth)

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
  original_text:      string;
  tokens:             Token[];
  total:              number;
  blocked:            boolean;
  error:              string | null;
  ocr:                { quality: string; warning: string; confidence: number } | null;
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
  const [ocrWarning,  setOcrWarning]  = useState(false);
  const [copiedPse,   setCopiedPse]   = useState(false);
  const [copiedText,  setCopiedText]  = useState(false);

  // Ręczne maskowanie (zastępuje "dodaj do profilu biura")
  const [maskInput,   setMaskInput]   = useState("");
  const [maskLabel,   setMaskLabel]   = useState("");
  const [maskedText,  setMaskedText]  = useState<string | null>(null);
  const [maskApplied, setMaskApplied] = useState("");

  const [, setPendingFile] = useState<File | null>(null);
  const fileRef    = useRef<HTMLInputElement>(null);
  const imgRef     = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  // Śledź zaznaczenie w oknie podglądu
  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection();
      if (!sel || !previewRef.current || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      if (!previewRef.current.contains(range.commonAncestorContainer)) return;
      const text = sel.toString().trim();
      if (text && text.length > 0 && text.length < 300) {
        setMaskInput(text);
        setMaskLabel("");
        setMaskApplied("");
      }
    };
    document.addEventListener("selectionchange", handler);
    return () => document.removeEventListener("selectionchange", handler);
  }, []);

  async function handleFile(file: File) {
    setUploading(true);
    setError("");
    setResult(null);
    setMaskedText(null);
    setMaskInput("");
    setMaskLabel("");
    setMaskApplied("");
    setOcrWarning(false);
    setPendingFile(null);
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
        if (res.status === 422 && errData?.ocr_rejected) {
          setError(errData.error ?? "Jakość OCR zbyt niska do bezpiecznego maskowania.");
        } else {
          setError(errData?.error ?? `Błąd serwera (${res.status})`);
        }
        return;
      }

      const data: PreviewResult = await res.json();

      if (data.ocr?.quality === "warn") {
        setPendingFile(null);
        setOcrWarning(true);
        setResult(data);
        setMaskedText(data.anonymized_preview);
        if (data.error) setError(data.error);
      } else {
        setResult(data);
        setMaskedText(data.anonymized_preview);
        if (data.error) setError(data.error);
      }
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
    if (!maskInput.trim() || !maskedText) return;
    const replacement = maskLabel.trim() || "█████";
    const escaped = maskInput.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const updated = maskedText.replace(new RegExp(escaped, "g"), replacement);
    setMaskedText(updated);
    setMaskApplied(`"${maskInput}" → ${replacement}`);
    setMaskInput("");
    setMaskLabel("");
  }

  const displayText = maskedText ?? "";

  return (
    <div style={{
      padding: 24,
      height: "100vh",
      boxSizing: "border-box",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
    }}>

      {/* Nagłówek */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 20, flexShrink: 0,
      }}>
        <div style={{
          fontSize: 13, letterSpacing: "0.12em", fontFamily: T.mono,
          color: T.blue, textTransform: "uppercase",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          Pseudonimizuj dokument
          <span style={{
            fontFamily: T.mono, fontSize: 11, color: T.amber,
            background: T.amberBg, border: `1px solid ${T.amberBorder}`,
            padding: "1px 8px", borderRadius: 4, letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}>
            ⚡ Express · bez NER
          </span>
        </div>
        <button
          onClick={onExit}
          style={{
            fontSize: 13, padding: "4px 12px",
            background: "none", border: `1px solid ${T.border}`,
            borderRadius: 6, color: T.textMuted, cursor: "pointer",
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.blue; e.currentTarget.style.color = T.blueLight; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; }}
        >
          ← Zaloguj się
        </button>
      </div>

      {/* ── Strefa wejścia ── */}
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

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16, flex: 1, minHeight: 0 }}>

            {/* Dropzone */}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{
                fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
                letterSpacing: "0.1em", marginBottom: 8, flexShrink: 0,
              }}>
                Wgraj plik
              </div>
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
                  {uploading ? "Pseudonimizuję..." : "Przeciągnij plik lub kliknij"}
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
                  flexShrink: 0,
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
                letterSpacing: "0.1em", marginBottom: 8, flexShrink: 0,
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span>Lub wklej tekst</span>
                {pasteText && (
                  <span style={{ fontSize: 12, color: T.textSecondary, textTransform: "none", letterSpacing: 0 }}>
                    {pasteText.length} znaków
                  </span>
                )}
              </div>
              <textarea
                value={pasteText}
                onChange={e => setPasteText(e.target.value)}
                onDrop={e => { e.preventDefault(); const d = e.dataTransfer.getData("text"); if (d) setPasteText(d); }}
                placeholder={"Ctrl+V — wklej treść dokumentu...\n\nLub przeciągnij tekst tutaj."}
                disabled={uploading}
                style={{
                  flex: 1, boxSizing: "border-box", padding: "12px 14px",
                  background: T.surface,
                  border: `1px solid ${pasteText ? T.borderActive : T.border}`,
                  borderRadius: 8, color: T.textSecondary,
                  fontSize: 15, lineHeight: 1.6, fontFamily: T.sans,
                  resize: "none", outline: "none",
                  transition: "border-color 0.15s", minHeight: 160,
                }}
              />
              {pasteText.trim() && !uploading && (
                <button
                  onClick={handlePasteSubmit}
                  style={{
                    width: "100%", marginTop: 8, padding: "9px",
                    background: T.blue, border: "none", borderRadius: 6,
                    color: "#fff", fontSize: 15, fontWeight: 500,
                    cursor: "pointer", flexShrink: 0,
                  }}
                >
                  → Pseudonimizuj tekst
                </button>
              )}
            </div>
          </div>

          {pasteText.trim() && (
            <div style={{
              fontSize: 14, color: T.textSecondary, marginBottom: 12, flexShrink: 0,
              padding: "6px 12px", background: T.surface,
              border: `1px solid ${T.border}`, borderRadius: 6,
            }}>
              ℹ Jeśli wgrasz plik — zastąpi wklejony tekst.
            </div>
          )}

          {error && (
            <div style={{
              background: T.redBg, border: `1px solid ${T.redBorder}`,
              borderRadius: 8, padding: "10px 16px", flexShrink: 0,
              fontSize: 15, color: T.red, lineHeight: 1.5,
            }}>
              ✕ {error}
            </div>
          )}
        </div>
      )}

      {/* ── Wynik pseudonimizacji ── */}
      {result && !ocrWarning && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflowY: "auto" }}>

          {/* Pasek tytułowy */}
          <div style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", marginBottom: 16, flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{
                fontFamily: T.mono, fontSize: 14, color: T.blueLight,
                background: T.blueBg, border: `1px solid ${T.borderActive}`,
                padding: "3px 10px", borderRadius: 4, letterSpacing: "0.08em",
              }}>
                {result.pse_code}
              </span>
              <button
                onClick={async () => {
                  try { await navigator.clipboard.writeText(result.pse_code); setCopiedPse(true); setTimeout(() => setCopiedPse(false), 2000); } catch { /* */ }
                }}
                style={{
                  fontSize: 13, padding: "3px 10px",
                  background: copiedPse ? T.greenBg : T.surface,
                  border: `1px solid ${copiedPse ? T.greenBorder : T.border}`,
                  borderRadius: 4, color: copiedPse ? T.green : T.textMuted,
                  cursor: "pointer", fontFamily: T.mono, transition: "all 0.15s",
                }}
              >
                {copiedPse ? "✓ PSE skopiowane" : "↗ Kopiuj PSE"}
              </button>
              <button
                onClick={async () => {
                  try { await navigator.clipboard.writeText(displayText); setCopiedText(true); setTimeout(() => setCopiedText(false), 2000); } catch { /* */ }
                }}
                style={{
                  fontSize: 13, padding: "3px 10px",
                  background: copiedText ? T.blueBg : T.surface,
                  border: `1px solid ${copiedText ? T.borderActive : T.border}`,
                  borderRadius: 4, color: copiedText ? T.blueLight : T.textMuted,
                  cursor: "pointer", fontFamily: T.mono, transition: "all 0.15s",
                }}
              >
                {copiedText ? "✓ Tekst skopiowany" : "↗ Kopiuj tekst"}
              </button>
            </div>
            <button
              onClick={() => {
                setResult(null); setError(""); setPasteText("");
                setMaskedText(null); setMaskInput(""); setMaskLabel("");
                setMaskApplied(""); setCopiedPse(false); setCopiedText(false);
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

          {/* Pseudonimizowany tekst */}
          <div
            ref={previewRef}
            style={{
              background: T.surface, border: `1px solid ${T.border}`,
              borderLeft: `3px solid ${T.borderActive}`,
              borderRadius: 8, padding: "14px 16px",
              fontSize: 16, lineHeight: 1.8,
              color: T.textSecondary, marginBottom: 16,
              maxHeight: 220, overflowY: "auto",
              whiteSpace: "pre-wrap", wordBreak: "break-word",
              userSelect: "text", cursor: "text",
              flexShrink: 0,
            }}
          >
            <HighlightedText text={displayText} />
          </div>

          {/* Tabela tokenów */}
          <div style={{
            border: `1px solid ${T.border}`, borderRadius: 8,
            overflow: "hidden", marginBottom: 16, flexShrink: 0,
          }}>
            <div style={{
              padding: "8px 16px", background: T.surface,
              borderBottom: `1px solid ${T.border}`,
              fontSize: 13, color: T.textSecondary,
              textTransform: "uppercase", letterSpacing: "0.1em",
            }}>
              Wykryte encje ({result.total})
            </div>
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              <table style={{ width: "100%", fontSize: 15, borderCollapse: "collapse", tableLayout: "fixed" }}>
                <colgroup>
                  <col style={{ width: "30%" }} />
                  <col style={{ width: "42%" }} />
                  <col style={{ width: "28%" }} />
                </colgroup>
                <thead>
                  <tr style={{ background: T.surface }}>
                    {["Token", "Wartość oryginalna", "Typ"].map(h => (
                      <th key={h} style={{
                        padding: "7px 16px", textAlign: "left",
                        fontSize: 13, color: T.textSecondary,
                        textTransform: "uppercase", letterSpacing: "0.08em",
                        fontWeight: 500, position: "sticky", top: 0,
                        background: T.surface, fontFamily: T.mono,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.tokens.map((tok, i) => (
                    <tr key={tok.token} style={{
                      borderTop: `1px solid ${T.border}`,
                      background: i % 2 === 0 ? "transparent" : T.surface,
                    }}>
                      <td style={{ padding: "7px 16px" }}>
                        <span style={{
                          fontFamily: T.mono, fontSize: 13, letterSpacing: "0.06em",
                          background: T.blueBg, color: T.blueLight,
                          border: `1px solid ${T.borderActive}`,
                          padding: "2px 8px", borderRadius: 4,
                        }}>{tok.token}</span>
                      </td>
                      <td style={{
                        padding: "7px 16px", color: T.textSecondary,
                        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                      }}>{tok.original}</td>
                      <td style={{
                        padding: "7px 16px", fontFamily: T.mono,
                        fontSize: 13, color: T.textMuted,
                      }}>{tok.label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Ręczne maskowanie — zaznacz tekst powyżej lub wpisz ręcznie */}
          <div style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: 8, padding: "12px 16px", marginBottom: 16,
            flexShrink: 0,
          }}>
            <div style={{
              fontSize: 13, color: T.textSecondary,
              textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10,
            }}>
              Zaznacz tekst powyżej lub wpisz ręcznie → zamaskuj
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={maskInput}
                onChange={e => { setMaskInput(e.target.value); setMaskApplied(""); }}
                onKeyDown={e => e.key === "Enter" && handleManualMask()}
                placeholder="np. Jan Kowalski"
                style={{
                  flex: 1, padding: "8px 12px",
                  background: T.bg, border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textPrimary, fontSize: 16,
                  fontFamily: T.sans, outline: "none", minWidth: 0,
                }}
              />
              <input
                value={maskLabel}
                onChange={e => setMaskLabel(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleManualMask()}
                placeholder="Zastępnik (opcja)"
                style={{
                  width: 160, padding: "8px 12px",
                  background: T.bg, border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textPrimary, fontSize: 15,
                  fontFamily: T.sans, outline: "none",
                }}
              />
              <button
                onClick={handleManualMask}
                disabled={!maskInput.trim()}
                style={{
                  padding: "8px 16px",
                  background: maskInput.trim() ? T.blue : T.surface,
                  border: `1px solid ${maskInput.trim() ? T.blue : T.border}`,
                  borderRadius: 6,
                  color: maskInput.trim() ? "#fff" : T.textMuted,
                  fontSize: 15, cursor: maskInput.trim() ? "pointer" : "not-allowed",
                  fontWeight: 500, whiteSpace: "nowrap",
                  transition: "background 0.15s",
                }}
              >
                → Zamaskuj
              </button>
            </div>
            {maskApplied && (
              <div style={{ fontSize: 14, color: T.green, marginTop: 8 }}>
                ✓ Zamaskowano: {maskApplied}
              </div>
            )}
            <div style={{ fontSize: 12, color: T.textMuted, marginTop: 6 }}>
              Brak zastępnika → fragment zostanie zastąpiony znakami █████. Zamaskowanie dotyczy wszystkich wystąpień.
            </div>
          </div>

          {error && (
            <div style={{
              background: T.redBg, border: `1px solid ${T.redBorder}`,
              borderRadius: 8, padding: "10px 16px",
              fontSize: 15, color: T.red, lineHeight: 1.5, flexShrink: 0,
            }}>
              ✕ {error}
            </div>
          )}

        </div>
      )}

      {/* OCR warning — dialog niskiej jakości */}
      {ocrWarning && result && result.ocr && (
        <div style={{
          flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-start",
        }}>
          <div style={{
            background: T.surface, border: `1px solid ${T.borderActive}`,
            borderRadius: 8, padding: "16px 20px",
          }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: T.text, marginBottom: 8 }}>
              ⚠️ Dokument słabej jakości OCR
            </div>
            <div style={{ fontSize: 15, color: T.textMuted, marginBottom: 4, lineHeight: 1.6 }}>
              {result.ocr?.warning || "Jakość odczytu jest niska. Maskowanie może zawierać błędy."}
            </div>
            <div style={{ fontSize: 14, color: T.textMuted, marginBottom: 14 }}>
              Pewność odczytu: {result.ocr?.confidence?.toFixed(0)}%
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => setOcrWarning(false)}
                style={{
                  padding: "7px 18px", borderRadius: 6, fontSize: 15,
                  background: T.blue, color: "#fff",
                  border: `1px solid ${T.blue}`, cursor: "pointer",
                }}
              >
                Tak, zamaskuj
              </button>
              <button
                onClick={() => { setOcrWarning(false); setResult(null); setMaskedText(null); setPendingFile(null); }}
                style={{
                  padding: "7px 18px", borderRadius: 6, fontSize: 15,
                  background: T.surface, color: T.textMuted,
                  border: `1px solid ${T.border}`, cursor: "pointer",
                }}
              >
                Anuluj
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
