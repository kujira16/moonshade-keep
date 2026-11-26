"""Stamp the knight's small 32px landmarks using frame-local coordinates."""

import numpy as np


PAULDRON = np.array([
    # 丸い肩当て：上が丸いドーム形。縁を一番明るい色で光らせ、下側は影
    [0, 0, 4, 4, 0, 0],
    [0, 4, 1, 1, 4, 0],
    [4, 1, 1, 2, 2, 4],
    [4, 1, 2, 2, 2, 4],
    [4, 2, 2, 2, 3, 4],
    [0, 4, 4, 4, 4, 0],
], dtype=np.uint8)
EYE = np.array([[1, 4], [4, 4], [4, 4]], dtype=np.uint8)


def hair_points(strokes):
    for x, y, length in strokes:
        for i in range(length):
            yield y + i, x + i
            if i:
                yield y + i - 1, x + i


def shoulders(details):
    # 奥の肩当ては体に隠れる前提で描かない（胸の上に丸が2つ並ぶと、ボタンや目に見えるため）
    x, y = details["pauldron"]
    yield np.s_[y - 3:y + 3, x - 3:x + 3], PAULDRON


def stamp(frame, details):
    result = np.array(frame, dtype=np.uint8, copy=True)
    if result.shape != (32, 32):
        raise ValueError("Knight detail stamps require a 32x32 indexed frame")
    for y, x in hair_points(details["hair_strokes"]):
        result[y, x] = 2
    left, right, y = details["fringe"]
    result[y, left:right + 1] = 2

    # Erase the earlier eye before painting the skin gap and the relocated eye.
    result[12:15, 22:24] = 2
    x, y = details["eye"]
    result[y:y + 3, x + 2:x + 4] = 2
    result[y:y + 3, x:x + 2] = EYE

    left, right, y = details["chin"]
    result[y, left:right + 1] = 4
    for region, mask in shoulders(details):
        panel = result[region]
        if panel.shape != mask.shape:
            raise ValueError("Knight pauldron stamp extends beyond the frame")
        panel[mask != 0] = mask[mask != 0]
    return result


def has_stamps(frame, details):
    x, y = details["eye"]
    if not (np.array_equal(frame[y:y + 3, x:x + 2], EYE)
            and np.all(frame[y:y + 3, x + 2:x + 4] == 2)):
        return False
    left, right, y = details["chin"]
    if not np.all(frame[y, left:right + 1] == 4):
        return False
    for region, mask in shoulders(details):
        panel = frame[region]
        if panel.shape != mask.shape or not np.array_equal(panel[mask != 0], mask[mask != 0]):
            return False
    left, right, y = details["fringe"]
    return (np.all(frame[y, left:right + 1] == 2)
            and all(frame[y, x] == 2 for y, x in hair_points(details["hair_strokes"])))
