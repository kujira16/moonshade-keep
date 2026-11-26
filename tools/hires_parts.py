"""Read full-color material maps and reduce them to twice-resolution sprites."""

import numpy as np
from PIL import Image

if __package__:
    from . import knight_parts as knight, sprite_grid as grid
else:
    import knight_parts as knight
    import sprite_grid as grid


HEAD_ROWS = 14
REDUCTION_ORDER = "EABOFPHCWTSLK."
SHADE_ORDER = (4, 1, 2, 3, 0)


def reduce_map(source, order, outline, transparent):
    """Read the highest-priority material in each 2x2 block."""
    height, width = source.shape
    blocks = source.reshape(height // 2, 2, width // 2, 2)
    result = np.full((height // 2, width // 2), transparent, dtype=source.dtype)
    interior_count = ((blocks != transparent) & (blocks != outline)).sum(axis=(1, 3))
    for material in reversed(order):
        present = np.any(blocks == material, axis=(1, 3))
        if material == outline:
            present &= interior_count < 3
        result[present] = material
    return result


def materials(sample, name):
    """Separate emissive, pale, warm and cool materials before palette mapping."""
    hue, sat, value = np.moveaxis(np.asarray(Image.fromarray(sample).convert("HSV")) / 255, -1, 0)
    hue *= 360
    opaque = sample[:, :, 3] >= 128
    shade = np.zeros(opaque.shape, dtype=np.uint8)
    shade[opaque] = 3
    shade[opaque & (value < .28)] = 4
    warm = (hue < 75) | (hue > 330)
    pale = sat < .28
    emissive = (value > .76) & ((sat < .38) | (hue >= 20) & (hue < 65))
    shade[opaque & (value >= .48) & (warm | pale)] = 2
    shade[opaque & emissive] = 1
    if name in {"skeleton", "boss_skull", "ghost", "bone"}:
        shade[opaque & pale & (value >= .65)] = 1
        shade[opaque & (sat < .46) & (value >= .37) & (value < .65)] = 2
    if name in {"heart", "gem", "orb", "fireball", "candle", "t_window"}:
        shade[opaque & (value >= .50) & (shade == 3)] = 2
        shade[opaque & (value >= .88) & (sat <= .56)] = 1
    if name in {"gem", "orb", "fireball"}:
        shade[opaque & (shade == 1) & (sat > .62)] = 2
    if name == "ghost":
        shade[opaque & (hue >= 165) & (hue <= 245) & (sat >= .21) & (value >= .43)] = 2
    if name.startswith("t_"):
        if name in {"t_pillar", "t_back"}:
            shade[opaque] = np.where(value[opaque] >= .29, 3, 4)
        elif name in {"t_brick", "t_brick_top", "t_ledge", "t_spikes"}:
            shade[opaque] = np.select([value[opaque] >= .70, value[opaque] >= .44,
                                       value[opaque] >= .25], [1, 2, 3], default=4)
    return shade


def outlined(frame):
    mask = frame != 0
    padded = np.pad(mask, 1)
    near = (padded[1:-1, :-2] | padded[1:-1, 2:] |
            padded[:-2, 1:-1] | padded[2:, 1:-1])
    return np.where(~mask & near, 4, frame).astype(np.uint8)


def tile_edges(frame, name):
    """Carry horizontal courses across the joins and keep the column periodic."""
    result = frame.copy()
    if name == "t_pillar":
        for x in range(result.shape[1]):
            stripe = np.bincount(result[:, x], minlength=5).argmax()
            result[:, x] = stripe
        return result
    if name in {"t_brick", "t_brick_top", "t_back"}:
        result[result == 0] = 4
        for y, row in enumerate(result):
            edges = row[[1, 2, -3, -2]]
            seam = np.bincount(edges, minlength=5).argmax()
            row[0] = row[-1] = seam
        if name != "t_brick_top":
            # Equal edge rows give a continuous horizontal mortar course.
            result[[0, -1]] = 4
        else:
            result[0] = np.where(result[0] >= 3, 2, result[0])
    if name == "t_ledge":
        result[8:] = 0
        for row in result[:8]:
            if row.any():
                shade = np.bincount(row[1:-1], minlength=5).argmax()
                row[0] = row[-1] = shade
    if name == "t_spikes":
        result[:-24] = 0
    return result


def creature_details(frame, name):
    result = frame.copy()
    box = grid.bounds(result)
    if box is None:
        return result
    x0, y0, x1, y1 = box
    _, width = result.shape
    if name == "skeleton":
        center = (x0 + x1) // 2
        for y in range(y0 + (y1 - y0) * 45 // 100, min(y1 - 4, y0 + (y1 - y0) * 45 // 100 + 6)):
            if np.count_nonzero(result[y, center - 3:center + 4]) < 4:
                continue
            result[y, center - 3:center + 4] = 1 if (y - y0 - (y1 - y0) * 45 // 100) % 2 == 0 else 4
    if name in {"bat", "bat_hang", "boss_skull"}:
        center = width // 2
        body_height = y1 - y0
        y = y0 + int(body_height * {"bat": .60, "bat_hang": .69, "boss_skull": .55}[name])
        offset = {"bat": 3, "bat_hang": 2, "boss_skull": 5}[name]
        eye_y, eye_x = np.nonzero((result == 4) & (np.indices(result.shape)[1] < center))
        for x in (center - offset, center + offset - 1):
            if result[y, x] == 0:
                continue
            if name == "boss_skull":
                points = [(abs(int(yy) - y) + abs(int(xx) - x), int(yy), int(xx))
                          for yy, xx in zip(eye_y, eye_x)
                          if abs(int(yy) - y) <= 3 and abs(int(xx) - x) <= 2]
                if x < center and points:
                    _, yy, xx = min(points)
                    result[yy, xx] = 1
            else:
                result[y, x] = 1
    if name == "boss_skull":
        left, right = result[:, :width // 2], result[:, width // 2:][:, ::-1]
        half = np.where(left, left, right)
        result = np.concatenate((half, half[:, ::-1]), axis=1)
    return result


def neighbors(array, pad):
    padded = np.pad(array, 1, constant_values=pad)
    return np.stack((padded[1:-1, :-2], padded[1:-1, 2:],
                     padded[:-2, 1:-1], padded[2:, 1:-1]))


def fill_knight_outline(parts, target):
    """Recover the material under dark source lines; redraw the contour later."""
    filled = parts.copy()
    for y, x in zip(*np.nonzero(parts == "O")):
        window = parts[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        options = "HF" if y < 18 else "PCLTS"
        if y >= 28:
            options += "K"
        counts = [np.count_nonzero(window == part) for part in options]
        if max(counts):
            filled[y, x] = options[int(np.argmax(counts))]
        elif target[y, x] in options:
            filled[y, x] = target[y, x]
        else:
            filled[y, x] = "H" if y < 18 else ("C" if y < 24 else "T")
    return filled


def checker_locations(frame):
    a, b, c, d = frame[:-1, :-1], frame[:-1, 1:], frame[1:, :-1], frame[1:, 1:]
    return np.argwhere((a > 0) & (b > 0) & (a == d) & (b == c) & (a != b))


def remove_checkers(frame, protected):
    """Merge alternating 2x2 dots, favoring a flat run away from small landmarks."""
    result = frame.copy()
    while True:
        original = checker_locations(result)
        if not len(original):
            return result
        updated = False
        for y, x in original:
            before = len(checker_locations(result))
            if result[y, x] != result[y + 1, x + 1] or result[y, x + 1] != result[y + 1, x]:
                continue
            for yy, xx in ((y + 1, x + 1), (y + 1, x), (y, x + 1), (y, x)):
                if protected[yy, xx]:
                    continue
                value = result[yy, xx]
                replacement = result[y, x + 1] if value == result[y, x] else result[y, x]
                result[yy, xx] = replacement
                if len(checker_locations(result)) < before:
                    updated = True
                    break
                result[yy, xx] = value
        if not updated:
            return result


def smooth_materials(frame, parts, protected):
    nearby = neighbors(frame, 0)
    same_part = neighbors(parts, ".") == parts
    disagrees = ((nearby != frame) & same_part).sum(axis=0)
    counts = np.stack([((nearby == shade) & same_part).sum(axis=0) for shade in range(1, 5)])
    majority = counts.argmax(axis=0) + 1
    smooth = (disagrees >= 2) & (frame != 0) & ~protected
    return np.where(smooth, majority, frame).astype(np.uint8)


def knight_interior(frame):
    opaque = frame != 0
    outline = (frame == 4) & np.any(neighbors(frame, 0) == 0, axis=0)
    return opaque & ~outline


def knight_ink(frame, hair, eye):
    inside = knight_interior(frame)
    shares_eye = np.any(neighbors(eye, False), axis=0)
    ink_in_hair = (frame == 4) & hair & inside & ~eye & ~shares_eye
    shares = np.array([np.count_nonzero(inside & (frame == shade)) for shade in range(1, 5)])
    return shares / max(1, np.count_nonzero(inside)), int(ink_in_hair.sum())


def shade_balance(shares):
    low, high = np.array([.25, .25, .10, 0]), np.array([.40, .40, .25, .25])
    excess = np.maximum(low - shares, 0) + np.maximum(shares - high, 0)
    return max(0, 1 - float(excess.sum()))


def knight_details(parts, target, name):
    """Add the small material accents that would otherwise vanish in reduction."""
    work = parts.copy()
    yy, xx = np.indices(work.shape)
    attacking = "attack" in name
    hair = (yy >= 3) & (yy < 18)
    face = (yy >= 9) & (yy < 18) & (xx >= 17) & (xx < 29)
    if attacking:
        columns = np.nonzero(work[9:17] == "F")[1]
        if len(columns):
            shift = min(5, max(0, 26 - int(np.percentile(columns, 90))))
            if shift:
                work[:17, shift:] = parts[:17, :-shift]
                work[:17, :shift] = "."
    work[(work == "F") & (yy < 8)] = "H"
    if np.count_nonzero((work == "H") & hair) < 35:
        work[(target == "H") & hair] = "H"
    if np.count_nonzero((work == "F") & face) < 24:
        work[(target == "F") & face] = "F"
    work[(work == "E") & face] = "F"
    work[work == "E"] = "O"
    work[work == "A"] = "H"
    work[:4] = "."
    for y, x in ((0, 21), (1, 21), (1, 20), (2, 20)):
        work[y, x] = "A"
    work[3:5, 20] = "H"
    work[12:15, 22:24] = "E"
    for material in ("P", "C", "T", "B", "L"):
        zone = (yy >= 18) & ((xx < 25) if attacking else True)
        if np.count_nonzero((work == material) & zone) < 7:
            work[(target == material) & zone] = material
    if not attacking and np.count_nonzero(work == "S") < 4:
        work[target == "S"] = "S"
    if not np.any(work[-1, 8:25] != "."):
        work[-1, 11:15] = "K"
        if name in {"player_idle", "player_attack"}:
            work[-1, 21:25] = "K"
    if attacking:
        work[:, 27:][work[:, 27:] == "W"] = "."
        work[16:18, 23:32] = "W"

    work = fill_knight_outline(work, target)
    stray_skin = (work == "F") & (yy < 15) & ((neighbors(work, ".") == "H").sum(axis=0) >= 3)
    work[stray_skin] = "H"
    work[(work == "B") & (yy != 24)] = "T"
    cloth = (yy >= 22) & (yy <= 27) & (xx >= 12) & (xx <= 23)
    work[cloth & ((target == "T") | ((yy >= 25) & (xx >= 14) & (xx <= 21))) &
         np.isin(work, ["C", "P", "T"])] = "T"
    frame = np.array([knight.PART_SHADE[p] for p in work.flat], dtype=np.uint8).reshape(work.shape)
    hair_part = np.isin(work, ["H", "A"])
    # The lower-left edge of the hair gets a single broad shadow band.
    frame[(work == "H") & (xx <= 9) & (yy >= 11)] = 2
    frame[3, 20] = 2
    armor = np.isin(work, ["P", "C", "L"])
    light = armor & ~np.isin(np.pad(work, 1, constant_values=".")[:-2, 1:-1], ["P", "C", "L"])
    frame[light & (xx >= 12) & (yy >= 18) & (yy < 23)] = 1
    protected = np.isin(work, ["A", "E", "B", "K", "W"])
    protected[3, 20] = True
    frame = smooth_materials(frame, work, protected)
    frame[12, 22] = 1
    # Alternating braid links near the back of the head.
    for y, x in ((9, 10), (11, 9), (13, 8)):
        if frame[y - 1:y + 2, x:x + 3].any():
            frame[y:y + 2, x:x + 2] = 2
            frame[y + 1, x] = 3
            protected[y:y + 2, x:x + 2] = True
    # Rounded pauldron, a polished spot on it, and engraved lines in the breastplate.
    radius = (xx - 11) ** 2 + (yy - 21) ** 2
    disk = radius <= 7
    rim = (radius > 7) & (radius <= 12) & (frame != 0)
    frame[rim] = 3
    frame[disk] = 2
    frame[20, 10:12] = 1
    frame[21, 9] = 3
    for x in (16, 19):
        frame[20:23, x:x + 2] = 2
        frame[21:23, x] = 3
    protected[disk | rim] = True
    protected[20:23, 16:21] = True
    collar = (yy == 18) & (xx >= 16) & (xx <= 24) & (frame != 0)
    frame[collar] = 3
    protected[collar] = True
    # Keep the tunic a solid dark plane under the belt.
    waist = (yy >= 25) & (yy <= 27) & (xx >= 10) & (xx <= 23)
    tunic = waist & ((work == "T") | ((target == "T") & (work != ".")))
    frame[tunic] = 3
    belt = (yy == 24) & (xx >= 11) & (xx <= 22) & (frame != 0)
    frame[belt] = 4
    frame[24, 18:20] = 1
    protected[belt] = True
    protected[24, 18:20] = True
    if attacking:
        frame[15:19, 23] = 1
        protected[15:19, 23] = True
    else:
        frame[24, 8:11] = 1
        protected[24, 8:11] = True
    frame = remove_checkers(outlined(frame), protected)
    shares, hair_ink = knight_ink(frame, hair_part, work == "E")
    return frame, shares, hair_ink


def score_detail(parts):
    anchors = {
        "eye": (parts[10:16, 16:27] == "E").any(),
        "hair_hook": np.count_nonzero(parts[:5] == "A") >= 3,
        "pauldron": np.count_nonzero(parts[17:24] == "P") >= 8,
        "engraving": np.count_nonzero(parts[18:24, 14:23] == "C") >= 8,
        "tunic": np.count_nonzero(parts[23:] == "T") >= 8,
        "belt": np.count_nonzero(parts[20:27] == "B") >= 3,
        "braid": np.count_nonzero(parts[7:16, :13] == "H") >= 10,
    }
    return sum(anchors.values()) / len(anchors)


def has_knight_details(frame, attacking):
    eye = frame[12:15, 22:24]
    braid = frame[9:15, 8:12]
    pauldron = frame[19:24, 9:14]
    hilt = frame[15:19, 23] if attacking else frame[24, 8:11]
    return all((
        np.count_nonzero(eye == 4) == 5 and np.count_nonzero(eye == 1) == 1,
        np.count_nonzero(frame[:4] == 1) == 4,
        np.count_nonzero(braid == 3) >= 2 and np.count_nonzero(braid == 2) >= 4,
        np.count_nonzero(pauldron == 2) >= 8 and np.any(pauldron == 1),
        np.all(frame[21:23, [16, 19]] == 3),
        np.all(frame[24, 18:20] == 1) and np.any(hilt == 1),
    ))


def evaluate(sample, agreement, name, spec, target, thresholds):
    if not agreement:
        return None, {}
    width, height = spec["size"]
    frames, templates, details, balances = [], [], [], []
    if sample.shape != (height * 2, width * 2 * len(spec["frames"]), 4):
        return None, {}
    for i in range(len(spec["frames"])):
        image = sample[:, i * width * 2:(i + 1) * width * 2]
        alpha = image[:, :, 3]
        if not alpha.any() or (not spec.get("texture") and alpha.mean() > 230):
            return None, {}
        if name.startswith("player_"):
            parts = reduce_map(knight.read_parts(image, thresholds, "attack" in name), REDUCTION_ORDER, "O", ".")
            weights = np.where(np.isin(target, ["A", "E", "P", "F"]), 3, 1)
            overlap = (parts != ".") | (target != ".")
            templates.append(float(weights[(parts == target) & overlap].sum() / weights[overlap].sum()))
            details.append(score_detail(parts))
            frame, shares, hair_ink = knight_details(parts, target, name)
            torso = knight_interior(frame)[18:]
            torso_dark = np.count_nonzero(torso & (frame[18:] == 4)) / max(1, np.count_nonzero(torso))
            if (not has_knight_details(frame, "attack" in name) or
                    max(shares[3], torso_dark) > .25 or hair_ink or len(checker_locations(frame))):
                return None, {}
            balances.append(shade_balance(shares))
        else:
            frame = reduce_map(materials(image, name), SHADE_ORDER, 4, 0)
            if name.startswith("t_"):
                frame = tile_edges(frame, name)
            else:
                frame = creature_details(frame, name)
        frames.append(frame)
    if not all(grid.bounds(frame) for frame in frames):
        return None, {}
    scores = grid.score_frames(np.array(frames), agreement, name, scale=spec["scale"])
    if templates:
        scores.pop("reference", None)
        scores.update(template=float(np.mean(templates)), details=float(np.mean(details)),
                      balance=float(np.mean(balances)))
    return grid.to_png(np.array(frames)), scores
