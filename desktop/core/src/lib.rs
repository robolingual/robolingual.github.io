//! 音声ファイル／動画ファイルから音を取り出す。
//!
//! Web版は動画を実時間で再生しながら録っているため、5分の動画に5分かかる。
//! デスクトップではここでデコードするので待ち時間が消える。
//!
//! symphonia が扱えない形式もあるので、失敗は素直にエラーで返す。
//! 呼び出し側(JS)はその場合、今までの再生方式へ戻す。

use std::path::Path;

use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::{DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::errors::Error as SymphoniaError;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

/// 取り出した音。JS側で AudioBuffer に載せ替える。
///
/// Debug は手で書いてある。derive にすると波形を丸ごと出力してしまい、
/// テストが失敗したときのログが数百万個の数字で埋まるため。
pub struct Decoded {
    /// モノラルに畳んだ波形。
    pub samples: Vec<f32>,
    /// 元のサンプリングレート。合わせ込みは JS 側の OfflineAudioContext で行う。
    pub sample_rate: u32,
}

impl std::fmt::Debug for Decoded {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Decoded")
            .field("frames", &self.samples.len())
            .field("sample_rate", &self.sample_rate)
            .finish()
    }
}

/// ファイルを読んでモノラルの波形にする。
///
/// 複数チャンネルは平均してモノラルにする。アプリが解析に使うのはモノラル波形なので、
/// ここで畳んでおけば受け渡す量も減る。
pub fn decode_file(path: &Path) -> Result<Decoded, String> {
    let file = std::fs::File::open(path).map_err(|e| format!("開けません: {e}"))?;
    let stream = MediaSourceStream::new(Box::new(file), Default::default());

    // 拡張子は当てにしすぎず、判別は symphonia に任せる。
    // 拡張子は候補を絞る手がかりとしてだけ渡す。
    let mut hint = Hint::new();
    if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
        hint.with_extension(ext);
    }

    let probed = symphonia::default::get_probe()
        .format(&hint, stream, &FormatOptions::default(), &MetadataOptions::default())
        .map_err(|e| format!("形式を判別できません: {e}"))?;
    let mut format = probed.format;

    // 動画ファイルには映像トラックも入っている。音声トラックだけを拾う。
    let track = format
        .tracks()
        .iter()
        .find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
        .ok_or_else(|| "音声トラックがありません".to_string())?;
    let track_id = track.id;

    let mut decoder = symphonia::default::get_codecs()
        .make(&track.codec_params, &DecoderOptions::default())
        .map_err(|e| format!("このコーデックは扱えません: {e}"))?;

    let mut samples: Vec<f32> = Vec::new();
    let mut sample_rate: u32 = 0;
    let mut buf: Option<SampleBuffer<f32>> = None;

    loop {
        let packet = match format.next_packet() {
            Ok(p) => p,
            // 末尾まで読み切るとここに来る。
            Err(SymphoniaError::IoError(ref e))
                if e.kind() == std::io::ErrorKind::UnexpectedEof =>
            {
                break
            }
            Err(SymphoniaError::ResetRequired) => break,
            Err(e) => return Err(format!("読み取りに失敗しました: {e}")),
        };
        if packet.track_id() != track_id {
            continue;
        }

        match decoder.decode(&packet) {
            Ok(audio) => {
                let spec = *audio.spec();
                if sample_rate == 0 {
                    sample_rate = spec.rate;
                }
                if buf.is_none() {
                    buf = Some(SampleBuffer::<f32>::new(audio.capacity() as u64, spec));
                }
                let b = buf.as_mut().unwrap();
                b.copy_interleaved_ref(audio);

                let channels = spec.channels.count().max(1);
                if channels == 1 {
                    samples.extend_from_slice(b.samples());
                } else {
                    let inv = 1.0 / channels as f32;
                    for frame in b.samples().chunks_exact(channels) {
                        samples.push(frame.iter().sum::<f32>() * inv);
                    }
                }
            }
            // 壊れたパケットは飛ばして続ける。全部落とすより、取り出せる分を返す。
            Err(SymphoniaError::DecodeError(_)) => continue,
            Err(SymphoniaError::IoError(ref e))
                if e.kind() == std::io::ErrorKind::UnexpectedEof =>
            {
                break
            }
            Err(e) => return Err(format!("デコードに失敗しました: {e}")),
        }
    }

    if samples.is_empty() || sample_rate == 0 {
        return Err("音を取り出せませんでした".into());
    }
    Ok(Decoded { samples, sample_rate })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn presets_dir() -> std::path::PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../presets")
            .canonicalize()
            .expect("presets が見つからない")
    }

    #[test]
    fn プリセットのwavを読める() {
        for n in 1..=3 {
            let p = presets_dir().join(format!("preset{n}.wav"));
            let d = decode_file(&p).unwrap_or_else(|e| panic!("preset{n}: {e}"));
            assert!(d.sample_rate >= 8000, "preset{n}: レートが不正 {}", d.sample_rate);
            let secs = d.samples.len() as f32 / d.sample_rate as f32;
            assert!(secs > 1.0, "preset{n}: 短すぎる {secs}s");
            let peak = d.samples.iter().fold(0.0f32, |a, s| a.max(s.abs()));
            assert!(peak > 0.01, "preset{n}: 無音に見える peak={peak}");
            println!("preset{n}: {secs:.2}s {}Hz peak={peak:.3}", d.sample_rate);
        }
    }

    #[test]
    fn 波形が範囲に収まっている() {
        let d = decode_file(&presets_dir().join("preset1.wav")).unwrap();
        let bad = d.samples.iter().filter(|s| !s.is_finite() || s.abs() > 1.001).count();
        assert_eq!(bad, 0, "範囲外の値が {bad} 個");
    }

    #[test]
    fn 存在しないファイルはエラーになる() {
        let e = decode_file(Path::new("/nonexistent/nope.wav")).unwrap_err();
        assert!(e.contains("開けません"), "想定外のエラー: {e}");
    }

    #[test]
    fn 音声でないファイルはエラーになる() {
        let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml");
        assert!(decode_file(&p).is_err(), "テキストを音として読んでしまった");
    }
}
