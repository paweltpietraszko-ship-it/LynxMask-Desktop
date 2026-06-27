// Pseudominizer — src-tauri/src/main.rs  v1.7
// ============================================================
// ZMIANY W TEJ WERSJI: Potok 4 Biblioteka — komendy odpowiedzi AI
// ============================================================
// Dodane funkcje (po save_depseudo_result):
//   list_depseudo_responses(pse) → Result<Vec<String>, String>
//     Linia ~310: Zwraca posortowaną listę plików odpowiedz_NNN.txt
//     ze ścieżki Documents\Pseudominizer\{pse}\
//     Jeśli folder nie istnieje → pusta lista (nie błąd).
//
//   read_depseudo_response(pse, filename) → Result<String, String>
//     Linia ~335: Czyta treść konkretnego pliku odpowiedzi.
//     Sanityzuje filename — odrzuca / \ .. aby zapobiec path traversal.
//
// Zarejestrowane w invoke_handler (linia ~375).
// Żadna istniejąca funkcja nie została zmieniona.
//
// Poprzednia wersja: v1.4 [BUG-4 + OsRng hardening]
// ============================================================

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{State, Manager};
use aes_gcm::{aead::{Aead, KeyInit}, Aes256Gcm, Nonce};
use pbkdf2::pbkdf2_hmac;
use sha2::Sha256;
use rand::{RngCore, rngs::OsRng};

const PBKDF2_ITER: u32  = 500_000;
const SALT_LEN:   usize = 16;
const KEY_LEN:    usize = 32;
const NONCE_LEN:  usize = 12;

/// Stały ciąg do weryfikacji hasła (known plaintext).
const KEY_VERIFY_PLAINTEXT: &[u8] = b"PSEUDOMINIZER_OK";

// Ścieżka do katalogu backendu względem exe Tauri.
const BACKEND_TOKEN_FILENAME: &str = "api_token.txt";
const STARTUP_ERROR_FILENAME: &str = "startup_error.json";

struct AppKey(Mutex<Option<[u8; KEY_LEN]>>);

// --- Sól: %APPDATA%\Pseudominizer\salt.bin ---

fn salt_path(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join("salt.bin"))
}

fn load_or_create_salt(path: &std::path::Path) -> Result<[u8; SALT_LEN], String> {
    if path.exists() {
        let b = std::fs::read(path).map_err(|e| e.to_string())?;
        if b.len() != SALT_LEN {
            return Err("salt.bin uszkodzony — usuń plik i uruchom ponownie.".into());
        }
        let mut s = [0u8; SALT_LEN];
        s.copy_from_slice(&b);
        Ok(s)
    } else {
        let mut s = [0u8; SALT_LEN];
        OsRng.fill_bytes(&mut s);
        std::fs::write(path, &s).map_err(|e| e.to_string())?;
        Ok(s)
    }
}

// --- Weryfikator: %APPDATA%\Pseudominizer\key_verify.bin ---

fn verify_path(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    Ok(dir.join("key_verify.bin"))
}

// --- Szyfrowanie wewnętrzne (klucz jako slice, nie z State) ---
// Używane wyłącznie przez derive_and_store_key do zapisu key_verify.bin.
// Format identyczny jak encrypt_data: nonce(12B) + ciphertext+tag.

fn encrypt_with_key(plaintext: &[u8], key: &[u8; KEY_LEN]) -> Result<Vec<u8>, String> {
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| e.to_string())?;
    let mut nonce_bytes = [0u8; NONCE_LEN];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ct = cipher.encrypt(nonce, plaintext)
        .map_err(|e| e.to_string())?;

    let mut out = Vec::with_capacity(NONCE_LEN + ct.len());
    out.extend_from_slice(&nonce_bytes);
    out.extend_from_slice(&ct);
    Ok(out)
}

