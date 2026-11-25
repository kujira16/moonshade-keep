"""Reduce full-color knight artwork while retaining recognizable features."""

import colorsys

import numpy as np
from PIL import Image

if __package__:
    from . import sprite_grid as grid
else:
    import sprite_grid as grid


HEAD_ROWS = 10
PART_SHADE = {".": 0, "E": 4, "A": 1, "B": 4, "O": 4, "F": 2, "P": 2,
              "H": 1, "C": 2, "W": 2, "T": 3, "S": 3, "L": 2, "K": 4}
PRIORITY = "EABOFPHCWTSLK."
WEIGHTS = {"A": 8, "E": 8, "H": 3, "F": 4, "P": 5, "C": 3}


def template_parts(image_path, rows):
    with Image.open(image_path) as image:
        rgba = np.asarray(image.convert("RGBA"))
    parts = np.array([list(row) for row in rows])
    if parts.shape != (16, 16) or rgba.shape[:2] != parts.shape:
        raise ValueError("Knight template must be 16x16")
    shades = np.array([PART_SHADE[part] for part in parts.flat]).reshape(parts.shape)
    if not np.array_equal(shades, grid.classify(rgba, (1, 2, 3, 4))):
        raise ValueError("The template PNG and configured part labels disagree")
    return parts


def read_parts(rgba, thresholds, attack=False):
    parts = np.full(rgba.shape[:2], ".")
    height, width = parts.shape
    for y, x in zip(*np.nonzero(rgba[:, :, 3])):
        r, g, b = rgba[y, x, :3] / 255
        hue, sat, value = colorsys.rgb_to_hsv(r, g, b)
        hue *= 360
        head = y < height * .61
        hair = thresholds["hair"]
        skin = thresholds["skin"]
        silver = thresholds["silver"]
        blue = thresholds["blue"]
        belt = thresholds["belt"]
        if value < thresholds["dark_value"]:
            part = "K" if y >= height * .90 else "O"
        elif head and skin[0] <= hue <= skin[1] and sat <= skin[2] and value >= skin[3]:
            part = "F"
        elif head and hair[0] <= hue <= hair[1] and sat >= hair[2] and value >= hair[3]:
            part = "A" if y < height * .18 else "H"
        elif sat <= silver[0] and value >= silver[1]:
            if attack and x >= width * .75 and height * .35 <= y <= height * .67:
                part = "W"
            elif y >= height * .76:
                part = "L"
            else:
                part = "P" if x < width * .38 or x >= width * .66 else "C"
        elif belt[0] <= hue <= belt[1] and belt[2] <= value <= belt[3] and height * .60 <= y < height * .85:
            part = "B"
        elif blue[0] <= hue <= blue[1] and value > blue[2]:
            part = "S" if x < width * .27 or x > width * .82 else "T"
        elif head and r > b * 1.3 and value >= .54:
            part = "H" if g > r * .77 and sat > .4 else "F"
        elif value >= .55 and sat < .42:
            part = "L" if y >= height * .77 else "C"
        else:
            part = "O"
        parts[y, x] = part
    # Dark dots surrounded by skin near the front of the head are eyes.
    eyes = []
    for y, x in zip(*np.nonzero(parts == "O")):
        if height * .27 <= y < height * .55 and width * .52 <= x < width * .90:
            skin_neighbors = np.count_nonzero(parts[y - 1:y + 2, x - 1:x + 2] == "F")
            if skin_neighbors >= 4:
                eyes.append((int(skin_neighbors), int(x), int(y)))
    if eyes:
        _, x, y = max(eyes)
        parts[y, x] = "E"
        if y + 1 < height and parts[y + 1, x] == "O" and parts[y + 1, x - 1] == "F":
            parts[y + 1, x] = "E"
    return parts


def reduce_parts(parts):
    frame = np.full((16, 16), ".")
    for y in range(16):
        for x in range(16):
            block = list(parts[y * 2:y * 2 + 2, x * 2:x * 2 + 2].flat)
            material = sum(value not in (".", "O") for value in block)
            frame[y, x] = next(value for value in PRIORITY
                               if value in block and not (value == "O" and material >= 3))
    return frame


def template_score(frame, target, name):
    occupied = (target != ".") | (frame != ".")
    weights = np.array([WEIGHTS.get(part, 1) for part in target.flat]).reshape((16, 16))
    if name != "player_idle":
        weights[HEAD_ROWS:] = 1
    if "attack" in name:
        # The idle template has a scabbard rather than a drawn blade.
        occupied[7:10, 12:] = False
    return float(np.sum(weights * (frame == target) * occupied) / np.sum(weights * occupied))


