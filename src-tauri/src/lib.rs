use std::process::Command;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager, WindowEvent,
};

// ── Health-check constants ────────────────────────────────────────────────────
/// URL polled until the FastAPI sidecar signals it is ready.
const HEALTH_URL: &str = "http://127.0.0.1:8080/health";

/// Interval between successive health-check attempts.
const POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Maximum time to wait for the backend before showing the window anyway.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(15);

// ── Shared timer state (Rust-side mirror of the JS timer) ────────────────────
// The JS side calls the `update_tray_timer` Tauri command every tick to push
// its state here. The tray menu reads it when rebuilding the label.

#[derive(Clone)]
struct TimerState {
    label: String, // e.g. "Focus: 22:14 remaining" or "Idle"
}

// ── Tauri command — called from JS Timer component every second ───────────────

/// Update the tray's timer label from JS.
///
/// The Timer component calls this command each tick so the tray always shows
/// live remaining time without Rust needing to own the countdown logic.
#[tauri::command]
fn update_tray_timer(
    app: AppHandle,
    state: tauri::State<Arc<Mutex<TimerState>>>,
    label: String,
) {
    // Write the new label into shared state
    {
        let mut ts = state.lock().unwrap();
        ts.label = label.clone();
    }

    // Rebuild the tray menu so the label item reflects the update.
    // We ignore errors here — tray menu rebuild is best-effort.
    let _ = rebuild_tray_menu(&app, &label);
}

// ── Tray menu builder ─────────────────────────────────────────────────────────

/// Construct (or reconstruct) the tray context menu.
///
/// Called once at startup and again every time the timer label changes.
/// Returns the new menu so the caller can attach it to the tray icon.
fn rebuild_tray_menu(app: &AppHandle, timer_label: &str) -> tauri::Result<Menu<tauri::Wry>> {
    let menu = Menu::new(app)?;

    // Item 0 — Live timer status (read-only display label)
    let status_text = if timer_label.is_empty() {
        "Nudge — Idle".to_string()
    } else {
        timer_label.to_string()
    };
    let status = MenuItem::with_id(app, "status", &status_text, false, None::<&str>)?;

    // Item 1 — Separator-equivalent: disabled dash item
    let sep = MenuItem::with_id(app, "sep", "─────────────", false, None::<&str>)?;

    // Item 2 — Open / show window
    let open = MenuItem::with_id(app, "open", "Open Nudge", true, None::<&str>)?;

    // Item 3 — Emit "start-focus" event that the JS Timer listens for
    let start_focus = MenuItem::with_id(app, "start_focus", "▶  Start Focus Session", true, None::<&str>)?;

    // Item 4 — Emit "pause-timer" event
    let pause = MenuItem::with_id(app, "pause", "⏸  Pause Timer", true, None::<&str>)?;

    // Item 5 — Hard quit
    let quit = MenuItem::with_id(app, "quit", "Quit Nudge", true, None::<&str>)?;

    menu.append(&status)?;
    menu.append(&sep)?;
    menu.append(&open)?;
    menu.append(&start_focus)?;
    menu.append(&pause)?;
    menu.append(&quit)?;

    Ok(menu)
}

// ── Helper: show + focus the main window ─────────────────────────────────────

fn show_main_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

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

    // Step 2 — Shared timer state accessible to both the Tauri command and the
    //          tray menu builder. Arc<Mutex<>> lets us share across threads safely.
    let timer_state = Arc::new(Mutex::new(TimerState {
        label: String::new(),
    }));

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        // Register the JS→Rust command
        .invoke_handler(tauri::generate_handler![update_tray_timer])
        // Make TimerState available via tauri::State<>
        .manage(timer_state)
        .setup(|app| {
            let app_handle = app.handle().clone();

            // ── Step 3: Health-check thread ──────────────────────────────────
            // Poll /health every 500 ms; show window once backend is ready.
            {
                let handle = app_handle.clone();
                thread::spawn(move || {
                    let client = reqwest::blocking::Client::builder()
                        .timeout(Duration::from_secs(2))
                        .build()
                        .expect("failed to build HTTP client");

                    let deadline = Instant::now() + STARTUP_TIMEOUT;
                    let mut backend_ready = false;

                    while Instant::now() < deadline {
                        match client.get(HEALTH_URL).send() {
                            Ok(resp) if resp.status().is_success() => {
                                println!("[Nudge] Backend is ready — showing window.");
                                backend_ready = true;
                                break;
                            }
                            _ => thread::sleep(POLL_INTERVAL),
                        }
                    }

                    if !backend_ready {
                        println!(
                            "[Nudge] WARNING: backend did not respond within {}s. \
                             Showing window anyway.",
                            STARTUP_TIMEOUT.as_secs()
                        );
                    }

                    show_main_window(&handle);
                });
            }

            // ── Step 4: System tray setup ────────────────────────────────────
            // Build the initial menu (timer label = empty → "Idle").
            let initial_menu = rebuild_tray_menu(app.handle(), "")
                .expect("failed to build tray menu");

            // Load the 32×32 icon from the bundled icons directory.
            // Image::from_path resolves relative to the resource dir at runtime.
            let icon = app.default_window_icon()
                .expect("no default window icon — check tauri.conf.json")
                .clone();

            // Build the tray icon. On macOS this appears in the menu bar.
            let _tray = TrayIconBuilder::new()
                .icon(icon)
                .menu(&initial_menu)
                .show_menu_on_left_click(false) // left-click → show window
                .tooltip("Nudge — Productivity Timer")
                .on_tray_icon_event({
                    // Left-click on tray icon → restore + focus main window.
                    let handle = app_handle.clone();
                    move |_tray, event| {
                        if let TrayIconEvent::Click {
                            button: MouseButton::Left,
                            button_state: MouseButtonState::Up,
                            ..
                        } = event
                        {
                            show_main_window(&handle);
                        }
                    }
                })
                .on_menu_event({
                    // Handle the four tray menu actions.
                    let handle = app_handle.clone();
                    move |app, event| match event.id.as_ref() {
                        "open" => {
                            // Restore the main window.
                            show_main_window(&handle);
                        }
                        "start_focus" => {
                            // Emit an event to the JS frontend — Timer listens for this.
                            show_main_window(&handle);
                            let _ = app.emit("tray-start-focus", ());
                        }
                        "pause" => {
                            // Emit pause event to JS Timer.
                            let _ = app.emit("tray-pause-timer", ());
                        }
                        "quit" => {
                            // Hard exit — this is intentional quit from tray.
                            println!("[Nudge] Quit requested from tray menu.");
                            app.exit(0);
                        }
                        _ => {}
                    }
                })
                .build(app)?;

            // ── Step 5: Window close → hide (not quit) ───────────────────────
            // Intercept the CloseRequested event on "main" so that clicking ✕
            // hides the window instead of terminating the process. The app
            // continues to run in the tray until the user chooses "Quit Nudge".
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    if let WindowEvent::CloseRequested { api, .. } = event {
                        // Prevent the default close/quit behaviour.
                        api.prevent_close();
                        // Hide the window — app lives on in tray.
                        if let Some(w) = app_handle.get_webview_window("main") {
                            let _ = w.hide();
                            println!("[Nudge] Window hidden — app running in tray.");
                        }
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}