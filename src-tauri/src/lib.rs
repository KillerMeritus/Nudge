use std::process::Command;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {

    Command::new("/Users/devasishmishra/Developer/TechGenDM_Codes/Hackathons/Anvil_SST_2026/Nudge/venv/bin/python")
        .current_dir("..")
        .args([
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080"
        ])
        .spawn()
        .expect("failed to start backend");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}