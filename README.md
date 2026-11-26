# MOONSHADE KEEP（月影の城）— ステージ1 試作

緑4階調のゴシック城アクション。描画は320×288で、移動と当たり判定は160×144の座標で計算します。キャラ・敵・城・曲はすべてオリジナルです。
ビルド不要の素の HTML + JavaScript で、PWA としてPC・スマホにインストールできます。

## 遊び方
| 操作 | キーボード | スマホ | ゲームパッド |
|---|---|---|---|
| 移動 | ← → / A D | 十字キー | スティック・十字 |
| ジャンプ（長押しで高く） | Z / Space / K | A | A(0) |
| ムチ攻撃 | X / J | B | B / X |
| スタート・ポーズ | Enter / Esc | START | Start |
| 色パレット切替（緑/グレー/紫） | P | SELECT | Select |
| 音 ON/OFF | M | – | – |

ステージ構成：城の中庭 → 第1ホール → 第2ホール（トゲと段差）→ 回廊（チェックポイント）→ ボス「翼骸」。
敵：コウモリ（近づくと飛ぶ）、ガイコツ（骨を投げる）、ゴースト（壁をすり抜けて追ってくる）。燭台を壊すとハート（回復）か宝石（+500点）。

## 起動・インストール
- **PCで試す**：このフォルダで `python3 -m http.server 8000` → Chrome/Edge で http://localhost:8000 を開く → アドレスバーの「インストール」アイコン（または右上の「インストール」ボタン）。
- **スマホに入れる**：HTTPS で公開する必要があります（GitHub Pages / Netlify / Cloudflare Pages などにフォルダごと置くだけ）。
  - Android（Chrome）：開いて「インストール」or メニュー →「ホーム画面に追加」
  - iPhone（Safari）：共有ボタン →「ホーム画面に追加」
- 一度開けばオフラインでも遊べます（sw.js がキャッシュ。更新時は sw.js の VERSION を上げる）。

## ファイル構成
```
index.html            画面・タッチボタン・PWA登録
manifest.webmanifest  アプリ名・アイコン
sw.js                 オフラインキャッシュ
js/game.js            ゲーム本体（物理・敵AI・ボス・描画・入力）
js/sprites.js         ドット絵データ（文字で描いたスプライト）とパレット
js/level.js           ステージの地図（1文字=8pxタイル）
js/audio.js           効果音とBGM（WebAudioの矩形波）
tools/make_level.py   level.js を生成するスクリプト
tools/make_icons.py   アイコン生成
assets/overrides.json 画像差し替えの設定
```

## AI生成の絵に差し替える方法
同梱の PNG 24 種は起動時に `assets/overrides.json` から読み込まれます。差し替えがない絵は `js/sprites.js` のドット絵を使います。

同梱素材は組み込みの画像生成機能で制作しました。主人公は騎士の参照画像から立ち絵を作り、採用した立ち絵を参照して各ポーズを展開しています。[新旧比較](assets/preview/compare.png)では、旧素材を16倍、新素材を8倍にしてゲーム上の同じ大きさで表示しています。

再生成する場合は `OPENAI_API_KEY` を環境変数に設定し、リポジトリのルートで実行します。

```sh
python -m pip install openai pillow numpy
python tools/gen_sprites.py --only player_idle,player_walk
python tools/gen_sprites.py --all
python tools/gen_sprites.py --reprocess
python tools/gen_sprites.py --pick player_walk=2
```

- 主人公の立ち絵は `docs/reference/knight.png` を参照します。ほかのポーズを生成する場合は、先に `player_idle` を生成してください。
- API での生成は高品質設定で 1 種につき候補を 4 枚作ります。歩きは横一列でまとめて描く方法と、立ち絵から1コマずつ作る方法を比較します。最高点が基準を下回る場合はプロンプトを調整し、さらに4候補まで生成します。
- `--reprocess` は全素材を読み取り直します。`assets/raw/hires_32/` の原画がなければ、候補一覧 PNG に保存したフルカラーのサンプルを使います。`--only` で対象を絞り、`--pick 名前=番号` で採用候補を選び直せます。どちらも API に接続しません。
- 既定モデルは `gpt-image-1` です。環境変数 `IMAGE_MODEL` または `--model` で、透過 PNG に対応するモデルに変更できます。
- 各素材をフルカラーで完成サイズの縦横2倍に生成します。例えば主人公は64×64を読み取り、HSVで部位を分け、2×2ごとに優先度の高い部位を残して32×32にします。敵・アイテム・背景も素材の色を分類したうえで縮めます。主人公は配置図との一致と細部の読めやすさを採点し、歩きの上14行を全コマで立ち絵に揃えます。
- 採用候補を `assets/source/` に保存し、`tools/polish_sprites.py` を自動実行してゲーム用の `assets/` を更新します。その後 `overrides.json` と `sw.js` のキャッシュ設定を更新します。仕上がりは [8倍拡大の一覧](assets/preview/_sheet.png) と [候補・採点一覧](assets/preview/candidates/) で確認できます。

手動で差し替える場合は `assets/<スプライト名>.png` を置き、`assets/overrides.json` の `sprites` に高解像度なら `{"w":32,"scale":2}` のように画像上の1フレーム幅と倍率を書きます。従来の数値指定は倍率1として使えます。城の壁は32×32の絵から、マップ座標に対応する画像上の16×16を切り出します。アーチ窓は32×48の全体を背景に表示します。

## ステージを作り替える
`tools/make_level.py` を編集して `python3 tools/make_level.py` を実行すると `js/level.js` が更新されます（直接 level.js を書き換えてもOK）。
記号：`#`壁 `=`乗れる足場 `^`トゲ `b`城の奥壁 `I`柱 `W`窓 `P`開始位置 `C`燭台 `B`コウモリ `S`ガイコツ `G`ゴースト `K`ボス `R`チェックポイント

### 生成した絵を見やすくする後処理
`python3 tools/polish_sprites.py` だけを実行すると、手元にある `assets/source/` をゲーム用の配色と縁取りで仕上げ直せます。生成スクリプトから実行した場合、この処理も自動で行われます。
