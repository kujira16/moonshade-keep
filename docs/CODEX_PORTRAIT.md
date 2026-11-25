# Codex への指示書（第2弾）：主人公の 128×128 ポートレートと 16×16 ドット絵

前回の指示書 `docs/CODEX_SPRITES.md` の続きです。共通のルール（4色パレット、API キーの扱い、縮小・減色の手順、`overrides.json`、`sw.js`）は前回と同じなので、先にそちらを読んでください。

今回の作業は3つです。

1. **主人公の 128×128 ポートレート**を作り、タイトル画面とステージクリア画面に表示する（新規）
2. そのポートレートを参照にして、**主人公の 16×16 ドット絵（ゲーム中のキャラ）を作り直す**
3. 敵・ボス・アイテム・背景の **16×16 ドット絵を、ポートレートと絵柄を揃えて作り直す**

参照画像：`docs/reference/knight.png`（金髪の騎士の女の子）

---

## 0. 128×128 をどこで使うか

ゲーム画面は 160×144 ピクセルしかないので、128×128 のキャラはゲーム中には使えない（画面のほとんどを埋めてしまう）。
**128×128 は「ポートレート（顔と上半身の大きな絵）」として、タイトル画面とクリア画面に表示する。** ゲーム中の主人公は 16×16 のまま。

ゲームボーイの作品で、タイトルや会話シーンにだけ大きな絵を出すのと同じ使い方です。

---

## 1. 128×128 ポートレート

### 仕様

| 項目 | 内容 |
|---|---|
| ファイル | `assets/player_portrait.png` |
| サイズ | 128×128、1フレーム |
| 色 | 前回と同じ4色（`#9bbc0f` `#8bac0f` `#306230` `#0f380f`）と透明だけ |
| 構図 | 頭から腰くらいまでの上半身、ほぼ正面（少し右向き）。顔が上半分に来るように |
| 背景 | 透明（ゲームの夜空の上に重ねる） |
| 輪郭 | 一番暗い色 `#0f380f` で 1px の輪郭線 |

### 参照画像から残すもの（優先順）
1. 金髪、頭の上のアホ毛、横の編み込み → 一番明るい色と明るい色
2. 大きな青い目（目のハイライトを 1〜2px 残す）
3. 銀の鎧：丸い肩当て、胸当ての模様 → 明るい色、影は暗い色
4. 青い服と鎖かたびら → 暗い色
5. 茶色のベルトと、腰の剣（青い鞘、金のつば）
6. ちびキャラの頭身とやさしい表情

### 生成から減色までの手順
1. images.edit に `docs/reference/knight.png` を渡し、1024×1024 で生成する。`background="transparent"`。
2. プロンプト（英語）：

   ```
   Game Boy style pixel art portrait of this character, bust shot from
   head to waist, facing slightly right, gentle smile. Drawn on a 128x128
   pixel grid with large crisp square pixels, strictly 4 shades of green
   (#9bbc0f, #8bac0f, #306230, #0f380f), dark 1-pixel outline, flat
   shading with at most simple checkerboard dithering, no anti-aliasing,
   no gradients, transparent background, no text, no frame.
   Keep: blonde hair with one ahoge strand and a side braid, big blue
   eyes, silver plate armor with round shoulder guards, blue tunic and
   chainmail, brown belt, sword with blue scabbard and gold crossguard.
   ```

3. 縮小と減色は前回の手順と同じだが、次の点だけ変える。
   - 縮小は **BOX で 128×128**。キャラの外接矩形を切り出し、**下端を合わせて**中央に置く（腰で切れてよい）。
   - 128px あれば細部が残るので、**影の境目にだけ市松模様のディザ（2色交互）を使ってよい**。それ以外のグラデーションは禁止。
   - 目と口は顔の印象を決めるので、減色後に崩れていたら、その数ドットだけ手で直してよい（直した箇所を README に書く）。
4. `assets/overrides.json` の `sprites` に `"player_portrait": 128` を追加する。
5. **ポートレートには `tools/polish_sprites.py` をかけない**（あの処理は 16×16 用）。ただし、同じ方法で `assets/source/player_portrait.png` に生成直後の絵を残しておく。

