"""Read, finish, and score the logical pixels in a generated sprite sheet."""

import numpy as np
from PIL import Image

if __package__:
    from .sprite_palette import GREEN, SHADE_BY_RGB
else:
    from sprite_palette import GREEN, SHADE_BY_RGB

PALETTE = np.array([(0, 0, 0, 0), *((*rgb, 255) for rgb in GREEN)], dtype=np.uint8)
NEIGHBORS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def find_grid(edges, count):
    """Return the pitch and origin with the strongest periodic edge alignment."""
    extent = len(edges) + 1
    nominal = extent / count
    peaks = edges - np.median(edges)
    peaks = np.maximum(peaks, 0)
    peak_weight = peaks.sum()
    if not peak_weight:
        return nominal, 0
    best_score, best = 0, (nominal, 0)
    positions = np.arange(1, extent)
    for pitch in range(max(2, round(nominal * .75)), round(nominal * 1.25) + 1):
        center = (extent - pitch * count) / 2
        for offset in range(-pitch // 2, pitch // 2 + 1):
            origin = center + offset
            phase = (positions - origin) / pitch
            residual = np.abs(phase - np.rint(phase))
            matched = peaks[(residual < .07) & (phase > .5) & (phase < count - .5)]
            coverage = matched.sum() / peak_weight
            score = coverage - .32 * abs(pitch / nominal - 1) - .10 * abs(offset) / pitch
            if score > best_score:
                best_score, best = score, (pitch, origin)
    return best if best_score >= .22 else (nominal, 0)


def classify(rgba, allowed):
    opaque = rgba[:, :, 3] >= 128
    indexed = np.zeros(opaque.shape, dtype=np.uint8)
    rgb = rgba[:, :, :3][opaque].astype(np.float32)
    if not rgb.size:
        return indexed
    colors = PALETTE[allowed, :3].astype(np.float32)
    distance = ((rgb[:, None] - colors) ** 2).sum(axis=2)
    luma = rgb @ np.array([.299, .587, .114], dtype=np.float32)
    low, high = np.percentile(luma, (5, 95))
    if high - low >= 12:
        contrast = np.clip((rgb - low) * (255 / (high - low)), 0, 255)
        normalized = ((contrast[:, None] - colors) ** 2).sum(axis=2)
        # Keep the specified palette stable, including nearly solid generated colors.
        distance = np.where((distance.min(axis=1) < 28 ** 2)[:, None], distance, normalized)
    result = np.array(allowed)[distance.argmin(axis=1)]
    for color, shade in SHADE_BY_RGB.items():
        closest = min(allowed, key=lambda value: abs(value - shade))
        result[np.all(rgb == color, axis=1)] = closest
    indexed[opaque] = result
    return indexed


def cell_boxes(rgba, cols, rows, aligned):
    height, width = rgba.shape[:2]
    if aligned:
        pitch_x, x0 = width / cols, 0
        pitch_y, y0 = height / rows, 0
    else:
        visual = rgba.astype(np.float32)
        visual[:, :, :3] *= visual[:, :, 3:] / 255
        x_edges = np.abs(np.diff(visual, axis=1)).sum(axis=(0, 2))
        y_edges = np.abs(np.diff(visual, axis=0)).sum(axis=(1, 2))
        pitch_x, x0 = find_grid(x_edges, cols)
        pitch_y, y0 = find_grid(y_edges, rows)
    for y in range(rows):
        top = max(0, round(y0 + (y + .25) * pitch_y))
        bottom = min(height, round(y0 + (y + .75) * pitch_y))
        for x in range(cols):
            left = max(0, round(x0 + (x + .25) * pitch_x))
            right = min(width, round(x0 + (x + .75) * pitch_x))
            if bottom > top and right > left:
                yield x, y, np.s_[top:bottom, left:right]


def read_sheet(image, cols, rows, allowed=(1, 2, 3, 4), opaque_tile=False, aligned=False):
    rgba = np.asarray(image.convert("RGBA"))
    indexed = classify(rgba, allowed)
    sheet = np.zeros((rows, cols), dtype=np.uint8)
    agreement = []
    for x, y, region in cell_boxes(rgba, cols, rows, aligned):
        votes = np.bincount(indexed[region].ravel(), minlength=5)
        if votes[0] * 2 < votes.sum():
            sheet[y, x] = np.argmax(votes[1:]) + 1
        if votes[0] != votes.sum():
            agreement.append(votes[sheet[y, x]] / votes.sum())
    if opaque_tile:
        sheet[sheet == 0] = max(allowed)
    return sheet, float(np.mean(agreement)) if agreement else 0.0


def read_color_sheet(image, cols, rows, aligned=False):
    """Sample the dominant RGB cluster at the center of each logical cell."""
    rgba = np.asarray(image.convert("RGBA"))
    output = np.zeros((rows, cols, 4), dtype=np.uint8)
    agreement = []
    for x, y, region in cell_boxes(rgba, cols, rows, aligned):
        cell = rgba[region].reshape(-1, 4)
        opaque = cell[cell[:, 3] >= 128, :3].astype(np.int32)
        if not len(opaque):
            continue
        if len(opaque) * 2 <= len(cell):
            agreement.append(1 - len(opaque) / len(cell))
            continue
        bins = opaque // 16
        codes = (bins[:, 0] << 8) | (bins[:, 1] << 4) | bins[:, 2]
        values, counts = np.unique(codes, return_counts=True)
        winner = counts.argmax()
        cluster = opaque[codes == values[winner]]
        center = cluster[0] // 16 * 16 + 8
        rgb = cluster[((cluster - center) ** 2).sum(axis=1).argmin()]
        output[y, x] = (*rgb, 255)
        agreement.append(len(cluster) / len(cell))
    return output, float(np.mean(agreement)) if agreement else 0.0


def bounds(frame):
    ys, xs = np.nonzero(frame)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def neighbor_values(frame, x, y):
    height, width = frame.shape
    return [int(frame[y + dy, x + dx]) if 0 <= x + dx < width and 0 <= y + dy < height else 0
            for dx, dy in NEIGHBORS]


def clean_dots(frame, keep):
    cleaned = frame.copy()
    for y, x in zip(*np.nonzero(frame)):
        if (x, y) in keep:
            continue
        nearby = neighbor_values(cleaned, x, y)
        shade = cleaned[y, x]
        if shade not in nearby:
            counts = np.bincount(nearby, minlength=5)
            choices = np.flatnonzero(counts == counts.max())
            cleaned[y, x] = min(choices, key=lambda color: abs(int(color) - int(shade)))
    return cleaned


def solidify(frame, keep):
    """Clean isolated dots and bridge single-cell breaks without leaving the canvas."""
    cleaned = clean_dots(frame, keep)
    result = cleaned.copy()
    for y, x in zip(*np.nonzero(cleaned == 0)):
        if (x, y) in keep:
            continue
        left, right, up, down = neighbor_values(cleaned, x, y)
        if left and left == right:
            result[y, x] = left
        elif up and up == down:
            result[y, x] = up
    return result


def thicken_actor(frame, protected):
    filled = frame.copy()
    height, width = frame.shape
    for y in range(1, height):
        for x in range(2, width - 2):
            shade = frame[y, x]
            if not shade or frame[y - 1, x] != shade or frame[y, x - 1] or frame[y, x + 1]:
                continue
            step = 1 if x < width / 2 else -1
            if frame[y - 1, x + step] and (x + step, y) not in protected:
                filled[y, x + step] = shade
    return filled


def place(frame, name, spec):
    box = bounds(frame)
    if box is None:
        return frame.copy()
    left, top, right, bottom = box
    height, width = frame.shape
    source = frame[top:bottom, left:right]
    anchor = spec.get("anchor", "bottom")
    is_attack = name.startswith("player_attack")
    margin = 1 if not name.startswith("t_") and not is_attack else 0
    if margin and source.shape[1] > width - 2:
        center = (source.shape[1] - width + 2) // 2
        source = source[:, center:center + width - 2]
    if margin and source.shape[0] == height:
        source = source[1:]
    x = width - source.shape[1] if is_attack else (width - source.shape[1]) // 2
    if name == "t_ledge":
        source = source[:4]
    if name == "t_spikes":
        source = source[:12]
    y = {"top": 0, "center": (height - source.shape[0]) // 2, "bottom": height - source.shape[0]}[anchor]
    placed = np.zeros_like(frame)
    placed[y:y + source.shape[0], x:x + source.shape[1]] = source
    return placed


def repeat_wall(frame, name):
    """Remove the duplicated frame margin from generated masonry tiles."""
    result = frame.copy()
    dark = result.max()
    framed = np.mean(result[:, 0] == dark) >= .75 and np.mean(result[:, -1] == dark) >= .75
    if framed or name == "t_back":
        for y, row in enumerate(result):
            edge = np.bincount(row[1:-1], minlength=5).argmax()
            result[y, 0] = result[y, -1] = edge
    if (name != "t_brick_top" and np.mean(result[0] == dark) >= .75
            and np.mean(result[-1] == dark) >= .75):
        result[-1] = result[-2]
    return result


def finish(frame, name, spec):
    if spec.get("texture"):
        return repeat_wall(frame, name)
    if name == "t_pillar":
        shaft = np.array([np.bincount(column, minlength=5).argmax() for column in frame.T],
                         dtype=np.uint8)
        return np.repeat(shaft[None, :], len(frame), axis=0)
    result = place(frame, name, spec)
    # Preserve the feet and the attack contact pixel at the frame boundary.
    keep = {tuple(point) for point in spec.get("keep", [])}
    if name.startswith("player_"):
        keep.update((x, len(frame) - 1) for x in range(frame.shape[1]))
    result = solidify(result, keep)
    if name.startswith("player_") or name in {"skeleton", "ghost", "bat", "boss_skull"}:
        result = thicken_actor(result, keep)
    if name == "boss_skull":
        left = result[:, :result.shape[1] // 2]
        right = result[:, result.shape[1] // 2:][:, ::-1]
        half = np.where(left > 0, left, right)
        result = np.concatenate((half, half[:, ::-1]), axis=1)
    if spec.get("outline", True):
        outlined = result.copy()
        for y, x in zip(*np.nonzero(result)):
            if (x, y) in keep or result[y, x] > 2:
                continue
            nearby = neighbor_values(result, x, y)
            exposed = nearby.count(0)
            # Keep 1px features readable; darker edges are already present in the source.
            if exposed == 1 and sum(value in (1, 2) for value in nearby) >= 2:
                outlined[y, x] = 4
        result = outlined
    if name.startswith("player_"):
        armor = result[7:11]
        armor[armor == 1] = 2
    result = clean_dots(result, keep)
    for x, y, color in spec.get("touchups", []):
        if result[y, x]:
            result[y, x] = color
    return result


def score_frames(frames, agreement, name, scale=1):
    boxes = [bounds(frame) for frame in frames]
    if any(box is None for box in boxes):
        return None
    pixels = sum(np.count_nonzero(frame) for frame in frames)
    isolated = sum(
        frame[y, x] not in neighbor_values(frame, x, y)
        for frame in frames for y, x in zip(*np.nonzero(frame))
    )
    bright = np.count_nonzero((frames == 1) | (frames == 2)) / pixels
    actor = name.startswith("player_") or name in {"bat", "bat_hang", "skeleton", "ghost", "boss_skull", "boss_wing"}
    if actor:
        light = min(1, bright / .4)
        size = np.mean([min(1, (r-l)/(8*scale), 14*scale/(r-l),
                            (b-t)/(12*scale), 16*scale/(b-t)) for l,t,r,b in boxes])
    elif name in {"t_back", "t_pillar"}:
        light, size = min(1, (1 - bright) / .8), 1
    else:
        light, size = min(1, bright / .4), 1
    parts = {"grid": agreement, "clean": 1 - isolated / pixels, "light": light, "size": float(size)}
    if name.startswith("player_"):
        hair = np.count_nonzero(frames[:, :5] == 1) / (8 * len(frames))
        armor = np.count_nonzero((frames[:, 7:11] > 0) & (frames[:, 7:11] <= 2)) / (8 * len(frames))
        sword = float(np.any(frames[:, 7:11, -1])) if "attack" in name else 1
        parts["reference"] = (min(1, hair) + min(1, armor) + sword) / 3
    return parts


def to_png(frames):
    return Image.fromarray(PALETTE[np.concatenate(frames, axis=1)])
