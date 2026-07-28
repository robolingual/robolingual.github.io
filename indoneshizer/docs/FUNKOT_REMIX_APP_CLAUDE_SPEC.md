# FUNKOT REMIX APP — 開発仕様書 / Claude引き継ぎ用

## 0. この文書の目的

この文書は、既存の歌モノ音源をインドネシアのファンコット（Funkot / Funky Kota）へ自動または半自動でリミックスするアプリを開発するための、Claude向け引き継ぎ資料である。

単なる「高速四つ打ち化」ではなく、ファンコット特有の以下の要素を、アプリの処理ロジックとして再現することを目的とする。

- 180 BPM前後の高速四つ打ち
- 「ドッタ・ドッドタ」と聞こえるFunky Beat
- 短いメインキックと補助キックの会話
- 跳ねるMoog / エレキベース風ベースライン
- カウベル、ウッドブロック、タム、コンガ等の大量配置
- スネアロール
- アーメンブレイクやブレイクビーツのフィル
- ボーカルの高速タイムストレッチ、切り刻み、反復
- DJシャウト、カウント、声ネタ
- 8小節単位の展開
- 一時的なハーフタイム、ダウンビート、別ジャンル挿入
- 少し粗く、強引で、ブートレグ的な編集感覚

アプリの最終目的は、ユーザー自身の歌モノを「ファンコットとして成立するリミックス」へ変換すること。

---

# 1. アプリの基本コンセプト

## 仮称

FUNKOT REMIXER

名称は後で変更可能。

## 入力

最低限、以下のいずれかを読み込めること。

1. 完成済みの2mix音源
2. ボーカルステム
3. インストステム
4. 複数ステム
   - Vocal
   - Drums
   - Bass
   - Other / Music

対応候補形式：

- WAV
- MP3
- M4A
- AAC
- 必要であればMP4 / MOVから音声抽出

## 出力

- リミックス済みWAV
- プレビュー再生
- 可能ならステム別書き出し
  - Vocal
  - Funkot Drums
  - Bass
  - Synth
  - FX
- 設定JSON
- プロジェクト再読込

## 基本思想

これは「元曲に適当な四つ打ちを被せるアプリ」ではない。

元曲を解析し、歌、リズム、展開を保ちながら、ファンコットのグルーヴ、パーカッション、ベース、シンセ、フィル、声ネタ、展開へ再構成する。

---

# 2. 最初に作るべきMVP

最初から完全自動化しない。

MVPでは、次の処理に集中する。

1. 音源読み込み
2. 元BPM検出、または手動BPM入力
3. 目標BPMを180前後へ設定
4. ボーカルまたは2mixをタイムストレッチ
5. ファンコット用ドラムを生成
6. ベースラインを生成
7. 8小節単位で展開を構築
8. プレビュー
9. WAV書き出し

MVPでは、コード検出や高度なステム分離が不安定なら、ユーザー手動入力を許可する。

例：

- 元BPM
- Key
- 小節頭
- サビ開始位置
- ボーカル区間
- ドロップ区間

「完全自動に見せるために精度を落とす」より、手動補助ありで音楽的に正しい結果を優先する。

---

# 3. 推奨UI

## メイン画面

上から順に：

1. LOAD AUDIO
2. 波形表示
3. 元BPM
4. 目標BPM
5. Key
6. 小節頭位置
7. REMIX STYLE
8. INTENSITY
9. GENERATE
10. PLAY / STOP
11. EXPORT WAV

## 推奨パラメータ

### TARGET BPM

- 170
- 175
- 180
- 185
- 190
- Custom

初期値は180 BPM。

### FUNKY BEAT

0〜100%

低い場合：
- 四つ打ち中心
- パーカッション少なめ

高い場合：
- 補助キック増加
- カウベル増加
- ウッドブロック増加
- タム、コンガ増加
- フィル頻度増加

### BASS MOTION

0〜100%

低い：
- ルート中心
- 単純

高い：
- 5度、短3度、短7度
- シンコペーション
- オクターブ移動
- ゴーストノート
- スライド

### VOCAL CHOP

0〜100%

低い：
- 元ボーカルを長く保持

高い：
- 音節切断
- 反復
- 16分刻み
- ピッチ変化
- 語尾反復
- 逆再生
- スタッター

### COWBELL

