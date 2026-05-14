use std::process::Command;
use std::thread;
use std::time::{Duration, Instant};
use tauri::Manager;

// ── Health-check constants ────────────────────────────────────────────────────
/// URL polled until the FastAPI sidecar signals it is ready.
const HEALTH_URL: &str = "http://127.0.0.1:8080/health";

/// Interval between successive health-check attempts.
const POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Maximum time to wait for the backend before showing the window anyway.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(15);

// ── Entry point ───────────────────────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Step 1 — Spawn the FastAPI/uvicorn sidecar in a separate OS process.
    // The process is detached; Tauri does NOT own its lifecycle.
    Command::new("/Users/devasishmishra/Developer/TechGenDM_Codes/Hackathons/Anvil_SST_2026/Nudge/venv/bin/python")
        .current_dir("..")
        .args([
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
        ])
        .spawn()
        .expect("failed to start backend sidecar");

    // Step 2 — Build Tauri with the setup hook that drives the health-check
    // flow. The main window starts hidden (see tauri.conf.json → visible:false)
    // and is revealed only after the backend is confirmed ready.
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Step 3 — Poll /health off the main thread so the event loop
            // remains responsive during the startup wait.
            thread::spawn(move || {
                let client = reqwest::blocking::Client::builder()
                    .timeout(Duration::from_secs(2))
                    .build()
                    .expect("failed to build HTTP client");

                let deadline = Instant::now() + STARTUP_TIMEOUT;
                let mut backend_ready = false;

                // Retry loop: keep polling until HTTP 200 or timeout.
                while Instant::now() < deadline {
                    match client.get(HEALTH_URL).send() {
                        Ok(resp) if resp.status().is_success() => {
                            println!("[Nudge] Backend is ready — showing window.");
                            backend_ready = true;
                            break;
                        }
                        _ => {
                            // Backend not ready yet; wait before next attempt.
                            thread::sleep(POLL_INTERVAL);
                        }
                    }
                }

                // Step 4 — Timeout safety: show the window regardless.
                if !backend_ready {
                    println!(
                        "[Nudge] WARNING: backend did not respond within {}s. \
                         Showing window anyway.",
                        STARTUP_TIMEOUT.as_secs()
                    );
                }

                // Step 5 — Reveal the main window (label defined in tauri.conf.json).
                if let Some(window) = app_handle.get_webview_window("main") {
                    window.show().unwrap_or_else(|e| {
                        eprintln!("[Nudge] Failed to show window: {e}");
                    });
                } else {
                    eprintln!("[Nudge] ERROR: could not find 'main' window handle.");
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}