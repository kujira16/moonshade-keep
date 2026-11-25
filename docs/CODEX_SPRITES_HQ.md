# Codex への指示書（第2弾）：16×16 のまま、ドット絵の精度を上げる

前回の指示書 `docs/CODEX_SPRITES.md` で作った仕組み（`tools/gen_sprites.py` と `tools/sprite_prompts.json`）を改良して、**同じ 16×16 のまま、もっと上手なドット絵**を gpt-image で作り直してください。
共通のルール（4色パレット、API キーの扱い、`overrides.json`、`sw.js`）は前回と同じです。

参照画像：`docs/reference/knight.png`（主人公の騎士の女の子）

> `docs/CODEX_PORTRAIT.md`（128×128 ポートレート）は取り消しになったので、そちらの作業はしないでください。

---

## 0. 今の絵の問題点（これを直すのが目的）

今の `assets/source/` の絵を 8 倍に拡大して見ると、次の問題がある。

1. **線が細く、かすれている。** 1024px の絵を面積平均（BOX）でいきなり 16×16 に縮めているので、細い線が中間色に溶けて、1px の途切れた線や、ぽつんと浮いた点になっている。
2. **暗い色ばかりで、形が分からない。** 主人公の体の大半が暗い色（`#306230`）で、夜の背景に埋もれる。
3. **コマごとに顔や体が変わる。** 歩きの4コマを別々に生成しているので、頭の形や髪の位置が毎コマ違い、動かすとチラチラする。
4. **主人公の特徴が残っていない。** 金髪・アホ毛・銀の鎧・剣が、16×16 になると判別できない。

---

## 1. 改良の方針

### 1-1. 「ドット 1 個 = 大きな正方形 1 個」で描かせ、ブロック単位で読み取る

縮小で線が溶けるのを防ぐため、gpt-image に**最初から 16×16 のマス目に沿った絵**を描かせ、縮小ではなく**マスごとの色の読み取り**で 16×16 にする。

- プロンプトで「1024×1024 の画像を 16×16 のマスに区切り、**1 マス = 64×64px を 1 色で塗る**」と指示する（下の「プロンプト」参照）。
- 読み取りは次の手順にする（`downsample` を置き換える）。
  1. 画像全体を 16×16 のマスに区切る（1 マス 64px）。生成画像の外周に余白があってマスがずれている場合に備え、**マス目の位置を自動で探す**：縦横それぞれ、色が急に変わる位置（エッジ）を集計し、間隔 48〜80px の範囲で最もよく合う「間隔とずれ」を選ぶ。合わなければ 64px・ずれ 0 を使う。
  2. 各マスの**中央 50% の範囲**だけを見て、ピクセルを4色＋透明のどれに近いかで分類し、**一番多い色（最頻値）**をそのマスの色にする。平均は使わない。
  3. アルファが 128 未満のピクセルが半分以上なら、そのマスは透明。
- 色の分類は、明るさのしきい値ではなく、**4色それぞれとの色の距離**（RGB のユークリッド距離）が一番近いものにする。元の絵の金髪（黄色）が一番明るい色、鎧の銀が明るい色、青い服が暗い色に落ちるよう、分類の前に**明るさとコントラストを自動で整える**（ヒストグラムの 5% 点と 95% 点を 0〜255 に引き伸ばす）。

### 1-2. 1 枚の画像にまとめて描かせ、コマをそろえる

- 複数コマあるもの（`player_walk` 4コマ、`bat` 2コマなど）は、**全コマを 1 枚の画像に横並びで描かせる**。
  例：歩き4コマなら 1536×1024 の画像に「64×16 のマス（16×16 のコマが4つ横並び）」を描かせる。1 マス = 24px になるので、読み取りのマス目探しは 18〜30px の範囲で行う。
- 主人公は、まず `player_idle`（立ち）を作り、**それを参照画像として** 残りのポーズ（歩き・ジャンプ・攻撃）を作る。
- 読み取り後、主人公の歩き4コマは**頭の部分（上から 7 行）を立ちの絵と同じにそろえる**（足の動きに合わせて 1px 上下させるのはよい）。これでコマごとに顔が変わるチラつきがなくなる。

### 1-3. 候補を複数作って、自動で採点して選ぶ