fn decrypt_with_key(ciphertext: &[u8], key: &[u8; KEY_LEN]) -> Result<Vec<u8>, String> {
    if ciphertext.len() < NONCE_LEN + 16 {
        return Err("Dane za krótkie — uszkodzone?".into());
    }
    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| e.to_string())?;
    let nonce = Nonce::from_slice(&ciphertext[..NONCE_LEN]);

    cipher.decrypt(nonce, &ciphertext[NONCE_LEN..])
        .map_err(|_| "WRONG_PASSWORD".into())
}

// --- Szuka api_token.txt w kilku miejscach ---
// Kolejność: zmienna środowiskowa PSEUDOMINIZER_BACKEND_DIR,
// potem katalog obok exe, potem Desktop\pseudominizer\ (hardcoded fallback dla dev).
fn find_token_file() -> Result<std::path::PathBuf, String> {
    // 1. Zmienna środowiskowa (najczystsze rozwiązanie produkcyjne)
    if let Ok(dir) = std::env::var("PSEUDOMINIZER_BACKEND_DIR") {
        let p = std::path::PathBuf::from(dir).join(BACKEND_TOKEN_FILENAME);
        if p.exists() { return Ok(p); }
    }

    // 2. Katalog exe (dla bundled release gdzie backend leży obok)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let p = dir.join(BACKEND_TOKEN_FILENAME);
            if p.exists() { return Ok(p); }
            // 3. Dla dev: exe w target/debug/, backend w Desktop\LynxMask-Desktop\backend\
            for up in 1..=5 {
                let mut candidate = dir.to_path_buf();
                for _ in 0..up { candidate = match candidate.parent() {
                    Some(p) => p.to_path_buf(),
                    None => break,
                };}
                let p = candidate.join("backend").join(BACKEND_TOKEN_FILENAME);
                if p.exists() { return Ok(p); }
                let p = candidate.join("LynxMask-Desktop").join("backend").join(BACKEND_TOKEN_FILENAME);
                if p.exists() { return Ok(p); }
                let p2 = candidate.join(BACKEND_TOKEN_FILENAME);
                if p2.exists() { return Ok(p2); }
            }
        }
    }

    // 4. Hardcoded dev fallback — Desktop\LynxMask-Desktop\backend\api_token.txt
    if let Ok(home) = std::env::var("USERPROFILE") {
        let p = std::path::PathBuf::from(&home)
            .join("Desktop")
            .join("LynxMask-Desktop")
            .join("backend")
            .join(BACKEND_TOKEN_FILENAME);
        if p.exists() { return Ok(p); }
        // Legacy fallback — stara ścieżka przed migracją 2026-06-25
        let p = std::path::PathBuf::from(home)
            .join("Desktop")
            .join("pseudominizer")
            .join(BACKEND_TOKEN_FILENAME);
        if p.exists() { return Ok(p); }
    }

    Err(format!("Nie znaleziono {}. Sprawdź czy backend jest uruchomiony.", BACKEND_TOKEN_FILENAME))
}

// Zwraca katalog backendu (bez wymagania istnienia konkretnego pliku).
// Używane przez read_startup_error — plik może nie istnieć, szukamy samego katalogu.
fn find_backend_dir() -> Option<std::path::PathBuf> {
    if let Ok(dir) = std::env::var("PSEUDOMINIZER_BACKEND_DIR") {
        let p = std::path::PathBuf::from(dir);
        if p.is_dir() { return Some(p); }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            if dir.join(STARTUP_ERROR_FILENAME).exists()
                || dir.join(BACKEND_TOKEN_FILENAME).exists()
            {
                return Some(dir.to_path_buf());
            }
            for up in 1..=5 {
                let mut candidate = dir.to_path_buf();
                for _ in 0..up { candidate = match candidate.parent() {
                    Some(p) => p.to_path_buf(),
                    None => break,
                };}
                let d = candidate.join("backend");
                if d.is_dir() { return Some(d); }
                let d = candidate.join("LynxMask-Desktop").join("backend");
                if d.is_dir() { return Some(d); }
            }
        }
    }
    if let Ok(home) = std::env::var("USERPROFILE") {
        let d = std::path::PathBuf::from(&home)
            .join("Desktop").join("LynxMask-Desktop").join("backend");
        if d.is_dir() { return Some(d); }
        let d = std::path::PathBuf::from(home)
            .join("Desktop").join("pseudominizer");
        if d.is_dir() { return Some(d); }
    }
    // Linux dev fallback (HOME)
    if let Ok(home) = std::env::var("HOME") {
        let d = std::path::PathBuf::from(&home)
            .join("LynxMask-Desktop").join("backend");
        if d.is_dir() { return Some(d); }
        let d = std::path::PathBuf::from(home)
            .join("Desktop").join("LynxMask-Desktop").join("backend");
        if d.is_dir() { return Some(d); }
    }
    None
}

