// guardAllowlist.ts — [LYNX-GUARD-ALLOWLIST-S5] „Zawsze jawne”: zaszyfrowana lista (fragment, reguła) w silniku, tylko żółte.
// Wartości wyłącznie w treści żądań (nie w adresie URL). Błąd silnika → wyjątek z komunikatem dla użytkownika.
import { GuardWarning } from "./guardDecisions";

const API = "http://127.0.0.1:8765";

export interface AllowEntry { value: string; rule: string }

async function call(path: string, apiToken: string, body?: object) {
  const res = await fetch(`${API}/profile/guard-allowlist${path}`, {
    method: body ? "POST" : "GET",
    headers: { "X-Api-Token": apiToken, ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? "Błąd połączenia z silnikiem.");
  return data;
}

const KIND: Record<string, string> = {
  R1: "Możliwe nazwisko", R2: "Inicjał przy osobie", R3: "Resztka numeru lub adresu", R4: "Numer lub data",
  R5: "Możliwa firma", MAP_LEAK: "Wartość zamaskowana w innym miejscu", "*": "Każde żółte ostrzeżenie",
};
export const ruleLabel = (rule: string) => KIND[rule] ?? rule.replace(/^(HIGH|MEDIUM) /, "").replace("_OCR", "");

/** Wszystkie reguły ostrzeżenia (silnik łączy nakładające się trafienia w jedną pozycję). */
export const rulesOf = (w: GuardWarning): string[] => (w as GuardWarning & { rules?: string[] }).rules ?? [w.rule];
export const listAllow = (t: string): Promise<{ entries: AllowEntry[]; damaged: boolean }> => call("", t);
export const addAllow = (t: string, value: string, rules: string[]) => call("", t, { value, rules });
export const removeAllow = (t: string, e: AllowEntry) => call("/remove", t, e);
export const clearAllow = (t: string) => call("/clear", t, {});
