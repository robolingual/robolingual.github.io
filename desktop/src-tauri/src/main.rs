// Windows でコンソール窓を出さない。デバッグビルドでは出す。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;

use tauri::ipc::Response;

/// 音声・動画を読んで、モノラルの波形を返す。
///
/// 戻り値は JSON ではなく生のバイト列にしてある。
/// 波形は数百万サンプルになることがあり、JSON の数値配列にすると
/// 文字列化と再パースだけで数秒かかってしまうため。
///
/// 並びは次の通り。JS 側はこの順で読む。
///   0..4   サンプリングレート (u32, リトルエンディアン)
///   4..    波形 (f32 リトルエンディアンの連続)
#[tauri::command]
fn decode_audio(path: String) -> Result<Response, String> {
    let decoded = robolingual_core::decode_file(&PathBuf::from(path))?;

    let mut out = Vec::with_capacity(4 + decoded.samples.len() * 4);
    out.extend_from_slice(&decoded.sample_rate.to_le_bytes());
    for s in &decoded.samples {
        out.extend_from_slice(&s.to_le_bytes());
    }
    Ok(Response::new(out))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![decode_audio])
        .run(tauri::generate_context!())
        .expect("アプリの起動に失敗しました");
}
