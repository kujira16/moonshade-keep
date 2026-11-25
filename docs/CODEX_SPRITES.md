# Codex への指示書：gpt-image で 16×16 ドット絵を生成してゲームに組み込む

このリポジトリは、ゲームボーイ風アクションゲーム「MOONSHADE KEEP（月影の城）」です。
今のドット絵は `js/sprites.js` の中に文字で描いた仮の絵です。これを **OpenAI の画像生成（gpt-image）で作った絵に置き換える**のが今回の作業です。

- 主人公：`docs/reference/knight.png` の騎士の女の子
- 敵・ボス・アイテム・背景タイル：同じ世界観で新しく作る

画像生成から、縮小・4色化・ゲームへの組み込みまでを**スクリプトで自動化**してください。

---

## 0. 前提として知っておくこと

1. **gpt-image は 16×16 を直接出力できない。** 出力サイズは 1024×1024 / 1536×1024 / 1024×1536 のどれか。
   そこで「1024px で、ドットが大きくはっきりしたピクセルアートを生成」→「スクリプトで 16×16 に縮小」→「4色に減色」の3段階にする。
2. **画面はゲームボーイ風の4階調。** 最終的な PNG は次の4色と透明だけにする。

   | 番号 | 色 | 用途の目安 |
   |---|---|---|
   | 1 | `#9bbc0f` | 一番明るい（髪のハイライト、鎧の光） |
   | 2 | `#8bac0f` | 明るい（鎧、肌） |
   | 3 | `#306230` | 暗い（服、影） |
   | 4 | `#0f380f` | 一番暗い（輪郭線、目） |

   ゲーム側は読み込んだ PNG を明るさで自動的に4階調にするが、生成側で先にこの4色に揃えておくと結果が安定する。
3. **差し替えの仕組みはもうある。** `assets/<名前>.png` を置き、`assets/overrides.json` の `sprites` に `"名前": 1フレームの横幅` を書けば、起動時に読み込まれる（`js/sprites.js` の `loadOverrides` / `quantizeImage`）。フレームは**横一列**に並べる。
4. **背景はステージの色が暗い**（一番暗い色 4 の夜空、城の奥壁は色 3）。キャラと敵は明るい色 1・2 を主体にして、暗い背景の上で目立つようにする。
5. **API キーは環境変数 `OPENAI_API_KEY` から読む。** コードにもリポジトリにも絶対に書かない。

---

## 1. 作るもの

### 1-1. スクリプト

| ファイル | 内容 |
|---|---|
| `tools/sprite_prompts.json` | 各スプライトの名前・サイズ・フレーム数・プロンプト・参照画像 |
| `tools/gen_sprites.py` | 生成 → 縮小 → 4色化 → シート化 → 保存 → `overrides.json` 更新 |
| `assets/raw/` | gpt-image の生の出力（1024px）を保存する。`.gitignore` に入れる |
| `assets/preview/` | 確認用に 8 倍に拡大した画像と、全スプライトの一覧シート |

`gen_sprites.py` は次のように使えるようにする。

```bash
pip install openai pillow
export OPENAI_API_KEY=...
python3 tools/gen_sprites.py --only player_idle,player_walk   # 一部だけ
python3 tools/gen_sprites.py --all                            # 全部
python3 tools/gen_sprites.py --all --reprocess                # API を呼ばず raw から縮小・減色だけやり直す
```

- モデル名は `--model` オプションと環境変数 `IMAGE_MODEL` で変えられるようにする（既定は `gpt-image-1`。利用できる新しい gpt-image があればそれを指定）。
- 生成には `background="transparent"`、`output_format="png"` を指定する。
- 同じキャラの別フレームや、主人公の見た目を揃えたいときは **画像編集 API（images.edit）に参照画像を渡す**。
  - 主人公の最初のフレーム（`player_idle`）は `docs/reference/knight.png` を参照にする。
  - 歩き・ジャンプ・攻撃のフレームは、できあがった `player_idle` の raw 画像を参照にする。
- 失敗したら 2 回までリトライし、それでも駄目ならそのスプライトを飛ばしてログに残す。

### 1-2. 縮小と減色の手順（ここが一番大事）

