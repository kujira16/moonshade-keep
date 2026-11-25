# MOONSHADE KEEP（月影の城）— ステージ1 試作

ゲームボーイ風（160×144・緑4階調）のゴシック城アクション。キャラ・敵・城・曲はすべてオリジナルです。
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
今のドット絵は `js/sprites.js` に文字（`.`=透明, `1`〜`4`=明→暗）で描いてあります。画像生成AIの絵に差し替えるには：

1. 画像生成AIに、例えば次のように頼む  
   「16x16 pixel art sprite sheet, 4 frames in a row, side view, gothic vampire hunter with wide-brim hat and scarf, game boy style, 4 shades of green, transparent background」
2. 出来た画像を**ドット数ちょうど**に縮小（例：4フレーム × 16px = 64×16px）。縮小は「ニアレストネイバー」で。背景は透明に。
3. `assets/<スプライト名>.png` として保存（例：`assets/player_walk.png`）
4. `assets/overrides.json` に1フレームの幅を書く：
   ```json
   { "sprites": { "player_walk": 16, "skeleton": 16, "boss_skull": 16 } }
   ```
5. 再読み込み。色は明るさで自動的に4階調へ変換されるので、フルカラーの絵でもゲームボーイ風になります。

差し替えられる名前：`player_idle` `player_walk`(4コマ) `player_jump` `player_attack` `player_attack_air` `bat`(2) `bat_hang` `skeleton`(2) `ghost`(2) `candle`(2) `heart` `gem` `bone`(2) `fireball`(2) `boss_skull` `boss_wing`(2) `orb`(2) `t_brick` `t_brick_top` `t_ledge` `t_spikes` `t_back` `t_pillar`（以上8×8タイル）`t_window`(16×24)。
サイズを変えると当たり判定とずれるので、最初は同じサイズで作るのがおすすめです。

## ステージを作り替える
`tools/make_level.py` を編集して `python3 tools/make_level.py` を実行すると `js/level.js` が更新されます（直接 level.js を書き換えてもOK）。
記号：`#`壁 `=`乗れる足場 `^`トゲ `b`城の奥壁 `I`柱 `W`窓 `P`開始位置 `C`燭台 `B`コウモリ `S`ガイコツ `G`ゴースト `K`ボス `R`チェックポイント