1 回の生成では当たり外れが大きいので、**1 スプライトにつき 4 枚生成し、採点して一番良いものを使う**。

採点の項目（それぞれ 0〜1 にして合計）：

| 項目 | 内容 |
|---|---|
| マス目の合い方 | 各マスの中が何色ちがうか。1 色に近いほど高い（ちゃんとドット絵として描けている） |
| 浮いた点の少なさ | 上下左右どこにも同じ色がない 1px の点が少ないほど高い |
| 明るさのバランス | キャラ・敵：明るい2色（1と2）が不透明部分の 40% 以上だと高い。背景の奥の壁：暗い2色が 80% 以上だと高い |
| 大きさ | キャラ・敵：不透明部分が横 8〜14px・縦 12〜16px に収まると高い |
| 参照との似かた（主人公のみ） | 金髪の位置（頭の上部 5 行に一番明るい色が 8px 以上）、鎧（胴体に明るい色）、剣（攻撃コマで右端に細長い形） |

- 4 枚の候補と点数を `assets/preview/candidates/<名前>.png` に並べて保存し、人が見て選び直せるように `--pick <名前>=<番号>` オプションを付ける。
- 4 枚とも合計点が低い（基準は自分で決めてよい）ときは、プロンプトを少し変えてもう 4 枚まで作り直す。

### 1-4. 読み取ったあとの仕上げ（自動）

1. **浮いた点の除去**：上下左右に同じ色がない 1px の点は、周りで一番多い色に置き換える（目の 1 ドットなど、`sprite_prompts.json` で `"keep": [[x,y], ...]` と指定した位置は残す）。
2. **線の太さ**：腕や足など、幅が 1px で途切れている線は、隣の 1px を同じ色で埋めて 2px にする（はみ出しは不可）。
3. **輪郭**：外側の輪郭は一番暗い色（`#0f380f`）にそろえる。ただし `tools/polish_sprites.py` があとで外側にもう 1px 縁を足すので、**絵の外周 1px は透明のまま空けておく**（足元の一番下の行は除く）。

---

## 2. 16×16 でのデザインの決まりごと（プロンプトにも反映する）

主人公（右向き、16×16、足は一番下の行、体の中心は横 4〜11 列目）：

| 部分 | 行（上から） | 色 | 決まりごと |
|---|---|---|---|
| アホ毛 | 0〜1 | 一番明るい | 頭のてっぺんから 1〜2 ドット跳ねる。これが一番の目印 |
| 金髪 | 1〜6 | 一番明るい＋明るい | 横幅 7〜8px。後ろ（左）に少し長く |
| 顔・目 | 4〜6 | 明るい | 目は一番暗い色の 1 ドット（右寄り） |
| 鎧（肩・胸） | 7〜10 | 明るい＋一番明るい | 丸い肩当てを 2〜3px で表す |
| 服・ベルト | 10〜11 | 暗い | ベルトは一番暗い 1 行 |
| 脚・すね当て | 12〜15 | 明るい | 2px 以上の太さ |
| 剣 | 立ち：腰の左右どちらか / 攻撃：8 行目あたりで右端まで | 明るい | 攻撃コマは剣先が 15 列目に届く |

敵・ボス：
- どれも**明るい2色を主体**にして、暗い背景の上で形が分かるようにする。
- 目は一番暗い色の 1〜2 ドット。ガイコツの目だけは「暗い穴」なので 2×1 でもよい。
- ボスの頭（`boss_skull`）は正面向きで左右対称。読み取り後に**左右対称にそろえる**処理を入れてよい。

背景タイル：
- 奥の壁 `t_back` と柱 `t_pillar` は暗い2色だけ。乗れる壁 `t_brick` `t_brick_top` と足場 `t_ledge` は明るい色を主体に。明暗の差で「乗れる・乗れない」が分かることが最優先。
- タイルは上下左右につなげて継ぎ目が出ないこと（読み取り後、左右の端の列・上下の端の行が、つないだときに自然か確認する）。

---

## 3. プロンプト

共通の前半（英語）：