0〜100%

複数音程のカウベルを生成。

### AMEN / BREAK

0〜100%

低い：
- 8小節末のフィルのみ

高い：
- 4小節末
- 8小節末
- ドロップ中
- ダウンビート移行
- 高速チョップ

### DJ VOICE

OFF / LOW / MID / HIGH

音声素材はユーザー提供か、プリセット。

### DOWNBEAT

OFF / HALF-TIME / BREAKBEAT / RANDOM

### ROUGHNESS

0〜100%

低い：
- 現代的で整ったミックス

高い：
- サンプラー感
- 帯域の狭い声
- 強引なカット
- 粗いピッチ変更
- 古いPCM的音色
- 多少の音量差
- ブートレグ感

---

# 4. ファンコットの基本テンポ

基本値：

- BPM 178〜184
- 推奨初期値 180 BPM
- 拍子 4/4
- 8小節を基本単位
- 16小節または32小節で大展開

180 BPM時：

- 4分音符：約333.33ms
- 8分音符：約166.67ms
- 16分音符：約83.33ms
- 32分音符：約41.67ms

すべてのパターン生成はBPMに追従すること。

---

# 5. ドラム生成の中核

## 5.1 基本グリッド

1小節を16ステップで扱う。

```text
STEP: 01 02 03 04 | 05 06 07 08 | 09 10 11 12 | 13 14 15 16
BEAT: 1           | 2           | 3           | 4
```

## 5.2 基本四つ打ち

```text
MAIN KICK:
X . . . | X . . . | X . . . | X . . .
```

## 5.3 スネア / クラップ

```text
SNARE:
. . . . | X . . . | . . . . | X . . .
```

2拍目、4拍目。

## 5.4 ハット

```text
CLOSED HAT:
x . x . | x . x . | x . x . | x . x .
```

または薄い16分刻み。

## 5.5 Funky Beat用補助キック

例：

```text
SHORT KICK:
. . X . | . . X X | . . X . | . . X X
```

別パターン：

```text
SHORT KICK:
. . X X | . X . X | . . X X | . X X .
```

重要：

- 補助キックはメインキックより短い
- 低域を減らす
- 音量を下げる
- 音程を少し高くする
- 強弱を付ける

推奨ベロシティ：

```text
Main Kick = 115〜127
Short Kick strong = 85〜105
Short Kick weak = 55〜80
```

## 5.6 ウッドブロック

```text
WOODBLOCK:
. X . X | . X . . | . X . X | . X . X
```

別パターン：

```text
WOODBLOCK:
. X . . | . . X . | . X . X | . . X X
```

## 5.7 カウベル

```text
COWBELL:
. . X . | . X . X | . . X . | . X X .
```

または：

```text
COWBELL:
. . . X | . . X . | . X . X | . . X X
```

カウベルは最低3音色。

- High
- Mid
- Low

音程例：

- High = +7〜+12 semitone
- Mid = original
- Low = -3〜-7 semitone

## 5.8 コンガ、ボンゴ、タム

```text
CONGA:
. . . X | . X . X | . . . X | . X X .
```

```text
LOW TOM:
. . X . | . . X X | . . X . | . X X .
```

## 5.9 重要なドラム設計原則

- メインキックは短い
- Gabberキックのように長くしない
- 補助キックは低音ではなくリズム発音
- カウベル、ウッド、タムが会話する
- 全パートを同時に鳴らし続けない
- 4小節目、8小節目は変化させる
- 8小節末に必ず何らかのフィルを入れる

---

# 6. キック音作り

## メインキック

目標：

- 短い
- 硬い
- 乾いている
- クリックがある
- 低域の尾が短い

推奨：

- Decay：80〜160ms
- Pitch Envelope：+12〜24 semitoneから急降下
- Pitch Decay：20〜50ms
- Fundamental：50〜70Hz
- Click：2〜5kHz
- Saturation：軽め

音源候補：

- TR-909系
- Eurodance系
- Hard House系
- 古いサンプラー系

## 補助キック

- HPF：60〜100Hz
- Decay：40〜100ms
- Main Kickより高めのPitch
- Main Kickより低いVelocity

---

# 7. スネアロール

ファンコットではスネアロールが重要。

## 1小節ビルド

```text
1拍目：8分
2拍目：16分
3拍目：16分
4拍目：32分
```

