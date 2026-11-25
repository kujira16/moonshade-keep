"""AI生成スプライトを画面で見やすくする後処理。

assets/source/<名前>.png（生成直後の絵）を読み、assets/<名前>.png に書き出す。
初回実行時に assets/<名前>.png を assets/source/ へ退避する。何度実行しても結果は同じ。
gen_sprites.py で作り直したら、その後にこれを実行する。

- 奥の壁・柱：暗くして手前の床や壁と区別をつける
- 乗れる壁・足場：明るくする
- キャラ・敵・アイテム：1段明るくし、外側に1pxの縁取りを付けて太く見せる
"""
import argparse
import os
import shutil
from PIL import Image

PAL = [(0x9b, 0xbc, 0x0f), (0x8b, 0xac, 0x0f), (0x30, 0x62, 0x30), (0x0f, 0x38, 0x0f)]
IDX = {c: i + 1 for i, c in enumerate(PAL)}
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
SRC = os.path.join(ASSETS, "source")

# 色番号の置き換え表（1=一番明るい … 4=一番暗い）
BACK = {1: 3, 2: 3, 3: 4, 4: 3}      # 奥の壁：地を一番暗く、目地をうっすら
PILLAR = {1: 3, 2: 3, 3: 3, 4: 4}
SOLID = {1: 1, 2: 1, 3: 2, 4: 3}     # 乗れる壁・足場：1段明るく
ACTOR = {1: 1, 2: 2, 3: 2, 4: 4}     # 髪と鎧の明るさを区別し、中間色だけ明るく
OUTLINE = 3                          # キャラの外側に付ける縁の色

RULES = {
    "t_back": (BACK, False), "t_pillar": (PILLAR, False), "t_window": (None, False),
    "t_brick": (SOLID, False), "t_brick_top": (SOLID, False), "t_ledge": (SOLID, False), "t_spikes": (SOLID, False),
}
ACTORS = ["player_idle", "player_walk", "player_jump", "player_attack", "player_attack_air",
          "bat", "bat_hang", "skeleton", "ghost", "boss_skull", "boss_wing",
          "candle", "heart", "gem", "bone", "fireball", "orb"]
FRAME_W = {"candle": 8, "heart": 8, "gem": 8, "bone": 8, "fireball": 8, "orb": 8}


def load(name):
    os.makedirs(SRC, exist_ok=True)
    src = os.path.join(SRC, name + ".png")
    if not os.path.exists(src):
        shutil.copy(os.path.join(ASSETS, name + ".png"), src)
    im = Image.open(src).convert("RGBA")
    px = [[0] * im.width for _ in range(im.height)]
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = im.getpixel((x, y))
            if a >= 128:
                px[y][x] = IDX.get((r, g, b)) or (1 if (0.299*r+0.587*g+0.114*b) > 192 else 2 if (0.299*r+0.587*g+0.114*b) > 128 else 3 if (0.299*r+0.587*g+0.114*b) > 64 else 4)
    return px


def save(name, px):
    h, w = len(px), len(px[0])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            if px[y][x]:
                im.putpixel((x, y), PAL[px[y][x] - 1] + (255,))
    im.save(os.path.join(ASSETS, name + ".png"))


def remap(px, table):
    return [[table[v] if v else 0 for v in row] for row in px]


def outline(px, fw):
    """フレームごとに、不透明ピクセルの上下左右の透明マスへ縁を付ける（フレームをはみ出さない）"""
    h, w = len(px), len(px[0])
    out = [row[:] for row in px]
    for y in range(h):
        for x in range(w):
            if px[y][x]:
                continue
            f0 = (x // fw) * fw
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if f0 <= nx < f0 + fw and 0 <= ny < h and px[ny][nx]:
                    out[y][x] = OUTLINE
                    break
    return out


def polished_actor(name):
    px = load(name)
    if not name.startswith("player_"):
        px = remap(px, ACTOR)
    return outline(px, FRAME_W.get(name, 16))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", choices=[*RULES, *ACTORS])
    args = parser.parse_args()
    selected = set(args.only or [*RULES, *ACTORS])
    for name, (table, _) in RULES.items():
        if name in selected:
            px = load(name)
            save(name, remap(px, table) if table else px)
    for name in ACTORS:
        if name not in selected:
            continue
        px = polished_actor(name)
        if name == "player_walk":
            idle = polished_actor("player_idle")
            for y in range(7):
                px[y] = idle[y] * (len(px[y]) // len(idle[y]))
        save(name, px)


if __name__ == "__main__":
    main()