1. raw 画像のアルファで、透明でない部分の外接矩形を切り出す。
2. 縦横比を保ったまま、正方形（または指定サイズの比率）の透明キャンバスの中央下に置く。キャラは足元を一番下の行に揃える。
3. **まず BOX（面積平均）で目標サイズ（16×16 など）に縮小する。** NEAREST だけだと線が欠けやすいので使わない。
4. アルファが 128 未満なら透明、それ以外は不透明にする（半透明は使わない）。
5. 明るさ（`0.299R + 0.587G + 0.114B`）を4段階に分けて、上の4色に置き換える。
   しきい値はスプライトごとに少し変えられるように、`sprite_prompts.json` に `"levels": [192,128,64]` のように書けるようにする。
6. **一番外側の輪郭は色 4 で縁取る。** 透明に隣接する不透明ピクセルのうち、明るい色 1・2 のものだけを 4 にする。小さいので、これがないと背景に埋もれる。
7. 複数フレームは横一列のシートにして `assets/<名前>.png` に保存する。
8. `assets/preview/<名前>.png`（8倍拡大、暗い背景つき）と、全部並べた `assets/preview/_sheet.png` を作る。

### 1-3. ゲームへの組み込み

- `assets/overrides.json` の `sprites` を自動で更新する（`"名前": 1フレームの横幅`）。
- **`sw.js` の `FILES` に新しい PNG を追加し、`VERSION` を上げる**（オフラインで遊ぶためのキャッシュに入れるため）。
- `README.md` の「AI生成の絵に差し替える方法」に、このスクリプトの使い方を追記する。

---

## 2. 生成するスプライト一覧

サイズはピクセル数（横×縦）。フレームは横に並べる。

### 主人公（参照：`docs/reference/knight.png`）

| 名前 | 1フレーム | フレーム数 | 内容 |
|---|---|---|---|
| `player_idle` | 16×16 | 1 | 立ち。右向き |
| `player_walk` | 16×16 | 4 | 歩き（右足前、そろえる、左足前、そろえる） |
| `player_jump` | 16×16 | 1 | ジャンプ（ひざを曲げる） |
| `player_attack` | 16×16 | 1 | 地上で剣を前に突き出す |
| `player_attack_air` | 16×16 | 1 | 空中で剣を前に突き出す |

ゲーム側の都合で守ること：
- **右向き**で描く（左向きはゲームが反転する）。
- 体の中心は横 4〜11 列目、足は一番下の行（15 行目）。当たり判定は 8×14。
- 攻撃フレームは、**剣を持った手が右端（15 列目）の高さ 8 行目あたり**に来るようにする。攻撃のエフェクトはこの位置からゲームが描く。

**16×16 に落とすときの特徴の残し方**（参照画像の要素を、少ないドットで分かるように優先順位をつける）
1. 金色の髪とアホ毛（頭の上 1〜2 ドットの跳ね）→ 色 1
2. 銀の鎧（肩当て・胸当て・すね当て）→ 色 2、影は色 3
3. 青い服（鎖かたびらの部分）→ 色 3
4. 青い目 → 色 4 の 1 ドット（左右 1 つずつ。右向きなら 1 つでもよい）
5. 剣（青い鞘と金のつば）→ 立ちポーズでは腰に、攻撃ポーズでは前へ
6. 頭身はちびキャラ（頭が全体の半分弱）のまま

### 敵・ボス・アイテム（同じ世界観で新規デザイン）

| 名前 | 1フレーム | フレーム数 | 内容 |
|---|---|---|---|
| `bat` | 16×16 | 2 | コウモリ。羽を上げた絵と下げた絵 |
| `bat_hang` | 16×16 | 1 | 天井にぶら下がって羽をたたんだコウモリ |
| `skeleton` | 16×16 | 2 | 歩くガイコツ兵（右向き）。2コマ歩き |
| `ghost` | 16×16 | 2 | ゆらめく幽霊。すそが揺れる2コマ |
| `boss_skull` | 16×16 | 1 | ボス「翼骸」の頭。大きな角のある頭蓋骨、正面 |
| `boss_wing` | 16×16 | 2 | ボスの右の翼（コウモリの翼）。上げ・下げ。左はゲームが反転 |
| `candle` | 8×16 | 2 | 壁の燭台。炎が揺れる2コマ |
| `heart` | 8×8 | 1 | 回復のハート |
| `gem` | 8×8 | 1 | 得点の宝石 |
| `bone` | 8×8 | 2 | ガイコツが投げる骨（回転2コマ） |
| `fireball` | 8×8 | 2 | ボスの火の玉 |
| `orb` | 8×8 | 2 | ボスを倒すと出る光の玉 |

敵は主人公より怖く、でもかわいすぎない「ちびゴシック」の雰囲気で揃える。

### 背景タイル（16×16 で作る）