## 2小節ビルド

1小節目：
- 16分固定

2小節目：
- 前半16分
- 後半32分
- 最後だけ高速化

ピッチオートメーション：

```text
0 → +3 → +7 semitone
```

ベロシティ：

```text
弱 → 中 → 強
```

追加処理：

- ノイズライザー
- フィルター開放
- リバーブ量増加
- 最後の1/4拍を無音
- ドロップ頭にImpact

---

# 8. ハイハット設計

基本：

- 8分裏
- 16分ゴースト
- オープンハットは控えめ

例：

```text
OPEN HAT:
. . X . | . . X . | . . X . | . . X .
```

高域にカウベル、声、スネア、リードが集中するため、ハットを明るくしすぎない。

---

# 9. アーメンブレイク / ブレイクビーツ

アーメンブレイクは主ドラムではなく、フィル、切り替え、暴走演出として使う。

主な使用位置：

- 4小節目
- 8小節目
- ドロップ直前
- ダウンビート移行
- ドロップ中の1小節だけ
- 最終ドロップ

処理：

- HPF：100〜180Hz
- LPF：8〜12kHz
- 強めのCompression
- Transient強調
- 必要ならMono寄り
- キック低域と競合させない

分割例：

- A = Kick
- B = Snare
- C = Ghost
- D = Ride
- E = Fill

再配置例：

```text
A B C B | A D C B | A B E E | A C B B
```

---

# 10. ベースライン

## 10.1 音色

目標：

- Moog風
- エレキベース風
- FMベース風
- 中低域で音程が聞こえる
- 短い
- 跳ねる
- サブだけではない

シンセ設定例：

- OSC1：Saw
- OSC2：Square -1 octave
- Sub：Sine少量
- Filter：24dB LPF
- Cutoff：250〜900Hz
- Resonance：5〜20%
- Amp Decay：100〜220ms
- Sustain：20〜50%
- Release：30〜80ms
- Filter Env：20〜50%
- Glide：0〜40ms

## 10.2 音程

マイナーキーでは以下を中心に生成。

- Root
- 5th
- Minor 3rd
- Minor 7th
- Octave

A minor例：

- A
- C
- E
- G

## 10.3 リズム例

```text
STEP: 01 02 03 04 | 05 06 07 08 | 09 10 11 12 | 13 14 15 16
NOTE: A  .  A  E  | .  A  .  G  | A  .  C  E  | .  G  E  .
```

音長：

- Gate 30〜65%

ベースは伸ばしすぎない。

## 10.4 キックとの関係

理想：

```text
Kick → Bass → Short Kick → Bass
```

例：

```text
STEP: 01 02 03 04 05 06 07 08
KICK: X  .  .  X  X  .  .  X
BASS: .  X  X  .  .  X  X  .
```

完全交互でなくてよいが、キックとベースの隙間を意識する。

## 10.5 サイドチェイン

- Gain Reduction：2〜5dB
- Attack：0〜5ms
- Release：50〜110ms

180 BPMでは16分が約83msなので、Releaseが長すぎるとベースが消える。

---

# 11. シンセリード

使用候補：

- Supersaw
- Detuned Saw
- Square Lead
- Whistle Lead
- Cheap Brass
- Organ Stab
- Bell
- Pluck
- Trance Arp
- GM系Synth Brass
- Orchestra Hit
- Rave Stab

## Supersaw例

- Voices：7〜16
- Detune：15〜35%
- Stereo Width：50〜80%
- HPF：150〜300Hz
- LPF：8〜14kHz
- Attack：0〜20ms
- Decay：300〜900ms
- Sustain：50〜80%
- Release：100〜400ms

Reverb：

- 0.7〜1.8秒
- Wet 8〜20%
- Pre-delay 15〜35ms

Delay：

- 1/8
- Dotted 1/8
- Feedback 10〜25%

高速BPMなので残響を長くしすぎない。

---

# 12. メロディ生成

複雑なメロディより、1〜2小節の明快なモチーフ。

特徴：

- 高音
- 短い反復
- ピッチベンド
- 休符
- 4小節目だけ変化
- 8小節目に上昇やフィル

A minor例：

```text
E5 E5 G5 A5 | E5 C6 B5 G5
E5 E5 G5 A5 | C6 B5 G5 E5
```

