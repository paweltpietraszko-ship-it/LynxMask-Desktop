// Pseudominizer — Pseudonimizuj.tsx  v1.8
// ============================================================
// ZMIANY W TEJ WERSJI (v1.7):
//   [UI-FONT-01] Czcionki podniesione globalnie we wszystkich elementach
// ============================================================
// ZMIANY W v1.6:
//   [UI-PSE-05] Kopiuj PSE — przycisk przy kodzie PSE w pasku wynikowym — linia ~380
//     Kopiuje pse_code do schowka. Stan copiedPse: boolean z timeoutem 2s.
//   [UI-PSE-06] Kopiuj tekst — przycisk w pasku wynikowym — linia ~395
//     Kopiuje anonymized_preview do schowka. Stan copiedText: boolean z timeoutem 2s.
//     Oba przyciski spójne wizualnie z resztą interfejsu.
// ============================================================
// ZMIANY W v1.5:
//   [UI-PSE-01] Powiększone czcionki bazowe (15px)
//   [UI-PSE-02] Eliminacja czarnej pustki — flex column
//   [UI-PSE-03] Przyciski akcji wyraźne
//   [UI-PSE-04] Textarea minHeight 160px
// ============================================================
// Zachowane bez zmian:
//   - [OCR-WARN-NULL] Zabezpieczenie dialogu OCR przed null result.ocr
//   - [OCR-REJECT] Obsługa HTTP 422 z ocr_rejected=true
//   - [FIX-HTTP-ERROR] Sprawdzenie res.ok przed res.json()
//   - [OCR-WARN] quality: "low"→"warn"
//   - [FIX-TOKEN-API] nagłówek X-Api-Token
//   - [FIX-BUG-1] guardBlocked blokuje przycisk Zapisz
//   - Cała logika: handleFile, handlePasteSubmit, handleSave, handleAddEntity
//   - HighlightedText (odkrywanie wystąpień: revealText.ts), guessEntityType
//   - selectionchange handler na previewRef
//   - Drag & drop pliku na dropzone + drag & drop tekstu na textarea
//   - Plik ma pierwszeństwo nad wklejonym tekstem
// ============================================================

import { useState, useRef, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { T } from "../theme";
import { segments, finalText, toggleReveal } from "./revealText";  // [LYNX-MANUAL-REVEAL]
import GuardPanel from "./GuardPanel";  // [LYNX-GUARD-B]
import { GuardWarning, Cover, applyCovers, coverWarning, coverTypeFor, pendingWarnings, rememberable, toUtf16, warningKey }
  from "./guardDecisions";

const API = "http://127.0.0.1:8765";

// ── Typy ─────────────────────────────────────────────────────────────────────

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
  guard_reasons:      string[];
  guard_values?:      string[];   // [LYNX-FAILCLOSED-S3] wartości naruszeń (powody są bez wartości)
  guard_warnings?:    GuardWarning[];  // [LYNX-GUARD-A] pozycje względem anonymized_preview
  error:              string | null;
  anonymizer_active:  boolean;
  original_text:      string;
  ocr:                { quality: string; warning: string; confidence: number; engine?: string } | null;
}

// ── Krypto helper ─────────────────────────────────────────────────────────────

