"""Generate and process the original Moonshade Keep sprite assets."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import ExitStack
from io import BytesIO
from pathlib import Path
from shutil import copyfile

import numpy as np
from PIL import Image, ImageDraw, PngImagePlugin

if __package__:
    from . import sprite_grid as grid
else:
    import sprite_grid as grid


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
RAW = ASSETS / "raw"
SOURCE = ASSETS / "source"
PREVIEW = ASSETS / "preview"
PALETTE = ((155, 188, 15), (139, 172, 15), (48, 98, 48), (15, 56, 15))
COLORS = {(0, 0, 0, 0)} | {(*color, 255) for color in PALETTE}
PREVIEW_BG = (35, 76, 35)
MIN_SCORE = .78


def raw_path(name, index):
    return RAW / name / f"{index:02}.png"


def read_image(path):
    with Image.open(path) as image:
        return image.convert("RGBA")


def alpha_bounds(image):
    bounds = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0).getbbox()
    if bounds is None:
        raise ValueError("Image contains no opaque artwork")
    return bounds


def request_image(client, model, prompt, references, size):
    options = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": "high",
        "background": "transparent",
        "output_format": "png",
    }
    for attempt in range(3):
        try:
            with ExitStack() as stack:
                if references:
                    images = [stack.enter_context(path.open("rb")) for path in references]
                    result = client.images.edit(image=images, **options)
                else:
                    result = client.images.generate(**options)
            with Image.open(BytesIO(base64.b64decode(result.data[0].b64_json))) as image:
                rgba = image.convert("RGBA")
            alpha_bounds(rgba)
            return rgba
        except Exception as error:
            if attempt == 2:
                raise
            print(f"  Retry {attempt + 1}/2 ({type(error).__name__})", file=sys.stderr)
            time.sleep(2 ** attempt)


def read_selection(name):
    selection = RAW / name / "selection.json"
    return json.loads(selection.read_text(encoding="utf-8")) if selection.exists() else {}


def make_prompt(name, spec, common, retry):
    width, height = spec["size"]
    frames = spec["frames"]
    cols = width * len(frames)
    canvas = (1536, 1024) if len(frames) > 1 else (1024, 1024)
    prompt = common.format(cols=cols, rows=height, pitch_x=canvas[0] / cols,
                           pitch_y=canvas[1] / height)
    prompt += " Opaque art edge to edge." if spec.get("texture") else " Transparent outside the subject."
    if name.startswith("player_"):
        prompt += (" Right-facing knight, keep bright hair/ahoge (rows 1–6), one dark eye,"
                   " bright round silver armor (rows 7–10), a dark tunic and belt, and two-pixel-wide"
                   " silver boots ending at row 15. Keep body centered in columns 4–11.")
    prompt += f" Draw exactly {len(frames)} frame(s) of {width}x{height} cells, left to right."
    prompt += " " + " ".join(f"Frame {i}: {pose}" for i, pose in enumerate(frames, 1))
    if retry:
        prompt += " Use larger solid clusters, fewer one-cell details, and brighter armor or lit faces."
    return prompt, "x".join(map(str, canvas))


def selected_idle():
    index = read_selection("player_idle").get("candidate")
    if index is None or not raw_path("player_idle", index).exists():
        raise FileNotFoundError("Generate or select player_idle before generating poses that reference it")
    return raw_path("player_idle", index)


def evaluate(image, name, spec):
    width, height = spec["size"]
    n = len(spec["frames"])
    allowed = tuple(index + 1 for index in spec.get("shades", range(4)))
    query, agreement = grid.read_sheet(image, width * n, height, allowed, spec.get("texture", False))
    if not agreement:
        return None, {}
    frames = np.array([grid.finish(query[:, i * width:(i + 1) * width], name, spec) for i in range(n)])
    parts = grid.score_frames(frames, agreement, name)
    if not parts:
        return None, {}
    png = grid.to_png(frames)
    return match_walk_head(png) if name == "player_walk" else png, parts


def match_walk_head(walk):
    idle_path = SOURCE / "player_idle.png"
    if idle_path.is_file():
        idle = read_image(idle_path)
        head = idle.crop((0, 0, idle.width, 7))
        for x in range(0, walk.width, idle.width):
            walk.paste(head, (x, 0))
    return walk


def mean_score(parts):
    return sum(parts.values()) / len(parts) if parts else 0


def generate_candidates(client, model, name, spec, common):
    refs = []
    if spec.get("reference") == "idle":
        refs = [selected_idle()]
    elif spec.get("reference"):
        refs = [ROOT / spec["reference"]]
        if not refs[0].is_file():
            raise FileNotFoundError(refs[0])
    candidates = []
    for retry in (False, True):
        prompt, size = make_prompt(name, spec, common, retry)
        for _ in range(4):
            image = request_image(client, model, prompt, refs, size)
            candidates.append((image, *evaluate(image, name, spec)))
        if max(mean_score(parts) for _, _, parts in candidates) >= MIN_SCORE:
            break
    for index, (image, _, _) in enumerate(candidates, 1):
        image.save(raw_path(name, index))
    for index in range(len(candidates) + 1, 9):
        raw_path(name, index).unlink(missing_ok=True)
    return [(i, image, parts) for i, (_, image, parts) in enumerate(candidates, 1)]


def load_candidates(name, spec):
    choices = [(i, *evaluate(read_image(raw_path(name, i)), name, spec))
               for i in range(1, 9) if raw_path(name, i).is_file()]
    if not choices:
        raise FileNotFoundError(f"No candidate sheets in assets/raw/{name}/")
    return choices


def saved_preview_candidates(name):
    path = PREVIEW / "candidates" / f"{name}.png"
    if not path.is_file():
        return []
    with Image.open(path) as preview:
        records = json.loads(preview.info.get("sprite_candidates", "[]"))
    return [(record["index"], Image.open(BytesIO(base64.b64decode(record["png"]))).convert("RGBA")
             if record["png"] else None, record["scores"]) for record in records]


def save_candidates(name, spec, candidates, selected):
    width, height = spec["size"]
    n = len(spec["frames"])
    scale, padding = 4, 10
    card_w, card_h = max(width * n * scale, 128) + 2 * padding, height * scale + 44
    columns = 2
    rows = (len(candidates) + columns - 1) // columns
    board = Image.new("RGB", (card_w * columns, card_h * rows), (15, 56, 15))
    draw = ImageDraw.Draw(board)
    records = []
    for slot, (index, png, parts) in enumerate(candidates):
        x, y = (slot % columns) * card_w + padding, (slot // columns) * card_h + padding
        marker = " SELECTED" if index == selected else ""
        score = f"{sum(parts.values()):.2f}/{len(parts)}" if parts else "invalid"
        draw.text((x, y), f"{index:02d}  {score}{marker}", fill=(205, 224, 165))
        buffer = BytesIO()
        if png is not None:
            png.save(buffer, "PNG")
        records.append({"index": index, "scores": parts,
                        "png": base64.b64encode(buffer.getvalue()).decode("ascii")})
        if png is None:
            continue
        enlarged = png.resize((png.width * scale, png.height * scale), Image.Resampling.NEAREST)
        board.paste(PREVIEW_BG, (x, y + 14, x + enlarged.width, y + 14 + enlarged.height))
        board.paste(enlarged, (x, y + 14), enlarged)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("sprite_candidates", json.dumps(records, separators=(",", ":")), zip=True)
    board.save(PREVIEW / "candidates" / f"{name}.png", pnginfo=metadata)


def validate_sprite(sheet, spec):
    width, height = spec["size"]
    if sheet.size != (width * len(spec["frames"]), height):
        raise ValueError(f"Unexpected sheet size {sheet.size}")
    allowed = COLORS
    if "shades" in spec:
        allowed = {(0, 0, 0, 0)} | {(*PALETTE[index], 255) for index in spec["shades"]}
    counts = sheet.getcolors(maxcolors=len(allowed))
    if counts is None or any(color not in allowed for _, color in counts):
        raise ValueError("Sheet includes pixels outside the specified palette")
    for x in range(0, sheet.width, width):
        if sheet.crop((x, 0, x + width, height)).getbbox() is None:
            raise ValueError("Sheet contains an empty frame")


def update_previews(sprites):
    cards = []
    for name, spec in sprites.items():
        path = ASSETS / f"{name}.png"
        if not path.is_file():
            continue
        image = read_image(path)
        validate_sprite(image, spec)
        enlarged = image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST)
        preview = Image.new("RGB", enlarged.size, PREVIEW_BG)
        preview.paste(enlarged, (0, 0), enlarged)
        preview.save(PREVIEW / path.name)
        cards.append((name, preview))
    if not cards:
        return
    positions = []
    max_width, gap, label_height = 1120, 16, 18
    x = y = gap
    row_height = 0
    for name, preview in cards:
        if x + preview.width + gap > max_width:
            x, y = gap, y + row_height + gap
            row_height = 0
        positions.append((name, preview, x, y))
        x += preview.width + gap
        row_height = max(row_height, preview.height + label_height)
    overview = Image.new("RGB", (max_width, y + row_height + gap), (15, 56, 15))
    draw = ImageDraw.Draw(overview)
    for name, preview, x, y in positions:
        draw.text((x, y), name, fill=(205, 224, 165))
        overview.paste(preview, (x, y + label_height))
    overview.save(PREVIEW / "_sheet.png")


def remember_baseline(sprites):
    baseline = RAW / "_baseline"
    baseline.mkdir(exist_ok=True)
    for name in sprites:
        source = SOURCE / f"{name}.png"
        backup = baseline / source.name
        if source.is_file() and not backup.exists():
            copyfile(source, backup)


def update_comparison(sprites):
    panels = []
    for folder, label in ((RAW / "_baseline", "BEFORE"), (SOURCE, "AFTER")):
        items = []
        for name, spec in sprites.items():
            path = folder / f"{name}.png"
            if not path.is_file():
                continue
            sprite = read_image(path)
            validate_sprite(sprite, spec)
            items.append((name, sprite.resize((sprite.width * 8, sprite.height * 8), Image.Resampling.NEAREST)))
        if not items:
            return
        positions = []
        x, y, row_h = 12, 38, 0
        for name, image in items:
            if x + image.width + 12 > 1120:
                x, y, row_h = 12, y + row_h + 14, 0
            positions.append((name, image, x, y))
            x += image.width + 12
            row_h = max(row_h, image.height + 16)
        panel = Image.new("RGB", (1120, y + row_h + 20), (15, 56, 15))
        draw = ImageDraw.Draw(panel)
        draw.text((12, 12), label, fill=(205, 224, 165))
        for name, image, x, y in positions:
            draw.text((x, y), name, fill=(205, 224, 165))
            panel.paste(PREVIEW_BG, (x, y + 16, x + image.width, y + 16 + image.height))
            panel.paste(image, (x, y + 16), image)
        panels.append(panel)
    output = Image.new("RGB", (1120, sum(panel.height for panel in panels)), (15, 56, 15))
    output.paste(panels[0], (0, 0))
    output.paste(panels[1], (0, panels[0].height))
    output.save(PREVIEW / "compare.png")


def update_overrides(written):
    if not written:
        return
    path = ASSETS / "overrides.json"
    data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    data.setdefault("sprites", {}).update(written)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_service_worker(written):
    if not written:
        return
    path = ROOT / "sw.js"
    if not path.is_file():
        print("sw.js is missing; service worker update skipped.", file=sys.stderr)
        return
    script = path.read_text(encoding="utf-8")
    files = re.search(r"\bFILES\s*=\s*\[(?P<entries>[^\]]*)\]", script)
    version = re.search(r"""\bVERSION\s*=\s*(?P<value>['"][^'"]+['"]|\d+)""", script)
    if files is None or version is None:
        raise ValueError("Could not locate the FILES array and VERSION literal in sw.js")

    entries = files["entries"].rstrip()
    urls = [f"assets/{name}.png" for name in written]
    urls.append("assets/overrides.json")
    for url in urls:
        if re.search(r"""['"](?:\./|/)?""" + re.escape(url) + r"""['"]""", entries):
            continue
        if entries.strip() and not entries.endswith(","):
            entries += ","
        entries += f"\n  './{url}',"
    script = script[:files.start("entries")] + entries + "\n" + script[files.end("entries"):]
    digest = hashlib.sha256()
    for url in sorted(re.findall(r"""['"](?:\./|/)?(assets/[^'"]+)['"]""", entries)):
        asset = ROOT / url
        if asset.is_file():
            digest.update(url.encode("utf-8"))
            digest.update(asset.read_bytes())
    version = re.search(r"""\bVERSION\s*=\s*(?P<value>['"][^'"]+['"]|\d+)""", script)
    value = version["value"]
    if value.isdecimal():
        replacement = str(int(value) + 1)
    else:
        prefix = re.sub(r"-sprites-[0-9a-f]{12}$", "", value[1:-1])
        replacement = f"{value[0]}{prefix}-sprites-{digest.hexdigest()[:12]}{value[-1]}"
    script = script[:version.start("value")] + replacement + script[version.end("value"):]
    path.write_text(script, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--only", help="Comma-separated sprite names")
    parser.add_argument("--reprocess", action="store_true", help="Score and finish existing raw candidate sheets offline")
    parser.add_argument("--pick", metavar="NAME=INDEX", action="append", default=[],
                        help="Select a saved candidate (number 1-8) offline")
    parser.add_argument("--model", default=os.getenv("IMAGE_MODEL", "gpt-image-1"))
    args = parser.parse_args()

    config = json.loads(Path(__file__).with_name("sprite_prompts.json").read_text(encoding="utf-8"))
    sprites = config["sprites"]
    picks = {}
    for pick in args.pick:
        name, _, number = pick.partition("=")
        if not re.fullmatch("[1-8]", number):
            parser.error("--pick requires NAME=INDEX with a candidate number 1–8")
        picks[name] = int(number)
    if not (args.all or args.only or picks):
        parser.error("Select sprites with --all, --only, or --pick")
    requested = set(sprites) if args.all else set(picks)
    if args.only:
        requested.update(name.strip() for name in args.only.split(","))
    if unknown := requested - sprites.keys():
        parser.error("Unknown sprites: " + ", ".join(sorted(unknown)))
    offline = args.reprocess or bool(picks)
    client = None
    if not offline:
        if not os.getenv("OPENAI_API_KEY"):
            parser.error("Set OPENAI_API_KEY to generate assets, or use --reprocess.")
        from openai import OpenAI
        client = OpenAI(max_retries=0)

    RAW.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    (PREVIEW / "candidates").mkdir(parents=True, exist_ok=True)
    remember_baseline(sprites)
    failed = []
    written = {}
    for name, spec in sprites.items():
        if name not in requested:
            continue
        try:
            folder = RAW / name
            folder.mkdir(exist_ok=True)
            if name in picks and not any(raw_path(name, i).is_file() for i in range(1, 9)):
                candidates = saved_preview_candidates(name)
                if name == "player_walk":
                    for _, png, _ in candidates:
                        if png is not None:
                            match_walk_head(png)
            elif offline:
                candidates = load_candidates(name, spec)
            else:
                candidates = generate_candidates(client, args.model, name, spec, config["common"])
            if not candidates:
                raise FileNotFoundError(f"No saved candidates for {name}")
            previous = read_selection(name) if offline else {}
            manual = picks.get(name, previous.get("manual"))
            if manual is None:
                selected = max(candidates, key=lambda option: mean_score(option[2]))
            else:
                selected = next((option for option in candidates if option[0] == manual), None)
                if selected is None:
                    raise ValueError(f"Candidate {manual} does not exist")
            index, png, scores = selected
            save_candidates(name, spec, candidates, index)
            if png is None:
                raise ValueError(f"Candidate {index} has an empty frame")
            validate_sprite(png, spec)
            png.save(SOURCE / f"{name}.png")
            (folder / "selection.json").write_text(
                json.dumps({"candidate": index, "manual": manual, "scores": scores}, indent=2) + "\n",
                encoding="utf-8")
            written[name] = spec["size"][0]
            print(f"Selected {name} #{index} ({sum(scores.values()):.2f}/{len(scores)})")
        except Exception as error:
            failed.append(name)
            print(f"Skipped {name}: {error}", file=sys.stderr)

    if "player_idle" in written and "player_walk" not in written:
        walk_path = SOURCE / "player_walk.png"
        if walk_path.is_file():
            match_walk_head(read_image(walk_path)).save(walk_path)
            written["player_walk"] = sprites["player_walk"]["size"][0]
    if written:
        process = subprocess.run([sys.executable, str(ROOT / "tools/polish_sprites.py"), "--only", *written])
        if process.returncode:
            return process.returncode
    update_overrides(written)
    update_service_worker(written)
    update_previews(sprites)
    update_comparison(sprites)
    if failed:
        print("Failed sprites: " + ", ".join(failed), file=sys.stderr)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