アルペジオ例：

```text
A4 C5 E5 G5 | A5 G5 E5 C5
```

---

# 13. ピッチベンド

用途：

- 笛
- リード
- 声ネタ
- シンセホーン
- ライザー
- ボーカルチョップ

Pitch Bend Range：

- ±2
- ±7
- ±12 semitone

演歌的なこぶし：

```text
開始 -2
30〜80ms後 0
末尾 +2
```

発狂ライザー：

```text
0 → +12 semitone
```

ドロップ前：

```text
0 → -12 semitone
```

---

# 14. コード進行

オリジナル生成時の候補。

## マイナー

```text
Am – F – C – G
Am – G – F – G
Am – C – G – F
```

## 歌謡 / ダンドゥット寄り

```text
Am – G – F – E
Dm – Am – E – Am
```

特に：

```text
Am – G – F – E
```

は演歌、歌謡、ダンドゥット、アラビック感を出しやすい。

コードは長く伸ばさず、スタブにする。

配置例：

- 8分裏
- 2拍目
- 4拍目
- 小節末

---

# 15. ボーカル処理

## 15.1 タイムストレッチ

元BPMから180 BPMへ変換。

例：

- 90 BPM → 180 BPM：倍テン
- 120 BPM → 180 BPM：1.5倍

ただし、歌全体を一括処理すると不自然になりやすい。

推奨：

1. フレーズごとに分割
2. 単語頭を小節へ固定
3. 語尾と空白を縮める
4. 音節内部は必要以上に変形しない
5. サビだけ先に処理

## 15.2 Vocal Chop

例：

```text
あなたが好き
↓
あなた、あなた、あなたが好き
```

```text
好き、好き、好き、好き
```

16分スタッター：

```text
SU SU SU SU
```

ピッチ：

```text
0, 0, +3, +7 semitone
```

## 15.3 生成パターン

### Pattern A：Repeat

1音節を2〜8回反復。

### Pattern B：Machine Gun

16分または32分で反復。

### Pattern C：Pitch Rise

同一音節を反復しながら上昇。

### Pattern D：Reverse Entry

逆再生音から原音へ接続。

### Pattern E：Tail Loop

語尾のみ反復。

### Pattern F：Call and Response

原ボーカル → ピッチ変更コピーで応答。

### Pattern G：Formant Split

同一フレーズを高低2種類のフォルマントで配置。

---

# 16. DJボイス / 声ネタ

候補：

- Ay!
- Hey!
- DJ!
- Are you ready?
- One, two, three, four
- 曲名
- アーティスト名
- 笑い声
- 観客
- 女性シャウト
- 男性シャウト
- ロボ声
- 電話声

配置：

- 8小節頭
- 4小節目
- 8小節目
- ドロップ直前
- ダウンビート直前
- 最終ドロップ

処理：

- HPF 100〜250Hz
- 強めのCompression
- 1/8 or 1/4 Delay
- Short Reverb
- Pitch ±3 / ±5 / ±7 / ±12
- Formant Shift
- Telephone EQ
- Bit Crush
- Distortion

---

# 17. 曲構成

## 17.1 8小節テンプレート

```text
BAR 1
Kick + Short Kick + Snare + Hat

BAR 2
Cowbell追加

BAR 3
Woodblock追加

BAR 4
Tom Fill

BAR 5
Bassline追加

BAR 6
Bass Variation

BAR 7
Voice追加

BAR 8
Snare Roll + 最後を無音
```

次の8小節：

```text
BAR 9
Full Drop + Synth Lead

BAR 10
Lead Repeat

BAR 11
Vocal Chop

BAR 12
Amen Fill

BAR 13
Lead 1 Octave Up

BAR 14
Horn Stab

BAR 15
DJ Count

BAR 16
32分Snare Roll → Breakdown
```

## 17.2 長尺構成例

```text
0:00 DJ Intro
0:20 Beat追加
0:40 Bass追加
1:00 Synth追加
1:20 Vocal提示
2:00 Drop 1
2:40 Break
3:20 Downbeat
4:00 Funkot復帰
5:00 Drop 2
6:00 別ジャンル挿入
7:00 Final Drop
8:00 Outro
```

MVPでは3〜5分でもよい。

---

# 18. ダウンビート