// Walidacja formatu PSE przed użyciem w ścieżce pliku.
// Zapobiega path traversal przez parametr pse w komendach zapisu/odczytu.
fn validate_pse(pse: &str) -> Result<(), String> {
    let b = pse.as_bytes();
    let valid = b.len() == 13
        && &b[..4] == b"PSE-"
        && b[4..8].iter().all(|c| c.is_ascii_digit())
        && b[8] == b'-'
        && b[9..13].iter().all(|c| c.is_ascii_digit());
    if valid { Ok(()) } else { Err("Nieprawidłowy format PSE — oczekiwano PSE-DDDD-DDDD.".into()) }
}

// --- Komendy Tauri ---

/// Czyta api_token.txt z katalogu backendu i zwraca token jako String.
/// Wywoływana przez front po odblokowaniu aplikacji.
#[tauri::command]
fn read_api_token() -> Result<String, String> {
    let path = find_token_file()?;
    let token = std::fs::read_to_string(&path)
        .map_err(|e| format!("Błąd odczytu {}: {}", BACKEND_TOKEN_FILENAME, e))?;
    let token = token.trim().to_string();
    if token.is_empty() {
        return Err("api_token.txt jest pusty — uruchom backend.".into());
    }
    Ok(token)
}

/// Czyta startup_error.json z katalogu backendu (jeśli istnieje) i zwraca jako String.
/// Gdy plik nie istnieje zwraca błąd — caller traktuje to jako "brak błędu startu".
#[tauri::command]
fn read_startup_error() -> Result<String, String> {
    let dir = find_backend_dir()
        .ok_or_else(|| "Nie znaleziono katalogu backendu.".to_string())?;
    let path = dir.join(STARTUP_ERROR_FILENAME);
    if !path.exists() {
        return Err("brak".into());
    }
    std::fs::read_to_string(&path)
        .map_err(|e| format!("Błąd odczytu startup_error.json: {}", e))
}

/// Restartuje aplikację (zamknij + uruchom ponownie).
#[tauri::command]
fn restart_app(app: tauri::AppHandle) {
    app.restart();
}

/// Wyprowadza klucz AES-256 z hasła przez PBKDF2 i trzyma go w State.
///
/// BUG-4: Weryfikacja przez known plaintext.
///
/// Pierwsze uruchomienie (key_verify.bin nie istnieje):
///   Klucz jest wyprowadzany, "PSEUDOMINIZER_OK" szyfrowane aktualnym kluczem
///   i wynik zapisywany do key_verify.bin. State zostaje ustawiony.
///
/// Kolejne uruchomienia (key_verify.bin istnieje):
///   Klucz jest wyprowadzany, key_verify.bin odszyfrowany aktualnym kluczem.
///   Jeśli wynik == "PSEUDOMINIZER_OK" → State zostaje ustawiony.
///   Jeśli wynik różny lub błąd odszyfrowania → State pozostaje None,
///   zwracany jest błąd "WRONG_PASSWORD".
#[tauri::command]
fn derive_and_store_key(
    password: String,
    app: tauri::AppHandle,
    state: State<AppKey>,
) -> Result<(), String> {
    let sp = salt_path(&app)?;
    let salt = load_or_create_salt(&sp)?;

    let mut key = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(password.as_bytes(), &salt, PBKDF2_ITER, &mut key);

    let vp = verify_path(&app)?;

    if vp.exists() {
        // Weryfikacja: próbujemy odszyfrować key_verify.bin aktualnym kluczem.
        let blob = std::fs::read(&vp).map_err(|e| e.to_string())?;
        let plaintext = decrypt_with_key(&blob, &key)?;
        // decrypt_with_key zwraca "WRONG_PASSWORD" jako Err przy złym kluczu.
        // Jeśli deszyfrowało się poprawnie — sprawdzamy czy to właściwy ciąg.
        if plaintext != KEY_VERIFY_PLAINTEXT {
            return Err("WRONG_PASSWORD".into());
        }
        // Hasło poprawne — zapisz klucz do State.
        *state.0.lock().map_err(|_| "Błąd mutex")? = Some(key);
    } else {
        // Pierwsze uruchomienie: utwórz weryfikator.
        let blob = encrypt_with_key(KEY_VERIFY_PLAINTEXT, &key)?;
        std::fs::write(&vp, &blob).map_err(|e| e.to_string())?;
        // Zapisz klucz do State.
        *state.0.lock().map_err(|_| "Błąd mutex")? = Some(key);
    }

    Ok(())
}