| 名前 | サイズ | 内容 |
|---|---|---|
| `t_brick` | 16×16 | 城の石壁（乗れる床・壁）。上下左右につなげても継ぎ目が目立たない |
| `t_brick_top` | 16×16 | 石壁の一番上の段。上の辺に明るい縁（雪が少し積もっていてもよい） |
| `t_ledge` | 16×16 | 乗れる石の足場。上 4 行に描き、下は透明 |
| `t_spikes` | 16×16 | 床のトゲ。下 12 行くらいに描く |
| `t_back` | 16×16 | 城の奥の壁（暗い石）。色 3 と 4 だけで、手前より目立たない |
| `t_pillar` | 16×16 | 奥の柱。縦につなげても継ぎ目が目立たない |
| `t_window` | 16×24 | 奥の壁のアーチ窓。月明かりで明るい |

**今のゲームのタイルは 8×8 なので、16×16 タイルを使えるようにゲーム側を少し直す必要がある。**
`js/game.js` の `drawWorld` で、タイル画像が 16×16 のときは、タイル座標 `(tx, ty)` に対して画像の `((tx & 1) * 8, (ty & 1) * 8)` から 8×8 を切り出して描くようにする（4 マスで 1 枚の模様になる）。8×8 の画像のときは今まで通り。
当たり判定とステージの地図（`js/level.js`）は 8 ピクセル単位のまま変えない。

---

## 3. プロンプトの書き方

全スプライト共通の前半（英語のほうが安定する）：

```
Pixel art game sprite, Game Boy style, strictly 4 shades of green
(#9bbc0f, #8bac0f, #306230, #0f380f), very low resolution look:
the whole subject is drawn on a {W}x{H} pixel grid with each pixel
as a large crisp square, no anti-aliasing, no gradients, no dithering,
thick dark outline, side view facing right, centered,
transparent background, single subject only, no text, no frame.
```

主人公（`player_idle`、images.edit で参照画像つき）の後半：

```
Convert this character into a 16x16 pixel chibi sprite, full body,
standing, facing right. Keep: blonde hair with one ahoge strand,
silver plate armor with round shoulder guards, blue tunic under
the armor, brown belt, sword in a blue scabbard at the hip.
Big head, small body (chibi proportions).
```

歩き・ジャンプ・攻撃は、`player_idle` の raw を参照にして、ポーズだけを指示する。例：

```
Same character, same size and colors. Walking pose, frame {n} of 4:
{right leg forward | legs together | left leg forward | legs together}.
```

```
Same character, same size and colors. Attack pose: sword thrust
straight forward to the right at chest height, arm fully extended.
```

敵の例（`skeleton`）：

```
A small skeleton soldier walking, facing right, holding nothing,
chibi gothic style, frame {n} of 2.
```

背景の例（`t_brick`）：

```
Seamless tileable castle stone wall texture, front view, fills the
entire square edge to edge, no transparency, no outline.
```

---

## 4. 完成の条件（チェックリスト）

- [ ] `assets/<名前>.png` がすべて**指定どおりのピクセル数**（16×16 ×フレーム数 など）
- [ ] 使っている色が**上の4色と透明だけ**（スクリプトで検査して、違反があればエラーにする）
- [ ] `assets/overrides.json` が更新され、`python3 -m http.server` で起動するとゲーム内の絵が変わっている
- [ ] 主人公が参照画像の騎士だと分かる（金髪、アホ毛、銀の鎧、青い服、剣）
- [ ] 主人公の足が床にぴったり立ち、当たり判定と見た目がずれていない
- [ ] 背景タイルを並べて継ぎ目が目立たない。16×16 タイルの描画に対応している
- [ ] パレット切り替え（P キー）で、新しい絵もグレーや紫に変わる
- [ ] `sw.js` の `FILES` と `VERSION` を更新した
- [ ] API キーをどこにもコミットしていない。`assets/raw/` は `.gitignore` に入っている
- [ ] `assets/preview/_sheet.png` を見て、つぶれて分からないスプライトがあれば、プロンプトかしきい値を直して作り直した

## 5. やらないこと

- 既存のゲーム（キャッスルヴァニアなど）の名前・キャラクター・絵に似せない。
- 当たり判定・ステージの地図・ゲームの動きは変えない（16×16 タイル描画への対応と、必要なら描画位置の微調整だけ）。
- 縮小後の画像を手で描き足すのは、どうしても必要な数ドットだけにする。その場合は何を直したか README に書く。