曲中に一度、速度感を変える。

## HALF-TIME

BPMは180のまま。

- Snareを3拍目
- Kickを1拍目中心
- Hatを8分

体感90 BPM。

## BREAKBEAT

130〜150 BPMへ移行。

切り替え方法：

1. Snare Roll
2. 無音
3. DJ Voice
4. 新BPMでDrop

## RANDOM GENRE INSERT

将来機能：

- Hardstyle
- Psytrance
- Dubstep
- Breakcore
- Jungle
- Gabber
- Dangdut
- Enka Break

ただしMVPではHalf-Timeだけでよい。

---

# 19. 8小節ごとの変化ルール

8小節ごとに最低1要素を変更。

候補：

- Cowbell追加
- Woodblock追加
- Bass末尾変更
- Voice追加
- Snare Roll
- Tom Fill
- Amen Fill
- Lead Octave Up
- Vocal Chop
- 1拍Kick抜き
- Reverse Cymbal
- Horn Stab
- Pitch Rise
- 1/4拍無音
- Filter変化

同一8小節を完全コピーし続けない。

---

# 20. Roughness / ブートレグ感

ファンコットは現代EDMのように整いすぎると弱い。

Roughnessパラメータで以下を制御。

## Low

- Clean
- 音量差少なめ
- 滑らかなタイムストレッチ
- 少ないフィル
- 高品質シンセ

## Mid

- サンプラー感
- 一部Bit Crush
- 声ネタが少し前
- 強引な切り替え
- PCM風音色

## High

- 粗いピッチ変更
- 帯域の狭い声
- 音量差
- 過剰なフィル
- 不自然なカット
- 古いサンプル感
- 突然のジャンル変更
- 短い無音
- 予測不能な声ネタ

ただし低域のキックとベースだけは整理する。

---

# 21. ミックス

## Kick

- 50〜80Hz：土台
- 100〜200Hz：濁り調整
- 2〜5kHz：クリック

## Bass

- 30Hz以下カット
- 60〜120Hz：低域
- 200〜800Hz：音程とエレキ感

## Cowbell / Wood

- HPF 200〜500Hz
- 2〜5kHzの刺さりを調整

## Lead

- HPF 150〜300Hz
- 300〜600Hzの濁りを整理
- 2.5〜5kHzの痛さを調整

## Vocal

- HPF 80〜150Hz
- 200〜500Hzの濁り
- 2〜5kHzの明瞭度
- 8〜12kHzの空気感

---

# 22. バス設計

推奨Bus：

- MAIN KICK
- SHORT KICK
- PERCUSSION
- BREAKS
- BASS
- SYNTH
- VOCAL
- DJ VOICE
- FX
- MASTER

## Percussion Bus

- Ratio：2:1〜4:1
- Attack：10〜30ms
- Release：30〜100ms
- Gain Reduction：1〜4dB
- 軽いSaturation

## Music Bus

KickからSidechain。

## Vocal Bus

歌とDJ Voiceは分ける。

DJ Voiceは歌より前でもよい。

---

# 23. マスター

目標：

- キックとベースの分離
- パーカッションの発音
- 高域が白くならない
- リミッターでFunky Beatを潰さない

推奨：

- Ceiling：-1.0dBTP
- Limiter Gain Reduction：常時1〜4dB程度
- 過度な常時6dB以上の圧縮は避ける

---

# 24. 必要サンプル

## Drums

- Main Kick x5
- Short Kick x5
- Low Tom x5
- High Tom x5
- Snare x8
- Clap x5
- Rolling Snare x5
- Closed Hat x5
- Open Hat x5
- Crash x5
- Ride x3

## Percussion

- Cowbell High / Mid / Low
- Woodblock High / Mid / Low
- Rimshot
- Clave
- Agogo
- Conga
- Bongo
- Kendang系
- Metal Percussion
- Tambourine
- Shaker
- Whistle

## Breaks

- Amen
- Think
- Apache
- Funky Drummer系
- 独自ブレイク

## Voices

- Ay
- Hey
- DJ
- Are You Ready
- 1,2,3,4
- Female Shout
- Male Shout
- Laugh
- Crowd
- Artist Name
- Song Name

## Synth / FX