/// Szyfruje bajty kluczem sesji. Format wyniku: nonce(12B) + ciphertext+tag.
#[tauri::command]
fn encrypt_data(plaintext: Vec<u8>, state: State<AppKey>) -> Result<Vec<u8>, String> {
    let guard = state.0.lock().map_err(|_| "Błąd mutex")?;
    let key = guard.as_ref().ok_or("Aplikacja nie jest odblokowana.")?;

    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| e.to_string())?;
    let mut nonce_bytes = [0u8; NONCE_LEN];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ct = cipher.encrypt(nonce, plaintext.as_ref())
        .map_err(|e| e.to_string())?;

    let mut out = Vec::with_capacity(NONCE_LEN + ct.len());
    out.extend_from_slice(&nonce_bytes);
    out.extend_from_slice(&ct);
    Ok(out)
}

/// Deszyfruje blob (nonce + ciphertext+tag) kluczem sesji.
#[tauri::command]
fn decrypt_data(ciphertext: Vec<u8>, state: State<AppKey>) -> Result<Vec<u8>, String> {
    if ciphertext.len() < NONCE_LEN + 16 {
        return Err("Dane za krótkie — uszkodzone?".into());
    }
    let guard = state.0.lock().map_err(|_| "Błąd mutex")?;
    let key = guard.as_ref().ok_or("Aplikacja nie jest odblokowana.")?;

    let cipher = Aes256Gcm::new_from_slice(key).map_err(|e| e.to_string())?;
    let nonce = Nonce::from_slice(&ciphertext[..NONCE_LEN]);

    cipher.decrypt(nonce, &ciphertext[NONCE_LEN..])
        .map_err(|_| "Błąd deszyfrowania — zły klucz lub uszkodzone dane.".into())
}

/// Ścieżka pliku weryfikatora klucza odzyskiwania.
fn recovery_path(app: &tauri::AppHandle) -> Result<std::path::PathBuf, String> {
    let dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    Ok(dir.join("key_recovery.bin"))
}

