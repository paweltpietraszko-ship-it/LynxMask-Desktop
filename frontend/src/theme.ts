// Pseudominizer — src/theme.ts  v2.7
// ============================================================
// ZMIANY v2.7: Przeprojektowanie jasnego motywu
//   Zamiast płaskiej szarości — ciepły slate z wyraźną głębią warstw:
//   bg (tło) ciemniejsze niż surface (karty) — jak Notion/Linear light
//   Karty mają lekki cień zamiast samego obramowania
//   Sidebar jeszcze ciemniejszy od tła — wyraźna separacja
//   Tekst: głęboki atrament (nie czerń, nie szarość)
// ============================================================
// ZMIANY v2.6: Korekta tekstu jasnego, czcionki globalne
// ZMIANY v2.4: Jasny motyw — dwie palety, mutowalny T
// ZMIANY v2.3: ZERO szarości w tekście (ciemny motyw)
// ============================================================

export type Theme = typeof DARK;

export const DARK = {
  bg:      "#0f1117",
  surface: "#22252b",
  sidebar: "#0d0f14",

  border:       "#2e3138",
  borderActive: "#3b82f6",

  textPrimary:   "#F5F7FA",
  textSecondary: "#D1D5DB",
  textMuted:     "#B8BEC8",
  textDim:       "#8899bb",
  text:          "#F5F7FA",

  blue:      "#3b82f6",
  blueLight: "#60A5FA",
  blueBg:    "#1e2d4a",
  activeNav: "#1a1f2e",

  green:       "#22c55e",
  greenBg:     "#052e16",
  greenBorder: "#166534",

  red:       "#f87171",
  redBg:     "#1c0808",
  redBorder: "#7f1d1d",

  amber:       "#fbbf24",
  amberBg:     "#2d1a00",
  amberBorder: "#92400e",

  sans: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
} as const;

export const LIGHT: Theme = {
  // Warstwy z wyraźną głębią — tło ciemniejsze od kart (jak Notion light)
  bg:      "#E2E6ED",   // tło strony — wyraźnie ciemniejsze
  surface: "#F0F2F6",   // karty, panele — jaśniejsze od tła
  sidebar: "#D4D9E2",   // sidebar — najciemniejszy element

  border:       "#B0B8C8",
  borderActive: "#1D4ED8",

  // Tekst — głęboki atrament, zero szarości
  textPrimary:   "#0A0E1A",   // prawie czerń z nutą granatu
  textSecondary: "#1A2540",   // atramentowy
  textMuted:     "#2D4070",   // średni granat
  textDim:       "#4A6090",   // jaśniejszy granat
  text:          "#0A0E1A",

  // Niebieski — głęboki, czytelny na jasnym tle
  blue:      "#1D4ED8",
  blueLight: "#2563EB",
  blueBg:    "#DBEAFE",
  activeNav: "#C8D4EE",

  // Sukces
  green:       "#16A34A",
  greenBg:     "#DCFCE7",
  greenBorder: "#34D468",

  // Błąd
  red:       "#DC2626",
  redBg:     "#FEE2E2",
  redBorder: "#F06060",

  // Ostrzeżenie
  amber:       "#D97706",
  amberBg:     "#FEF3C7",
  amberBorder: "#F0A020",

  sans: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace",
};

export const T: Theme = { ...DARK };

export type ThemeMode = "dark" | "light";

export function applyTheme(mode: ThemeMode): void {
  const palette = mode === "light" ? LIGHT : DARK;
  (Object.keys(palette) as (keyof Theme)[]).forEach(key => {
    (T as any)[key] = palette[key];
  });
}