- Moog Bass
- Electric Bass
- Supersaw
- Square Lead
- Whistle Lead
- Rave Stab
- Orchestra Hit
- Synth Brass
- Bell
- Pluck
- GM Strings
- Choir
- Noise Riser
- Downlifter
- Reverse Cymbal
- Impact
- Laser
- Siren

---

# 25. アルゴリズム設計

## 25.1 Pattern Generator

ドラム、ベース、シンセ、声ネタを別Generatorにする。

### DrumGenerator

入力：

- BPM
- Intensity
- Funky Beat
- Cowbell
- Amen
- Variation Seed

出力：

- 16 step pattern x bars
- Sample ID
- Velocity
- Pan
- Pitch
- Timing Offset
- FX Send

### BassGenerator

入力：

- Key
- Chord
- Bass Motion
- Bar Position
- Intensity

出力：

- Note
- Start
- Duration
- Velocity
- Glide
- Accent

### VocalChopGenerator

入力：

- Audio Buffer
- Slice Positions
- Vocal Chop Amount
- Key
- BPM

出力：

- Slice ID
- Start
- Duration
- Repeat Count
- Pitch
- Reverse
- Formant
- Pan
- FX

### ArrangementGenerator

入力：

- Song Length
- Section Markers
- Intensity Curve
- Downbeat Mode

出力：

- Intro
- Build
- Drop
- Break
- Downbeat
- Final Drop
- Outro

---

# 26. ランダム生成の制御

完全ランダムではなく、ルールベース＋確率。

例：

```text
4小節目のFill発生率：60%
8小節目のFill発生率：95%
Amen発生率：Intensity依存
Cowbell追加率：Funky Beat依存
Voice発生率：DJ Voice依存
Vocal Chop発生率：Vocal Chop依存
```

同じSeedなら同じ結果を再生成できること。

---

# 27. 音楽的な失敗条件

以下の場合はファンコットとして失敗。

1. ただの高速EDM
2. 四つ打ち＋Supersawだけ
3. Gabberキックが長すぎる
4. Cowbellが1音だけ
5. BassがSubのみ
6. 全部4小節コピペ
7. Drumが均一Velocity
8. Vocalを一括タイムストレッチしただけ
9. Fillがない
10. 8小節展開がない
11. 高域が全部明るく耳に痛い
12. 音を綺麗にしすぎてブートレグ感がない
13. 元曲の歌が埋もれている
14. キックとベースが常に完全重複
15. パーカッションが装飾扱い

---

# 28. 成功条件

以下を満たせば成功。

1. キックを消してもFunky Beatのノリが残る
2. Cowbell、Woodblock、Short Kickが会話する
3. Bassが跳ねる
4. 8小節ごとに変化がある
5. Vocalが180 BPMでも破綻しない
6. 元曲のサビが認識できる
7. Drumだけでも踊れる
8. Dropで密度が上がる
9. Breakで一度空間ができる
10. Final Dropで最も派手になる
11. Roughnessがある
12. それでも低域は整理されている

---

# 29. 推奨開発段階

## Phase 1

- 1音源読み込み
- BPM手動入力
- 180 BPMへStretch
- Funkot Drum生成
- Bass生成
- Preview
- WAV Export

## Phase 2

- BPM自動検出
- Key自動検出
- Vocal Chop
- Cowbell / Percussion Variation
- Amen Fill
- Arrangement自動生成

## Phase 3

- Stem対応
- Vocal / Instrumental分離
- Downbeat
- DJ Voice
- Roughness
- Seed保存
- Project保存

## Phase 4

- 複数Remix Pattern生成
- 6〜10 Variation同時生成
- Section単位再生成
- Stem Export
- MIDI Export
- REAPER連携
- iPhone Safari対応
- MP4 / MOV読込

---

# 30. 技術方針

未確定部分。

Claudeは実装前に、以下から現実的な構成を選ぶこと。

## Browser App案

- Web Audio API
- AudioWorklet
- OfflineAudioContext
- Tone.js
- Essentia.js
- ffmpeg.wasm
- Meyda
- IndexedDB
- Web Workers

長所：

- GitHub Pagesで公開可能
- インストール不要
- iPhone対応可能

短所：

- 長い音源
- Stem Separation
- 高品質Stretch
- WAV Export
- Safari制約
- メモリ制限

## Desktop App案