/// Generuje klucz odzyskiwania (24 znaki alnum, 4 grupy po 6 rozdzielone myślnikami).
/// Szyfruje KEY_VERIFY_PLAINTEXT kluczem PBKDF2 wyprowadzonym z tego klucza i zapisuje
/// wynik jako key_recovery.bin. Zwraca klucz jako String do wyświetlenia użytkownikowi.
/// Wymaga aktywnej sesji (State musi mieć klucz).
#[tauri::command]
fn generate_recovery_key(
    app: tauri::AppHandle,
    state: State<AppKey>,
) -> Result<String, String> {
    // Upewnij się że użytkownik jest zalogowany
    {
        let g = state.0.lock().map_err(|_| "Błąd mutex")?;
        if g.is_none() {
            return Err("Aplikacja nie jest odblokowana.".into());
        }
    }

    // Generuj 18 losowych bajtów → 24 znaki base32-like (0-9, A-Z bez O,I,L,U)
    const CHARSET: &[u8] = b"ABCDEFGHJKMNPQRSTVWXYZ0123456789";
    let mut raw = [0u8; 24];
    OsRng.fill_bytes(&mut raw);
    let chars: String = raw.iter()
        .map(|b| CHARSET[(b % 32) as usize] as char)
        .collect();

    // Format: XXXXXX-XXXXXX-XXXXXX-XXXXXX
    let display = format!("{}-{}-{}-{}", &chars[0..6], &chars[6..12], &chars[12..18], &chars[18..24]);

    // Wyprowadź klucz AES z recovery_key (użyj soli z pliku, tak samo jak hasło)
    let sp = salt_path(&app)?;
    let salt = load_or_create_salt(&sp)?;
    let mut rkey = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(display.as_bytes(), &salt, PBKDF2_ITER, &mut rkey);

    // Zapisz weryfikator
    let blob = encrypt_with_key(KEY_VERIFY_PLAINTEXT, &rkey)?;
    let rp = recovery_path(&app)?;
    std::fs::write(&rp, &blob).map_err(|e| e.to_string())?;

    Ok(display)
}