async function encryptToBase64(text: string): Promise<string> {
  const plaintext = Array.from(new TextEncoder().encode(text));
  const encrypted: number[] = await invoke("encrypt_data", { plaintext });
  const bytes = new Uint8Array(encrypted);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

// ── Heurystyczne wykrywanie typu encji ───────────────────────────────────────

function guessEntityType(text: string): string {
  const t = text.trim();
  if (/\b(ul\.|al\.|os\.|pl\.|sk\.|dr\.|rondo|aleja|ulica)/i.test(t)) return "ADRES";
  if (/^\d{11}$/.test(t)) return "NUMER";
  if (/^\d{3}[- ]?\d{3}[- ]?\d{2}[- ]?\d{2}$/.test(t)) return "NUMER";
  if (/@/.test(t)) return "NUMER";
  if (/^[+]?[\d \-]{9,15}$/.test(t)) return "NUMER";
  if (/(sp\. ?z|s\.a\.|ltd|s\.c\.|krs|spółk)/i.test(t)) return "FIRMA";
  if (/(zł|pln|eur|usd|\d+[,.]\d{2})/i.test(t)) return "KWOTA";
  if (/^[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ [A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+$/.test(t)) return "OSOBA";
  return "OSOBA";
}

// ── Token highlight ───────────────────────────────────────────────────────────

// [LYNX-MANUAL-REVEAL] klik w wystąpienie tokenu = odkryj/cofnij tylko to miejsce (onToggle brak → tokeny nieklikalne)
function HighlightedText({ text, map = {}, revealed = new Set<number>(), onToggle }: { text: string;
    map?: Record<string, string>; revealed?: ReadonlySet<number>; onToggle?: (at: number, token: string) => void }) {
  return <>{segments(text, map, revealed).map((s, i) => s.token === undefined ? s.text : (
    <span key={i} role={onToggle ? "button" : undefined} tabIndex={onToggle ? 0 : undefined}
      title={!onToggle ? undefined : s.revealed ? "Cofnij odkrycie" : map[s.token] === undefined
        ? "Brak wartości w mapie — tego miejsca nie można odkryć" : `Odkryj tutaj (całą wartość: ${map[s.token]})`}
      onClick={() => onToggle?.(s.at!, s.token!)} onKeyDown={e => e.key === "Enter" && onToggle?.(s.at!, s.token!)}
      style={{
        fontFamily: s.revealed ? undefined : T.mono, fontSize: s.revealed ? undefined : 14, letterSpacing: "0.06em",
        background: s.revealed ? "transparent" : T.blueBg, color: s.revealed ? T.red : T.blueLight,
        border: `1px solid ${s.revealed ? T.red : T.borderActive}`, textDecoration: s.revealed ? "underline" : undefined,
        padding: "1px 6px", borderRadius: 4, cursor: onToggle ? "pointer" : undefined,
      }}>
      {s.text}
    </span>))}</>;
}

// ── Komponent główny ──────────────────────────────────────────────────────────

interface Props {
  apiToken?: string;
  expressMode?: boolean;  // [LYNX-EXPRESS-ONE-ENGINE] ten sam silnik; bez akcji wymagających logowania (profil, biblioteka)
}

export default function Pseudonimizuj({ apiToken = "", expressMode = false }: Props) {
  const [uploading,    setUploading]    = useState(false);
  const [result,       setResult]       = useState<PreviewResult | null>(null);
  const [error,        setError]        = useState("");
  const [description,  setDescription]  = useState("");
  const [saving,       setSaving]       = useState(false);
  const [saved,        setSaved]        = useState(false);
  const [missedText,   setMissedText]   = useState("");
  const [missedType,   setMissedType]   = useState("OSOBA");
  const [addingEntity, setAddingEntity] = useState(false);
  const [addedToken,   setAddedToken]   = useState("");
  const [guardBlocked,   setGuardBlocked]   = useState(false);  // twarda blokada z silnika (nie ostrzeżenia)
  const [kept,         setKept]         = useState<Set<string>>(new Set());  // [LYNX-GUARD-B] Zostaw (tylko pamięć)
  const [covered,      setCovered]      = useState<Set<string>>(new Set());  // [LYNX-GUARD-B] Zakryj (klucze, tylko pamięć)
  const [remember,     setRemember]     = useState(true);  // [LYNX-GUARD-B] Zakryj → słownik biura (Paweł 22.10)
  const [pasteText,    setPasteText]    = useState("");
  const [dragOver,     setDragOver]     = useState(false);
  const [ocrWarning,   setOcrWarning]   = useState(false);
  const [revealed,     setRevealed]     = useState<Set<number>>(new Set());  // [LYNX-MANUAL-REVEAL] tylko UI
  const [ocrRejected,  setOcrRejected]  = useState(false);  // [LYNX-PHOTO-CHAIN] odmowa zdjęcia → „Wklej tekst”
  const [copiedPse,    setCopiedPse]    = useState(false);  // [UI-PSE-05]
  const [copiedText,   setCopiedText]   = useState(false);  // [UI-PSE-06]
  const [, setPendingFile]  = useState<File | null>(null);
  const fileRef    = useRef<HTMLInputElement>(null);
  const imgRef     = useRef<HTMLInputElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const pasteRef   = useRef<HTMLTextAreaElement>(null);

  // [LYNX-MANUAL-REVEAL] nowy wynik (nowy dokument, „Dodaj i zakryj”) czyści odkrycia; jeden tekst dla ekranu/kopii/zapisu
  useEffect(() => setRevealed(new Set()), [result, covered]);
  const resultMap: Record<string, string> = Object.fromEntries((result?.tokens ?? []).map(t => [t.token, t.original]));
  const warnings = result ? toUtf16(result.anonymized_preview, result.guard_warnings ?? []) : [];  // Codex F1: UTF-16
  const covers = result ? warnings.filter(w => covered.has(warningKey(result.anonymized_preview, w)))
    .reduce<Cover[]>((cs, w) => coverWarning(result.anonymized_preview, w, resultMap, cs), []) : [];
  const coverTokens = covers.filter((c, i) => !(c.token in resultMap) && covers.findIndex(d => d.token === c.token) === i);
  const tokenMap: Record<string, string> = { ...resultMap, ...Object.fromEntries(coverTokens.map(c => [c.token, c.original])) };
  // [LYNX-GUARD-B] ostrzeżenia na niezmiennym anonymized_preview; ekran/kopia/zapis z zakryciami i odkryciami
  const pending = result ? pendingWarnings(result.anonymized_preview, warnings, kept, covers) : [];
  const locked = guardBlocked || pending.length > 0;  // S4: zapis/kopia/eksport dopiero po decyzji przy każdym ostrzeżeniu
  const base = result ? applyCovers(result.anonymized_preview, covers) : "";
  const shownText = result ? finalText(base, tokenMap, guardBlocked ? new Set() : revealed) : "";

  // Śledź zaznaczenie w oknie podglądu przez selectionchange
  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection();
      if (!sel || !previewRef.current || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      if (!previewRef.current.contains(range.commonAncestorContainer)) return;
      const text = sel.toString().trim();
      if (text && text.length > 1 && text.length < 200) {
        setMissedText(text);
        setMissedType(guessEntityType(text));
      }
    };
    document.addEventListener("selectionchange", handler);
    return () => document.removeEventListener("selectionchange", handler);
  }, []);

  // ── Upload pliku ────────────────────────────────────────────

  async function handleFile(file: File) {
    setUploading(true);
    setError("");
    setResult(null);
    setSaved(false);
    setDescription("");
    setAddedToken("");
    setGuardBlocked(false); setKept(new Set()); setCovered(new Set());
    setOcrWarning(false);
    setOcrRejected(false);
    setPendingFile(null);
    const form = new FormData();
    form.append("file", file);

    const headers: Record<string, string> = {};
    if (apiToken) headers["X-Api-Token"] = apiToken;

    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res = await fetch(`${API}/preview`, { method: "POST", body: form, headers, signal: ctrl.signal });
      clearTimeout(tid);

      // [FIX-HTTP-ERROR]
      if (!res.ok) {
        let errData: any = {};
        try { errData = await res.json(); } catch { /* brak JSON */ }

        // [OCR-REJECT] [LYNX-PHOTO-CHAIN] odmowa zdjęcia przychodzi też jako 400 z ocr.quality="reject" (bez tekstu)
        if ((res.status === 422 && errData?.ocr_rejected) || errData?.ocr?.quality === "reject") {
          setOcrRejected(true);
          setError(errData.error ?? "Jakość OCR zbyt niska do bezpiecznego maskowania.");
        } else {
          setError(errData?.error ?? `Błąd serwera (${res.status})`);
        }
        return;
      }

      const data: PreviewResult = await res.json();

      setGuardBlocked(data.blocked);  // [LYNX-GUARD-B] ostrzeżenia blokują przez `locked`, nie tutaj

      // [OCR-WARN]
      if (data.ocr?.quality === "warn") {
        setPendingFile(null);
        setOcrWarning(true);
        setResult(data);
        if (data.error) setError(data.error);
      } else {
        setResult(data);
        if (data.error) setError(data.error);
      }
    } catch {
      setError("Błąd połączenia. Czy backend :8765 jest uruchomiony?");
    } finally {
      setUploading(false);
    }
  }

  // ── Przetworzenie wklejonego tekstu ────────────────────────

  async function handlePasteSubmit() {
    if (!pasteText.trim() || uploading) return;
    const blob = new Blob([pasteText], { type: "text/plain" });
    const file = new File([blob], "wklejony.txt", { type: "text/plain" });
    await handleFile(file);
  }

  // ── Zapis do biblioteki ─────────────────────────────────────

  async function handleSave() {
    if (!result || !description.trim() || saving || locked) return;  // [LYNX-GUARD-B] bez zbiorczego obejścia
    setSaving(true);
    setError("");
    try {
      const encBlob = await encryptToBase64(JSON.stringify({
        tokens: [...result.tokens, ...coverTokens.map(c => ({ token: c.token, original: c.original }))],  // Przywróć zakryte
        anonymized_preview: shownText,  // [LYNX-MANUAL-REVEAL] to samo co ekran i kopia
      }));
      const encDesc = await encryptToBase64(description.trim());

      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res = await fetch(`${API}/archive`, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiToken ? { "X-Api-Token": apiToken } : {}),
        },
        body: JSON.stringify({
          pse:         result.pse_code,
          token_count: result.total,
          enc_blob:    encBlob,
          description: encDesc,
        }),
        signal: ctrl.signal,
      });
      clearTimeout(tid);
      const data = await res.json();
      if (data.ok) {
        setSaved(true);
        setDescription("");
      } else {
        setError(data.error ?? "Błąd zapisu archiwum.");
      }
    } catch {
      setError("Błąd szyfrowania lub zapisu.");
    } finally {
      setSaving(false);
    }
  }

  // [LYNX-GUARD-B] Zakryj z panelu: w tym dokumencie zawsze; do słownika biura gdy zaznaczone i wartość się nadaje
  async function handleCover(ws: GuardWarning[]) {  // wiersz panelu = te same słowo (×N) — wszystkie wskazane wystąpienia
    if (!result || ws.length === 0) return;
    const w = ws[0];
    setCovered(s => { const n = new Set(s); ws.forEach(x => n.add(warningKey(result.anonymized_preview, x))); return n; });
    setSaved(false);
    const type = coverTypeFor(w, resultMap);  // słownik biura przyjmuje OSOBA/FIRMA/NUMER/ADRES
    if (expressMode || !remember || !rememberable(w.fragment) || !["OSOBA", "FIRMA", "NUMER", "ADRES"].includes(type)) return;
    try {
      const res = await fetch(`${API}/profile/add-entity`, { method: "POST", headers: { "Content-Type": "application/json",
        ...(apiToken ? { "X-Api-Token": apiToken } : {}) }, body: JSON.stringify({ text: w.fragment.trim(), token_type: type }) });
      const data = await res.json();
      if (!data.ok) setError(`Zakryto w tym dokumencie; słownik biura: ${data.error ?? "nie udało się zapisać"}.`);
    } catch { setError("Zakryto w tym dokumencie, ale nie udało się zapisać w słowniku biura."); }
  }

  // ── Dodaj encję i od razu ponów pseudonimizację ────────────

  async function handleAddEntity() {
    if (!missedText.trim() || addingEntity || !result) return;
    setAddingEntity(true);
    setAddedToken("");
    setError("");
    try {
      const ctrl = new AbortController();
      const tid = setTimeout(() => ctrl.abort(), 30_000);
      const res = await fetch(`${API}/profile/add-entity`, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiToken ? { "X-Api-Token": apiToken } : {}),
        },
        body: JSON.stringify({ text: missedText.trim(), token_type: missedType }),
        signal: ctrl.signal,
      });
      clearTimeout(tid);
      const data = await res.json();
      if (!data.ok) {
        setError(data.error ?? "Błąd dodawania encji.");
        return;
      }
      setAddedToken(data.token_id);
      setMissedText("");

      // Re-procesuj oryginalny tekst z nową encją
      const blob = new Blob([result.original_text], { type: "text/plain" });
      const file = new File([blob], "reprocess.txt", { type: "text/plain" });
      const form = new FormData();
      form.append("file", file);
      const headers: Record<string, string> = {};
      if (apiToken) headers["X-Api-Token"] = apiToken;
      const ctrlRe = new AbortController();
      const tidRe = setTimeout(() => ctrlRe.abort(), 30_000);
      const res2 = await fetch(`${API}/preview`, { method: "POST", body: form, headers, signal: ctrlRe.signal });
      clearTimeout(tidRe);
      const data2: PreviewResult = await res2.json();
      if (!data2.blocked) {  // nowy wynik: Zakryj/Zostaw pamiętane po fragmencie+otoczeniu (U2)
        setSaved(false); setGuardBlocked(false);
        setResult(data2);
      }
    } catch {
      setError("Błąd połączenia z backendem.");
    } finally {
      setAddingEntity(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────

  return (
    // [UI-PSE-02] Flex column — eliminuje czarną pustkę
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
        fontSize: 13, letterSpacing: "0.12em", fontFamily: T.mono,
        color: T.blue, textTransform: "uppercase", marginBottom: 20,
        flexShrink: 0,
      }}>
        Pseudonimizuj dokument
      </div>

      {/* ── Strefa wejścia — dwie kolumny ── */}
      {!result && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            style={{ display: "none" }}
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          <input
            ref={imgRef}
            type="file"
            accept=".png,.jpg,.jpeg,.tiff,.bmp,.webp"
            style={{ display: "none" }}
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16, flex: 1, minHeight: 0 }}>

            {/* Lewa kolumna — dropzone */}
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{
                fontSize: 13, color: T.textSecondary, textTransform: "uppercase",
                letterSpacing: "0.1em", marginBottom: 8, flexShrink: 0,
              }}>
                Wgraj plik
              </div>

              {/* Główny dropzone */}
              <div
                onClick={() => !uploading && fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={e => {
                  e.preventDefault();
                  setDragOver(false);
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
                {/* [UI-PSE-01] 15px bazowy */}
                <div style={{ fontSize: 15, color: uploading ? T.blueLight : T.textSecondary, marginBottom: 4 }}>
                  {uploading ? "Pseudonimizuję..." : "Przeciągnij plik lub kliknij"}
                </div>
                <div style={{ fontSize: 13, color: T.textMuted, fontFamily: T.mono }}>
                  PDF · DOCX · TXT · MD
                </div>
              </div>

              {/* OCR przycisk */}
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

            {/* Prawa kolumna — paste textarea */}
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

              {/* [UI-PSE-04] flex:1 — textarea wypełnia dostępną wysokość */}
              <textarea
                ref={pasteRef}
                value={pasteText}
                onChange={e => setPasteText(e.target.value)}
                onDrop={e => {
                  e.preventDefault();
                  const dropped = e.dataTransfer.getData("text");
                  if (dropped) setPasteText(dropped);
                }}
                placeholder={"Ctrl+V — wklej treść dokumentu...\n\nLub przeciągnij tekst tutaj."}
                disabled={uploading}
                style={{
                  flex: 1,
                  boxSizing: "border-box",
                  padding: "12px 14px",
                  background: T.surface,
                  border: `1px solid ${pasteText ? T.borderActive : T.border}`,
                  borderRadius: 8,
                  color: T.textSecondary,
                  fontSize: 15, lineHeight: 1.6,  // [UI-PSE-01]
                  fontFamily: T.sans,
                  resize: "none",
                  outline: "none",
                  transition: "border-color 0.15s",
                  minHeight: 160,  // [UI-PSE-04]
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

          {/* Info o pierwszeństwie */}
          {pasteText.trim() && (
            <div style={{
              fontSize: 14, color: T.textSecondary, marginBottom: 12, flexShrink: 0,
              padding: "6px 12px", background: T.surface,
              border: `1px solid ${T.border}`, borderRadius: 6,
            }}>
              ℹ Jeśli wgrasz plik — zastąpi wklejony tekst.
            </div>
          )}

          {/* Błąd na etapie wejścia */}
          {error && (
            <div style={{
              background: T.redBg, border: `1px solid ${T.redBorder}`,
              borderRadius: 8, padding: "10px 16px", flexShrink: 0,
              fontSize: 15, color: T.red, lineHeight: 1.5,
            }}>
              ✕ {error}
              {ocrRejected && (
                <button onClick={() => { setError(""); setOcrRejected(false); pasteRef.current?.focus(); }}
                  style={{ marginLeft: 12, padding: "4px 12px", borderRadius: 6, fontSize: 14, cursor: "pointer" }}>
                  Wklej tekst
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Wynik pseudonimizacji ── */}
      {/* [UI-PSE-02] flex:1 + overflowY:auto — eliminuje pustkę na dole */}
      {result && !ocrWarning && (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflowY: "auto" }}>

          {/* Pasek tytułowy z PSE + przyciski Kopiuj PSE / Kopiuj tekst / Nowy dokument */}
          <div style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "center", marginBottom: 16, flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {/* PSE badge */}
              <span style={{
                fontFamily: T.mono, fontSize: 14, color: T.blueLight,
                background: T.blueBg, border: `1px solid ${T.borderActive}`,
                padding: "3px 10px", borderRadius: 4, letterSpacing: "0.08em",
              }}>
                {result.pse_code}
              </span>
              {/* [UI-PSE-05] Kopiuj PSE */}
              <button
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(result.pse_code);
                    setCopiedPse(true);
                    setTimeout(() => setCopiedPse(false), 2000);
                  } catch { /* brak clipboard */ }
                }}
                style={{
                  fontSize: 13, padding: "3px 10px",
                  background: copiedPse ? T.greenBg : T.surface,
                  border: `1px solid ${copiedPse ? T.greenBorder : T.border}`,
                  borderRadius: 4,
                  color: copiedPse ? T.green : T.textMuted,
                  cursor: "pointer", fontFamily: T.mono,
                  transition: "all 0.15s",
                }}
              >
                {copiedPse ? "✓ PSE skopiowane" : "↗ Kopiuj PSE"}
              </button>
              {/* [UI-PSE-06] Kopiuj tekst — [LYNX-FAILCLOSED-S3] niedostępne przy blokadzie Guarda */}
              <button
                disabled={locked}
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(shownText);
                    setCopiedText(true);
                    setTimeout(() => setCopiedText(false), 2000);
                  } catch { /* brak clipboard */ }
                }}
                style={{
                  fontSize: 13, padding: "3px 10px",
                  background: copiedText ? T.blueBg : T.surface,
                  border: `1px solid ${copiedText ? T.borderActive : T.border}`,
                  borderRadius: 4,
                  color: copiedText ? T.blueLight : T.textMuted, opacity: locked ? 0.4 : 1,
                  cursor: locked ? "not-allowed" : "pointer", fontFamily: T.mono,
                  transition: "all 0.15s",
                }}
              >
                {copiedText ? "✓ Tekst skopiowany" : "↗ Kopiuj tekst"}
              </button>
              {!result.anonymizer_active && (
                <span style={{ fontSize: 14, color: T.amber }}>
                  ⚠ anonymizer nieaktywny
                </span>
              )}
            </div>
            {/* [UI-PSE-03] Przycisk Nowy dokument */}
            <button
              onClick={() => {
                setResult(null); setError(""); setSaved(false);
                setAddedToken(""); setPasteText("");
                setCopiedPse(false); setCopiedText(false);
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
            {!guardBlocked && <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 6, userSelect: "none" }}>
              Jeśli LynxMask zakrył coś niepotrzebnie, kliknij token, żeby odkryć tylko to miejsce. Odkryta wartość znajdzie się
              także w kopiowanym i zapisanym tekście.</div>}
            <HighlightedText text={base} map={tokenMap} revealed={revealed}
              onToggle={guardBlocked ? undefined : (at, tok) => {
                setRevealed(r => toggleReveal(r, at, tok, tokenMap));
                setSaved(false);  // [LYNX-MANUAL-REVEAL F1] nowa treść = do zapisania (ten sam PSE nadpisuje archiwum)
              }} />
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

          {/* Dodaj pominiętą encję + Zapisz do biblioteki — tylko po zalogowaniu (token Express: wyłącznie /preview) */}
          {!expressMode && (<>
          <div style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: 8, padding: "12px 16px", marginBottom: 16,
            flexShrink: 0,
          }}>
            <div style={{
              fontSize: 13, color: T.textSecondary,
              textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10,
            }}>
              Zaznacz tekst powyżej lub wpisz ręcznie → dodaj do profilu biura
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={missedText}
                onChange={e => { setMissedText(e.target.value); setAddedToken(""); }}
                onKeyDown={e => e.key === "Enter" && handleAddEntity()}
                placeholder="np. ul. Lipowa 14"
                style={{
                  flex: 1, padding: "8px 12px",
                  background: T.bg, border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textPrimary, fontSize: 16,
                  fontFamily: T.sans, outline: "none", minWidth: 0,
                }}
              />
              <select
                value={missedType}
                onChange={e => setMissedType(e.target.value)}
                style={{
                  padding: "8px 10px",
                  background: T.bg, border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textSecondary,
                  fontSize: 15, cursor: "pointer", outline: "none",
                }}
              >
                <option value="OSOBA">OSOBA</option>
                <option value="FIRMA">FIRMA</option>
                <option value="ADRES">ADRES</option>
                <option value="NUMER">NUMER</option>
              </select>
              {/* [UI-PSE-03] Spójny styl przycisku */}
              <button
                onClick={handleAddEntity}
                disabled={!missedText.trim() || addingEntity}
                style={{
                  padding: "8px 16px",
                  background: missedText.trim() && !addingEntity ? T.blue : T.surface,
                  border: `1px solid ${missedText.trim() ? T.blue : T.border}`,
                  borderRadius: 6,
                  color: missedText.trim() && !addingEntity ? "#fff" : T.textMuted,
                  fontSize: 15, cursor: missedText.trim() && !addingEntity ? "pointer" : "not-allowed",
                  fontWeight: 500, whiteSpace: "nowrap",
                  transition: "background 0.15s",
                }}
              >
                {addingEntity ? "▸ Zakrywam..." : "→ Dodaj i zakryj"}
              </button>
            </div>
            {addedToken && (
              <div style={{ fontSize: 14, color: T.green, marginTop: 8 }}>
                ✓ Dodano jako {addedToken} — dokument zaktualizowany
              </div>
            )}
          </div>

          {/* Zapisz do biblioteki */}
          {saved ? (
            <div style={{
              background: T.greenBg, border: `1px solid ${T.greenBorder}`,
              borderRadius: 8, padding: "12px 16px", flexShrink: 0,
              fontSize: 16, color: T.green,
            }}>
              ✓ Zapisano w bibliotece jako {result.pse_code}
            </div>
          ) : (
            <div style={{
              background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: 8, padding: "12px 16px", flexShrink: 0,
              display: "flex", gap: 10, alignItems: "center",
            }}>
              <input
                value={description}
                onChange={e => setDescription(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSave()}
                placeholder="Opis dokumentu (szyfrowany)..."
                style={{
                  flex: 1, padding: "8px 12px",
                  background: T.bg, border: `1px solid ${T.border}`,
                  borderRadius: 6, color: T.textPrimary, fontSize: 16,
                  fontFamily: T.sans, outline: "none", minWidth: 0,
                }}
              />
              {/* [UI-PSE-03] Spójny styl przycisku Zapisz */}
              <button
                onClick={() => handleSave()}
                disabled={!description.trim() || saving || locked}
                style={{
                  padding: "8px 20px",
                  background: description.trim() && !locked ? T.blue : T.surface,
                  border: `1px solid ${description.trim() && !locked ? T.blue : T.border}`,
                  borderRadius: 6,
                  color: description.trim() && !locked ? "#fff" : T.textMuted,
                  fontSize: 15, fontWeight: 500,
                  cursor: description.trim() && !saving && !locked ? "pointer" : "not-allowed",
                  whiteSpace: "nowrap", transition: "background 0.15s",
                }}
              >
                {saving ? "▸ Zapisuję..." : "▸ Zapisz"}
              </button>
            </div>
          )}
          </>)}

        </div>
      )}

      {/* OCR warning — dialog niskiej jakości */}
      {/* [OCR-WARN-NULL] Warunek result && result.ocr przed renderem */}
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
              {result.ocr?.engine !== "rapid" && <>Pewność odczytu: {result.ocr?.confidence?.toFixed(0)}%</>}
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
                onClick={() => { setOcrWarning(false); setResult(null); setPendingFile(null); }}
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

      {/* [LYNX-GUARD-B] ostrzeżenia Guarda: decyzja przy każdej pozycji, bez zbiorczego „zapisz mimo to” (S4) */}
      {result && !ocrWarning && <GuardPanel base={result.anonymized_preview} warnings={warnings} pending={pending}
        kept={kept} onCover={handleCover} remember={remember} onRemember={expressMode ? undefined : setRemember}
        onKeep={(keys, keep) => setKept(s => { const n = new Set(s); keys.forEach(k => keep ? n.add(k) : n.delete(k)); return n; })} />}
      {guardBlocked && result && (
        <div style={{ background: T.redBg, border: `1px solid ${T.redBorder}`, borderRadius: 8, padding: "12px 16px",
          marginTop: 12, fontSize: 15, color: T.red, flexShrink: 0 }}>
          ⛔ Nie udało się sprawdzić dokumentu. Spróbuj ponownie; jeśli problem się powtarza, zgłoś błąd.
        </div>
      )}

      {/* Błąd ogólny */}
      {error && !guardBlocked && (
        <div style={{
          background: T.redBg, border: `1px solid ${T.redBorder}`,
          borderRadius: 8, padding: "10px 16px", marginTop: 12,
          fontSize: 15, color: T.red, lineHeight: 1.5, flexShrink: 0,
        }}>
          ✕ {error}
        </div>
      )}

    </div>
  );
}