def add_outline(frame):
    result = frame.copy()
    dark = {"O", "E", "B", "K"}
    for y, x in zip(*np.nonzero(frame != ".")):
        if frame[y, x] in dark:
            continue
        for dx, dy in grid.NEIGHBORS:
            xx, yy = x + dx, y + dy
            if 0 <= xx < 16 and 0 <= yy < 16 and frame[yy, xx] == ".":
                result[yy, xx] = "O"
    return result


def align_attack_head(frame):
    """Keep the head centered over the body when the blade widens the crop."""
    face_columns = np.nonzero(frame[4:9] == "F")[1]
    if not len(face_columns):
        return frame
    shift = min(3, max(0, 13 - int(face_columns.max())))
    if not shift:
        return frame
    result = frame.copy()
    result[:9, shift:] = frame[:9, :-shift]
    result[:9, :shift] = "."
    return result


def recognize(frame, target, name):
    result = frame.copy()
    attack = "attack" in name
    rows, cols = np.indices(result.shape)
    hair = (rows >= 2) & (rows < 9)
    face = (rows >= 5) & (rows <= 8) & (cols >= 9) & (cols <= 13)
    if np.count_nonzero((result == "H") & hair) < 14:
        result[(target == "H") & hair] = "H"
    # Warm highlights at the top of the head are hair rather than skin.
    top_hair = (rows >= 2) & (rows < 5) & (target == "H")
    result[top_hair & np.isin(result, ["F", "C", "P"])] = "H"
    if np.count_nonzero((result == "F") & face) < 8:
        result[(target == "F") & face] = "F"
    # Keep a single distinct strand, separated from the rest of the hair by dark edges.
    result[result == "A"] = "H"
    result[:2] = np.where(np.isin(target[:2], ["O", "A"]), target[:2], ".")
    result[2, 9] = "H"
    # Clear stray eye labels and put a 1-2px eye in the right-hand skin area.
    eye = (result == "E") & face
    choices = [tuple(pos) for pos in np.argwhere(eye)]
    result[result == "E"] = "O"
    if choices:
        y, x = min(choices, key=lambda point: abs(point[0] - 6) + abs(point[1] - 11))
        result[y, x] = "E"
        if (y + 1, x) in choices:
            result[y + 1, x] = "E"
    else:
        result[(target == "E") & face] = "E"
        result[6:8, 10] = "F"
        result[6, 12] = "F"
    result[(target == "O") & (rows == 9) & (cols >= 8)] = "O"
    for material, minimum in (("P", 4), ("C", 4), ("T", 4)):
        zone = (rows >= 9) & ((cols < 12) if attack else True)
        if np.count_nonzero((result == material) & zone) < minimum:
            result[(target == material) & zone] = material
    if not np.any((result == "B") & (rows >= 11)):
        result[target == "B"] = "B"
    if not attack and np.count_nonzero((result == "S") & (rows >= 11)) < 2:
        result[target == "S"] = "S"
    if not np.any(result[-1] != "."):
        result[-1] = target[-1]
    if name in {"player_idle", "player_walk", "player_attack"}:
        result[-1, np.isin(result[-1], ["L", "T"])] = "K"
    if attack:
        extension = result[:, 13:]
        extension[extension == "W"] = "."
        result[8, 11:16] = "W"
    return add_outline(result)


def evaluate(samples, agreement, name, spec, target, thresholds):
    if not agreement:
        return None, {}
    frames = []
    similarities = []
    attack = "attack" in name
    for i in range(len(spec["frames"])):
        pixels = samples[:, i * 32:(i + 1) * 32]
        if not pixels[:, :, 3].any():
            return None, {}
        frame = reduce_parts(read_parts(pixels, thresholds, attack))
        if attack:
            frame = align_attack_head(frame)
        similarities.append(template_score(frame, target, name))
        fitted = recognize(frame, target, name)
        frames.append(np.array([PART_SHADE[p] for p in fitted.flat], dtype=np.uint8).reshape((16, 16)))
    image = grid.to_png(np.array(frames))
    scores = grid.score_frames(np.array(frames), agreement, name)
    del scores["reference"]
    scores["template"] = float(np.mean(similarities))
    # Four equally weighted readings and a triple weight for the semantic layout.
    return image, scores