### ゲームへの組み込み（`js/game.js`）

- **タイトル画面**（`drawTitle`）
  - 夜空の背景はそのまま。ポートレートを **x=16, y=16** に描く（画面の下端に揃う）。
  - タイトル文字 `MOONSHADE` `KEEP` はポートレートより手前に、今と同じ影付きで描く。顔に重ならないよう、**文字は画面上部（y=4〜20）に移す**。
  - `PRESS ENTER` / `TAP START` と操作説明は、画面下部に暗い色の帯（高さ 20px 程度）を敷いてその上に描く。
  - ポートレートは、ゆっくり（60フレームに1px程度）上下に 1px 揺らしてよい。
- **ステージクリア画面**
  - 今の「STAGE CLEAR!」の枠の後ろ（画面の右下寄り）にポートレートを描き、枠の文字が読めるようにする。
- **`assets/player_portrait.png` がないときも今まで通り動くこと。** `Sprites.baked.player_portrait` があるときだけ描く。
- `P` キーでパレットを切り替えたとき、ポートレートの色も変わること（`Sprites` の仕組みに乗せれば自動でそうなる）。

---

## 2. 主人公の 16×16 を作り直す

- 参照画像は **`docs/reference/knight.png` ではなく、できあがった 128×128 ポートレート**（`assets/source/player_portrait.png`）を使う。小さい絵どうしのほうが、16×16 に落としたときの見た目が揃いやすい。
- 作るものと守ること（サイズ、フレーム数、右向き、足の位置、攻撃フレームの手の位置）は前回の指示書の「主人公」の表と同じ。
- 16×16 でも分かるように、**髪の色（一番明るい色）とアホ毛、鎧の肩当て**を一番優先して残す。顔は目 1 ドットでよい。

## 3. 敵・ボス・アイテム・背景の 16×16 を作り直す

- 名前・サイズ・コマ数は前回の指示書の表と同じ。
- **ポートレートを「絵柄の参照」として images.edit に一緒に渡し**、線の太さ・陰影の付け方を主人公と揃える。
  プロンプトに `Match the pixel art style, outline and shading of the reference character.` を足す。
- 背景タイルは前回と同じく 16×16 で、ゲーム側の 16×16 タイル描画（`drawTile`）はすでにあるのでそのまま使う。

## 4. 生成後の後処理

16×16 の絵（主人公・敵・ボス・アイテム・背景）を作り直したら、最後に次を実行する。

```bash
python3 tools/polish_sprites.py
```

これで、奥の壁を暗く、床や壁を明るく、キャラを明るくして縁取りする調整がかかる。
**作り直した絵は `assets/source/<名前>.png` に置く**こと（このスクリプトは `assets/source/` を読んで `assets/` に書き出す）。`player_portrait` はこのスクリプトの対象外。

## 5. 完成の条件（チェックリスト）

- [ ] `assets/player_portrait.png` が 128×128、4色と透明だけ
- [ ] ポートレートを見て、参照画像の騎士だと分かる（金髪、アホ毛、青い目、銀の鎧、剣）
- [ ] タイトル画面で、タイトル文字・ポートレート・「PRESS ENTER」が重ならずに読める
- [ ] ステージクリア画面にポートレートが出て、スコアの文字も読める
- [ ] ポートレートの PNG を消しても、ゲームがエラーなく動く
- [ ] 主人公・敵・背景の 16×16 が作り直され、`tools/polish_sprites.py` を実行済み
- [ ] ゲーム中、主人公と敵が背景に埋もれず見える
- [ ] `sw.js` の `FILES` に `assets/player_portrait.png` を追加し、`VERSION` を上げた
- [ ] スタートからボスを倒してクリアまで、エラーなく遊べる
- [ ] API キーをコミットしていない

## 6. やらないこと

- ゲーム画面の解像度（160×144）や、ゲーム中の主人公のサイズ（16×16）を変えない。
- 当たり判定・ステージの地図・ゲームの動きは変えない。
- 既存のゲーム（キャッスルヴァニアなど）の名前・キャラクター・絵に似せない。
