"""Generate and process the original Moonshade Keep sprite assets."""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
from contextlib import ExitStack
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
RAW = ASSETS / "raw"
PREVIEW = ASSETS / "preview"
PALETTE = ((155, 188, 15), (139, 172, 15), (48, 98, 48), (15, 56, 15))
COLORS = {(0, 0, 0, 0)} | {(*color, 255) for color in PALETTE}
PREVIEW_BG = (35, 76, 35)
LEVELS = (151, 115, 58)


def raw_path(name, index):
    return RAW / f"{name}_{index + 1:02}.png"


def read_image(path):
    with Image.open(path) as image:
        return image.convert("RGBA")


def alpha_bounds(image):
    bounds = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0).getbbox()
    if bounds is None:
        raise ValueError("Image contains no opaque artwork")
    return bounds


def request_image(client, model, prompt, references):
    options = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1024",
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


def generate_sources(client, model, name, spec, common):
    width, height = spec["size"]
    reference = ROOT / spec["reference"] if "reference" in spec else None
    if reference is not None and not reference.is_file():
        raise FileNotFoundError(reference.relative_to(ROOT))
    backdrop = ("Only the texture, opaque edge to edge." if spec.get("texture")
                else "Isolate the silhouette on a genuinely transparent background.")
    sources = []
    with TemporaryDirectory(dir=RAW) as temporary:
        first = Path(temporary) / "first_frame.png"
        for index, pose in enumerate(spec["frames"]):
            references = [first] if index and spec.get("match_frames") else []
            if reference is not None:
                references.append(reference)
            prompt = " ".join((common.format(width=width, height=height), backdrop, pose))
            source = request_image(client, model, prompt, references)
            if index == 0 and spec.get("match_frames"):
                source.save(first)
            sources.append(source)
    return sources


def downsample(source, spec):
    width, height = spec["size"]
    cropped = source.crop(alpha_bounds(source))
    if spec.get("texture"):
        scaled = cropped.resize((width, height), Image.Resampling.BOX)
        background = Image.new("RGBA", (width, height), (*PALETTE[3], 255))
        return Image.alpha_composite(background, scaled)

    target_width, target_height = spec.get("content_size", (width, height))
    scale = min(target_width / cropped.width, target_height / cropped.height)
    size = (target_width, target_height) if spec.get("fill_content") else (
        max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))
    )
    scaled = cropped.resize(size, Image.Resampling.BOX)
    bounds = alpha_bounds(scaled)
    x = width - bounds[2] if spec.get("align") == "right" else (width - size[0]) // 2
    anchor = spec.get("anchor", "bottom")
    y = {
        "top": -bounds[1],
        "center": (height - size[1]) // 2,
        "bottom": height - bounds[3],
    }[anchor]
    result = Image.new("RGBA", (width, height))
    result.paste(scaled, (x, y))
    return result


def quantize(source, spec):
    image = downsample(source, spec)
    width, height = image.size
    pixels = image.load()
    levels = spec.get("levels", LEVELS)
    shades = spec.get("shades", range(4))
    indices = {}
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha >= 128:
                luma = 0.299 * red + 0.587 * green + 0.114 * blue
                index = sum(luma < level for level in levels)
                indices[x, y] = min(shades, key=lambda shade: abs(index - shade))

    result = Image.new("RGBA", image.size)
    output = result.load()
    outline = spec.get("outline", not spec.get("texture"))
    for (x, y), index in indices.items():
        neighbors = ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
        if outline and index < 2 and any(
            0 <= nx < width and 0 <= ny < height and (nx, ny) not in indices
            for nx, ny in neighbors
        ):
            index = 3
        output[x, y] = (*PALETTE[index], 255)
    return result


def save_sprite(name, spec, sources):
    width, height = spec["size"]
    frames = [quantize(source, spec) for source in sources]
    sheet = Image.new("RGBA", (width * len(spec["frames"]), height))
    if len(frames) != len(spec["frames"]):
        raise ValueError("Unexpected frame count")
    for index, frame in enumerate(frames):
        if frame.getbbox() is None:
            raise ValueError(f"Frame {index + 1} is empty after resizing")
        sheet.paste(frame, (index * width, 0))
    validate_sprite(sheet, spec)
    sheet.save(ASSETS / f"{name}.png")


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
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--only", help="Comma-separated sprite names")
    parser.add_argument("--reprocess", action="store_true", help="Process existing raw PNGs offline")
    parser.add_argument("--model", default=os.getenv("IMAGE_MODEL", "gpt-image-1"))
    args = parser.parse_args()

    config = json.loads(Path(__file__).with_name("sprite_prompts.json").read_text(encoding="utf-8"))
    sprites = config["sprites"]
    requested = set(sprites) if args.all else {name.strip() for name in args.only.split(",")}
    if unknown := requested - sprites.keys():
        parser.error("Unknown sprites: " + ", ".join(sorted(unknown)))
    client = None
    if not args.reprocess:
        if not os.getenv("OPENAI_API_KEY"):
            parser.error("Set OPENAI_API_KEY to generate assets, or use --reprocess.")
        from openai import OpenAI
        client = OpenAI(max_retries=0)

    RAW.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    failed = []
    written = {}
    for name, spec in sprites.items():
        if name not in requested:
            continue
        try:
            if args.reprocess:
                sources = [read_image(raw_path(name, i)) for i in range(len(spec["frames"]))]
            else:
                sources = generate_sources(client, args.model, name, spec, config["common"])
            save_sprite(name, spec, sources)
            if not args.reprocess:
                for index, source in enumerate(sources):
                    source.save(raw_path(name, index))
            written[name] = spec["size"][0]
            print(f"Saved assets/{name}.png")
        except Exception as error:
            failed.append(name)
            print(f"Skipped {name}: {error}", file=sys.stderr)

    update_overrides(written)
    update_service_worker(written)
    update_previews(sprites)
    if failed:
        print("Failed sprites: " + ", ".join(failed), file=sys.stderr)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