```
A tiny pixel art game sprite, Game Boy style, using only these 4 colors:
#9bbc0f (lightest), #8bac0f (light), #306230 (dark), #0f380f (darkest).
The image is a strict {COLS}x{ROWS} pixel grid: every grid cell is one
solid square of a single color, perfectly aligned, all cells the same
size, filling the whole image. No anti-aliasing, no gradients, no
dithering, no blur, no texture inside cells. Transparent background
outside the subject. Clear readable silhouette, mostly the two light
colors on the subject, darkest color for the outline and eyes.
No text, no border, no grid lines drawn.
```

主人公 `player_idle`（images.edit、参照に `docs/reference/knight.png`）：

```
{共通}
Subject: this exact character as a 16x16 chibi sprite, full body,
standing, side view facing right. Must keep: one ahoge strand sticking
up from the top of the head, blonde hair (lightest color), silver
armor with round shoulder guards (light color), blue tunic (dark color),
darkest-color belt, sword at the hip. Big head, short body.
```

主人公の他のポーズ（images.edit、参照に `player_idle` の採用画像）：

```
{共通}
Subject: the same character as the reference, identical head, hair and
colors. Grid is {COLS}x16 = {N} frames of 16x16 side by side.
Frames: {例: walk cycle — right leg forward, legs together, left leg
forward, legs together}.
```

敵の例（`skeleton`、2コマ、参照に `player_idle` の採用画像を「絵柄の参照」として渡す）：

```
{共通}
Subject: a small skeleton soldier walking, facing right, chibi gothic
style. Grid is 32x16 = 2 frames of 16x16 side by side: left leg
forward, right leg forward. Match the outline and shading style of the
reference character, but this is a different character.
```

背景の例（`t_brick`、参照なし）：

```
{共通（Transparent background の文は外す）}
Subject: seamless tileable castle stone wall, front view, 16x16 grid,
fills every cell edge to edge, mostly light colors, darkest color for
the mortar lines between stones.
```

- 生成は `quality="high"` を指定する。
- モデルは前回同様、`--model` と環境変数 `IMAGE_MODEL` で変えられるようにする。

---

## 4. 処理の流れ（ファイルの置き場所に注意）

`tools/polish_sprites.py`（見やすくする最後の調整）は **`assets/source/<名前>.png` を読んで `assets/<名前>.png` に書き出す**作りになっている。
今の `gen_sprites.py` は `assets/<名前>.png` に直接書いているので、このままだと作り直した絵に調整がかからない。次の流れに直すこと。

```
gpt-image 生成（候補4枚） → assets/raw/<名前>/候補.png
  → マス目読み取り・採点・仕上げ → assets/source/<名前>.png
  → python3 tools/polish_sprites.py → assets/<名前>.png（ゲームが読む）
```

- `gen_sprites.py` の最後で `polish_sprites.py` を自動で呼ぶ。
- `--reprocess`（API を呼ばず raw から作り直す）も、この流れで動くようにする。
- `assets/raw/` は今まで通り `.gitignore` に入れる。

---

## 5. 完成の条件（チェックリスト）

- [ ] 全スプライトが前回と同じサイズ・コマ数で、4色と透明だけ
- [ ] `assets/preview/compare.png`：**今の絵（作業前の `assets/source/`）と新しい絵を 8 倍で上下に並べた比較画像**を作り、新しいほうが明らかに見やすい
- [ ] 主人公の 16×16 で、アホ毛・金髪・銀の鎧・剣が見て分かる
- [ ] 主人公の歩き4コマで、頭が毎コマ同じ（チラつかない）
- [ ] 1px の浮いた点がない（目など指定したもの以外）
- [ ] ゲーム中、暗い背景の上で主人公と敵の形がはっきり分かる。床・壁と奥の壁の区別がつく
- [ ] `assets/preview/candidates/` に候補と点数が残っていて、`--pick` で選び直せる
- [ ] `gen_sprites.py` → `polish_sprites.py` の流れで `assets/` が更新される
- [ ] `sw.js` の `VERSION` を上げた
- [ ] スタートからボスを倒してクリアまで、エラーなく遊べる
- [ ] API キーをコミットしていない

## 6. やらないこと

- 16×16 のサイズ、当たり判定、ステージの地図、ゲームの動きは変えない。
- 生成後の絵を手で大きく描き直さない（目の位置など数ドットの修正だけ。直したら README に書く）。
- 既存のゲーム（キャッスルヴァニアなど）の名前・キャラクター・絵に似せない。