/// Zmiana hasła przy użyciu klucza odzyskiwania (gdy użytkownik zapomniał hasła).
/// recovery_key — klucz w formacie XXXXXX-XXXXXX-XXXXXX-XXXXXX
/// new_password  — nowe hasło
/// Weryfikuje klucz przez key_recovery.bin, re-szyfruje sesje, aktualizuje oba pliki weryfikatorów.
#[tauri::command]
async fn reset_password_with_recovery(
    recovery_key: String,
    new_password: String,
    api_token: String,
    app: tauri::AppHandle,
    state: State<'_, AppKey>,
) -> Result<(), String> {
    use base64::{engine::general_purpose::STANDARD as B64, Engine as _};

    let sp = salt_path(&app)?;
    let salt = load_or_create_salt(&sp)?;

    // Weryfikuj klucz odzyskiwania
    let mut rkey = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(recovery_key.trim().as_bytes(), &salt, PBKDF2_ITER, &mut rkey);

    let rp = recovery_path(&app)?;
    if !rp.exists() {
        return Err("Brak klucza odzyskiwania — nie został wygenerowany.".into());
    }
    let rblob = std::fs::read(&rp).map_err(|e| e.to_string())?;
    let plaintext = decrypt_with_key(&rblob, &rkey)
        .map_err(|_| "WRONG_RECOVERY_KEY".to_string())?;
    if plaintext != KEY_VERIFY_PLAINTEXT {
        return Err("WRONG_RECOVERY_KEY".into());
    }

    // Wyprowadź nowy klucz główny
    let mut new_key = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(new_password.as_bytes(), &salt, PBKDF2_ITER, &mut new_key);

    // Re-szyfruj sesje (bez starego klucza — sesje są już niedostępne przy zapomnianym haśle,
    // więc jeśli użytkownik nie jest zalogowany, pomijamy re-szyfrowanie sesji)
    let is_logged_in = state.0.lock().map_err(|_| "Błąd mutex")?.is_some();

    if is_logged_in {
        let old_key = *state.0.lock().map_err(|_| "Błąd mutex")?.as_ref().unwrap();
        let client = reqwest::Client::new();
        let list_resp = client
            .get("http://127.0.0.1:8765/archive")
            .header("x-api-token", &api_token)
            .send().await
            .map_err(|e| format!("Błąd połączenia: {e}"))?;

        if list_resp.status().is_success() {
            let list_json: serde_json::Value = list_resp.json().await.unwrap_or_default();
            let documents = list_json["documents"].as_array().cloned().unwrap_or_default();
            let mut blobs_payload: Vec<serde_json::Value> = Vec::new();

            for doc in &documents {
                let pse = doc["pse"].as_str().unwrap_or("").to_string();
                if !doc["enc_exists"].as_bool().unwrap_or(false) { continue; }

                let blob_resp = client
                    .get(format!("http://127.0.0.1:8765/archive/{pse}/blob"))
                    .header("x-api-token", &api_token)
                    .send().await;
                if let Ok(r) = blob_resp {
                    if r.status().is_success() {
                        if let Ok(j) = r.json::<serde_json::Value>().await {
                            if let Some(enc_b64) = j["enc_blob"].as_str() {
                                if let Ok(enc_bytes) = B64.decode(enc_b64) {
                                    if let Ok(pt) = decrypt_with_key(&enc_bytes, &old_key) {
                                        if let Ok(new_enc) = encrypt_with_key(&pt, &new_key) {
                                            blobs_payload.push(serde_json::json!({
                                                "pse": pse,
                                                "enc_blob": B64.encode(&new_enc),
                                            }));
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if !blobs_payload.is_empty() {
                let _ = client
                    .post("http://127.0.0.1:8765/archive/reencrypt")
                    .header("x-api-token", &api_token)
                    .header("content-type", "application/json")
                    .json(&serde_json::json!({ "blobs": blobs_payload }))
                    .send().await;
            }
        }
    }

    // Zaktualizuj key_verify.bin
    let new_verify = encrypt_with_key(KEY_VERIFY_PLAINTEXT, &new_key)?;
    let vp = verify_path(&app)?;
    std::fs::write(&vp, &new_verify).map_err(|e| e.to_string())?;

    // Unieważnij stary klucz odzyskiwania (bezpieczeństwo — użyty raz)
    std::fs::remove_file(&rp).ok();

    // Zaktualizuj klucz w State
    *state.0.lock().map_err(|_| "Błąd mutex")? = Some(new_key);

    Ok(())
}

/// Zeruje klucz z pamięci. Wywoływana przy zamknięciu okna.
#[tauri::command]
fn clear_key(state: State<AppKey>) {
    if let Ok(mut g) = state.0.lock() {
        *g = None;
    }
}

/// Sprawdza czy klucz jest aktywny (czy użytkownik jest zalogowany).
#[tauri::command]
fn is_unlocked(state: State<AppKey>) -> bool {
    state.0.lock().map(|g| g.is_some()).unwrap_or(false)
}

/// Sprawdza czy to pierwsze uruchomienie (key_verify.bin nie istnieje).
/// Wywoływana przez LockScreen przy starcie — decyduje czy pokazać onboarding.
#[tauri::command]
fn is_first_run(app: tauri::AppHandle) -> bool {
    match verify_path(&app) {
        Ok(p) => !p.exists(),
        Err(_) => false,
    }
}

/// Zapisuje zdepseudonimizowaną odpowiedź do:
/// Dokumenty\Pseudominizer\{pse}\odpowiedz_NNN.txt
/// Zwraca pełną ścieżkę zapisanego pliku.
#[tauri::command]
fn save_depseudo_result(
    pse: String,
    text: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    validate_pse(&pse)?;
    let docs = app.path().document_dir()
        .map_err(|e| format!("Brak folderu Dokumenty: {}", e))?;

    let folder = docs.join("Pseudominizer").join(&pse);
    std::fs::create_dir_all(&folder)
        .map_err(|e| format!("Nie można utworzyć folderu: {}", e))?;

    let next_n = (1u32..)
        .find(|n| !folder.join(format!("odpowiedz_{:03}.txt", n)).exists())
        .ok_or("Zbyt wiele plików w folderze")?;

    let filename = format!("odpowiedz_{:03}.txt", next_n);
    let filepath = folder.join(&filename);

    std::fs::write(&filepath, text.as_bytes())
        .map_err(|e| format!("Błąd zapisu: {}", e))?;

    filepath.to_str()
        .ok_or("Nieprawidłowa ścieżka".into())
        .map(|s| s.to_string())
}

/// Zwraca posortowaną listę plików odpowiedzi AI dla danego PSE.
/// Czyta: Dokumenty\Pseudominizer\{pse}\odpowiedz_NNN.txt
/// Jeśli folder nie istnieje — zwraca pustą listę (nie błąd).
/// Wywoływana przez Bibliotekę przy rozwijaniu węzła dokumentu (lazy load).
#[tauri::command]
fn list_depseudo_responses(
    pse: String,
    app: tauri::AppHandle,
) -> Result<Vec<String>, String> {
    validate_pse(&pse)?;
    let docs = app.path().document_dir()
        .map_err(|e| format!("Brak folderu Dokumenty: {}", e))?;

    let folder = docs.join("Pseudominizer").join(&pse);
    if !folder.exists() {
        return Ok(vec![]);
    }

    let mut files: Vec<String> = std::fs::read_dir(&folder)
        .map_err(|e| format!("Błąd odczytu folderu: {}", e))?
        .filter_map(|entry| {
            let entry = entry.ok()?;
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with("odpowiedz_") && name.ends_with(".txt") {
                Some(name)
            } else {
                None
            }
        })
        .collect();

    files.sort();
    Ok(files)
}

/// Czyta treść konkretnego pliku odpowiedzi AI.
/// Sanityzuje filename — odrzuca / \ .. aby zapobiec path traversal.
/// Wywoływana przez Bibliotekę przy akcjach Kopiuj / Drukuj.
#[tauri::command]
fn read_depseudo_response(
    pse: String,
    filename: String,
    app: tauri::AppHandle,
) -> Result<String, String> {
    validate_pse(&pse)?;
    // Sanityzacja: filename nie może zawierać separatorów ścieżki ani ".."
    if filename.contains('/') || filename.contains('\\') || filename.contains("..") {
        return Err("Nieprawidłowa nazwa pliku.".into());
    }

    let docs = app.path().document_dir()
        .map_err(|e| format!("Brak folderu Dokumenty: {}", e))?;

    let path = docs.join("Pseudominizer").join(&pse).join(&filename);

    std::fs::read_to_string(&path)
        .map_err(|e| format!("Błąd odczytu pliku: {}", e))
}

/// Zmiana hasła szyfrowania.
///
/// Algorytm:
/// 1. Wyprowadza stary klucz z old_password + istniejącą solą.
/// 2. Weryfikuje stary klucz przez key_verify.bin → WRONG_PASSWORD jeśli zły.
/// 3. Wyprowadza nowy klucz z new_password + tą samą solą.
/// 4. Pobiera listę wszystkich PSE z backendu (GET /archive).
/// 5. Dla każdego PSE pobiera blob (GET /archive/{pse}/blob), deszyfruje
///    starym kluczem, szyfruje nowym kluczem.
/// 6. Wysyła wszystkie re-zaszyfrowane bloby do POST /archive/reencrypt.
/// 7. Nadpisuje key_verify.bin nowym kluczem.
/// 8. Aktualizuje klucz w State (użytkownik pozostaje zalogowany).
#[tauri::command]
async fn change_password(
    old_password: String,
    new_password: String,
    api_token: String,
    app: tauri::AppHandle,
    state: State<'_, AppKey>,
) -> Result<(), String> {
    use base64::{engine::general_purpose::STANDARD as B64, Engine as _};

    let sp = salt_path(&app)?;
    let salt = load_or_create_salt(&sp)?;

    // Krok 1: wyprowadź stary klucz i zweryfikuj
    let mut old_key = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(old_password.as_bytes(), &salt, PBKDF2_ITER, &mut old_key);

    let vp = verify_path(&app)?;
    if vp.exists() {
        let blob = std::fs::read(&vp).map_err(|e| e.to_string())?;
        let plaintext = decrypt_with_key(&blob, &old_key)
            .map_err(|_| "WRONG_PASSWORD".to_string())?;
        if plaintext != KEY_VERIFY_PLAINTEXT {
            return Err("WRONG_PASSWORD".into());
        }
    } else {
        return Err("Profil nie jest zainicjowany.".into());
    }

    // Krok 2: wyprowadź nowy klucz
    let mut new_key = [0u8; KEY_LEN];
    pbkdf2_hmac::<Sha256>(new_password.as_bytes(), &salt, PBKDF2_ITER, &mut new_key);

    // Krok 3: pobierz listę PSE z backendu
    let client = reqwest::Client::new();
    let list_resp = client
        .get("http://127.0.0.1:8765/archive")
        .header("x-api-token", &api_token)
        .send()
        .await
        .map_err(|e| format!("Błąd połączenia z backendem: {e}"))?;

    if !list_resp.status().is_success() {
        return Err(format!("Błąd pobierania listy PSE: {}", list_resp.status()));
    }

    let list_json: serde_json::Value = list_resp.json().await
        .map_err(|e| format!("Błąd parsowania listy PSE: {e}"))?;

    let documents = list_json["documents"].as_array()
        .ok_or("Nieprawidłowy format listy dokumentów")?;

    // Krok 4: dla każdego PSE — pobierz blob, re-szyfruj
    let mut blobs_payload: Vec<serde_json::Value> = Vec::new();

    for doc in documents {
        let pse = doc["pse"].as_str().ok_or("Brak pola pse w dokumencie")?.to_string();
        let enc_exists = doc["enc_exists"].as_bool().unwrap_or(false);
        if !enc_exists {
            continue; // brak pliku .enc — pomiń
        }

        let blob_resp = client
            .get(format!("http://127.0.0.1:8765/archive/{pse}/blob"))
            .header("x-api-token", &api_token)
            .send()
            .await
            .map_err(|e| format!("Błąd pobierania bloba {pse}: {e}"))?;

        if !blob_resp.status().is_success() {
            return Err(format!("Błąd pobierania bloba {pse}: {}", blob_resp.status()));
        }

        let blob_json: serde_json::Value = blob_resp.json().await
            .map_err(|e| format!("Błąd parsowania bloba {pse}: {e}"))?;

        let enc_b64 = blob_json["enc_blob"].as_str()
            .ok_or(format!("Brak enc_blob dla {pse}"))?;

        let enc_bytes = B64.decode(enc_b64)
            .map_err(|e| format!("Błąd base64 dla {pse}: {e}"))?;

        // Deszyfruj starym kluczem
        let plaintext = decrypt_with_key(&enc_bytes, &old_key)
            .map_err(|e| format!("Błąd deszyfrowania {pse}: {e}"))?;

        // Szyfruj nowym kluczem
        let new_enc = encrypt_with_key(&plaintext, &new_key)
            .map_err(|e| format!("Błąd szyfrowania {pse}: {e}"))?;

        blobs_payload.push(serde_json::json!({
            "pse": pse,
            "enc_blob": B64.encode(&new_enc),
        }));
    }

    // Krok 5: wyślij re-zaszyfrowane bloby do backendu
    if !blobs_payload.is_empty() {
        let reenc_resp = client
            .post("http://127.0.0.1:8765/archive/reencrypt")
            .header("x-api-token", &api_token)
            .header("content-type", "application/json")
            .json(&serde_json::json!({ "blobs": blobs_payload }))
            .send()
            .await
            .map_err(|e| format!("Błąd wysyłania nowych blobów: {e}"))?;

        if !reenc_resp.status().is_success() {
            let err: serde_json::Value = reenc_resp.json().await.unwrap_or_default();
            return Err(format!("Błąd reencrypt: {}", err["error"].as_str().unwrap_or("nieznany")));
        }
    }

    // Krok 6: zaktualizuj key_verify.bin nowym kluczem
    let new_verify_blob = encrypt_with_key(KEY_VERIFY_PLAINTEXT, &new_key)?;
    std::fs::write(&vp, &new_verify_blob).map_err(|e| e.to_string())?;

    // Krok 7: zaktualizuj klucz w State
    *state.0.lock().map_err(|_| "Błąd mutex")? = Some(new_key);

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(AppKey(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            derive_and_store_key,
            encrypt_data,
            decrypt_data,
            clear_key,
            is_unlocked,
            is_first_run,
            save_depseudo_result,
            read_api_token,
            read_startup_error,
            restart_app,
            list_depseudo_responses,
            read_depseudo_response,
            change_password,
            generate_recovery_key,
            reset_password_with_recovery,
        ])
        .run(tauri::generate_context!())
        .expect("Błąd uruchamiania Pseudominizer");
}