- Electron
- Tauri
- Python backend
- Rubber Band
- librosa
- essentia
- ffmpeg
- soundfile

長所：

- 高品質処理
- 長尺音源
- ファイルアクセス
- Stem処理

短所：

- 配布が必要
- 開発量が増える

## MVP推奨

まずはBrowser Appで音楽ロジックを検証。

ただし高品質タイムストレッチが難しい場合は、Desktop版へ切り替える。

---

# 31. Claudeへの重要指示

1. いきなり巨大な完成版を書かない
2. まず音楽処理の設計を分割する
3. MVPの最小構成を提示する
4. 音楽理論を一般論で誤魔化さない
5. Funky Beatを具体的な16 step patternとして扱う
6. BPM、ノート、サンプル、ベロシティ、タイミングをデータ化する
7. UIとAudio Engineを分離する
8. 同一Seedで再生成可能にする
9. iPhone Safariの制約を軽視しない
10. 音声処理をMain Threadに集中させない
11. 長尺音源でメモリ破綻しない構成にする
12. 最初は自動Key検出より手動Key入力を優先してよい
13. 元曲の歌を残すことを最優先する
14. ファンコットらしさはキックではなくパーカッション全体で作る
15. 未確定事項を勝手に決めず、仮定として明記する

---

# 32. 最初にClaudeへ依頼する内容

以下の順番で進める。

## STEP 1

この仕様を読み、実装可能なMVP構成を設計する。

回答内容：

- 技術構成
- Audio Engine構成
- データ構造
- UI構成
- 主要クラス / モジュール
- 処理フロー
- 制約
- 最初に作る機能
- 後回しにする機能

## STEP 2

16 step Funky Beat Generatorを単体実装する。

最低限：

- Main Kick
- Short Kick
- Snare
- Hat
- Cowbell
- Woodblock
- Tom
- Fill

## STEP 3

ブラウザ上で180 BPM再生。

## STEP 4

音源読み込みと同期。

## STEP 5

Bass Generator。

## STEP 6

8小節Arrangement。

## STEP 7

WAV Export。

---

# 33. Claudeへ渡す最初のプロンプト

以下をClaudeへそのまま送ってよい。

---

この文書は、既存の歌モノ音源をインドネシアのファンコットへリミックスするアプリの開発仕様書です。

まず全文を読み、いきなりコードを書かず、実装可能なMVPの設計を提示してください。

重視する点は以下です。

- 単なる高速四つ打ちではなく、ファンコット固有のFunky Beatを再現する
- ドラムは16 step patternで管理する
- Main Kick、Short Kick、Cowbell、Woodblock、Tom、Snare Rollを別レイヤーで設計する
- 元曲の歌を残す
- 180 BPM前後へタイムストレッチする
- 8小節単位でArrangementを作る
- BassはMoog / Electric Bass風で短く跳ねさせる
- Vocal Chopは後段階で追加する
- 同一Seedで同じRemixを再生成できるようにする
- Browser AppとDesktop Appのどちらが現実的か比較する
- iPhone Safari対応の難所を明記する
- 不明点は勝手に補完せず、仮定として明記する

最初の返答では、以下を出してください。

1. MVPの定義
2. 推奨技術構成
3. モジュール構成
4. データ構造
5. Audio処理フロー
6. UI構成
7. 実装順
8. 想定される技術的問題
9. 最初に作る最小プロトタイプ
10. この仕様の中で矛盾または不足している部分

コードはまだ書かないでください。

---

# 34. 最終的なアプリ像

最終的には、ユーザーが歌モノを読み込み、以下の操作だけで複数のファンコットRemixを生成できること。

1. 音源を読み込む
2. BPMとKeyを確認
3. Funky Beat量を決める
4. Cowbell量を決める
5. Bass Motionを決める
6. Vocal Chop量を決める
7. Amen量を決める
8. Roughnessを決める
9. Generate
10. 複数Variationを聴き比べる
11. 気に入ったSectionだけ再生成
12. WAVまたはStemで書き出す

理想は「ファンコットを知らない人でもボタン一つでそれらしい曲になる」ことではない。

理想は、ファンコットの構造を理解した音楽家が、素材を素早くファンコット化し、そこから手作業で完成させられること。

このアプリは完成品を自動生成するだけではなく、人間の編集を加えるための制作支援機である。
