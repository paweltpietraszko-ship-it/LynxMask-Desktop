# Pseudominizer v1.0 — Krok 1: Scaffold

## Co tu jest

Gotowy szkielet Tauri v2 + React + TypeScript.
- **Ekran hasła** — PBKDF2-HMAC-SHA256 (500k iter), AES-256-GCM, klucz w Rust State
- **Sidebar** z nawigacją i linkiem do Triangulum (:8000)
- **Placeholder** dla ekranów 2-4

Krok 1 kończy się gdy `cargo tauri dev` uruchamia okno i przycisk "Odblokuj" działa.

---

## Wymagania (sprawdź zanim zaczniesz)

```
node --version   # >= 18
npm --version    # >= 9
rustc --version  # >= 1.75  (masz zainstalowany)
cargo tauri --version  # powinno dać: tauri-cli 2.x
```

Jeśli `cargo tauri` nie istnieje:
```
cargo install tauri-cli --version "^2" --locked
```

---

## Uruchomienie

```bash
# 1. Wejdź do katalogu projektu
cd pseudominizer

# 2. Zainstaluj zależności JS
npm install

# 3. Uruchom w trybie dev (pierwsze uruchomienie: Cargo pobiera ~50 pakietów, ~5 min)
npm run tauri dev
```

Powinno otworzyć się okno Pseudominizer z ekranem hasła.
Wpisz cokolwiek i kliknij "Odblokuj" — jeśli zobaczysz sidebar, Krok 1 gotowy.

---

## Potencjalne problemy

### `error[E0432]: unresolved import` w main.rs
Upewnij się że Cargo.toml ma wersje: `aes-gcm = "0.10"`, `pbkdf2 = "0.12"`, `rand = "0.8"`.

### Okno się otwiera ale kliknięcie Odblokuj nie robi nic
Otwórz DevTools (F12 w trybie dev) i sprawdź konsolę. Najczęstszy powód:
brak odpowiedzi z Rust — sprawdź czy `derive_and_store_key` jest w `generate_handler![]`.

### `connect-src` blokuje :8765
Sprawdź `tauri.conf.json` → `app.security.csp`. Musi być:
`connect-src 'self' http://127.0.0.1:8765 ...`

### Kompilacja Rust trwa wieki
Normalne przy pierwszym `cargo build`. Kolejne są szybkie (incremental).

---

## Następne kroki po Kroku 1

**Krok 2** — `src/screens/Pseudonimizuj.tsx`
- Upload pliku → POST /upload → anonymized text + token table
- Żółty wiersz dla pominiętych encji → POST /profile/add-entity
- "Zapisz do biblioteki" → invoke("encrypt_data") → POST /archive

**Krok 3** — `src/screens/Biblioteka.tsx`
- GET /archive → lista, invoke("decrypt_data") na opis
- Wyszukiwarka (decrypt all, filter JS)
- Pole odpowiedzi AI + PSE autodetekt

**Krok 4** — `src/screens/Depseudonimizuj.tsx`
- Wklej tekst → GET /archive/map/{pse} → invoke("decrypt_data") → podmiana tokenów

---

## Architektura krypto (dla następnych instancji)

Klucz **nigdy** nie opuszcza Rust. Schemat:

```
hasło (JS) → invoke("derive_and_store_key")
                → PBKDF2(hasło, salt.bin, 500k) → [u8;32] w Mutex<State>

dane (JS)  → invoke("encrypt_data", plaintext: Vec<u8>)
                → AES-256-GCM(klucz, nonce) → nonce(12B) + ciphertext+tag
                ← Vec<u8> (ciphertext) → JS przesyła do backendu

ciphertext (JS) → invoke("decrypt_data", ciphertext: Vec<u8>)
                → AES-256-GCM.decrypt → plaintext
                ← Vec<u8> → JS wyświetla
```

salt.bin: `%APPDATA%\Pseudominizer\salt.bin` (generowany przy pierwszym uruchomieniu)

Brak migracji starych .enc plików — nowy start.
