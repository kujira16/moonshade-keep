# Generates js/level.js. Edit the sections below or edit level.js directly.
W, H = 200, 16
g = [['.'] * W for _ in range(H)]

def fill(x0, x1, y0, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < W and 0 <= y < H:
                g[y][x] = c

def put(x, y, c): g[y][x] = c

# --- ground everywhere, then carve pits
fill(0, W - 1, 14, 15, '#')
for a, b in [(30, 33), (84, 87), (128, 131)]:
    fill(a, b, 14, 15, '.')

# --- section 1: courtyard (0-33)
put(3, 12, 'P')
put(8, 12, 'C'); put(16, 12, 'C'); put(24, 12, 'C')
put(14, 6, 'B'); put(27, 12, 'S')
fill(31, 32, 11, 11, '=')

# --- castle body (36-199): ceiling + back wall
fill(36, W - 1, 0, 1, '#')
fill(36, W - 1, 2, 13, 'b')
fill(36, 37, 2, 11, '#')          # entrance wall (door below)
fill(34, 35, 2, 3, '#')
for x in (44, 58, 72, 96, 110, 140, 154):
    put(x, 3, 'W')
for x in (50, 66, 104, 118, 148):
    for y in range(2, 14):
        if g[y][x] == 'b': g[y][x] = 'I'

# --- section 2: first hall (38-83)
fill(40, 41, 13, 13, '#'); fill(42, 43, 12, 13, '#')
fill(48, 53, 10, 10, '='); put(50, 8, 'C')
fill(56, 61, 7, 7, '='); put(58, 5, 'C')
put(55, 12, 'S'); put(70, 12, 'S'); put(76, 6, 'G')
fill(63, 65, 13, 13, '^')
put(46, 12, 'C'); put(68, 12, 'C'); put(80, 12, 'C')
fill(85, 86, 11, 11, '=')

# --- section 3: second hall, raised walkway (88-127)
fill(92, 99, 11, 13, '#')
fill(100, 103, 13, 13, '^')
fill(104, 111, 11, 13, '#')
fill(112, 114, 13, 13, '^')
fill(115, 120, 9, 13, '#')
fill(121, 124, 11, 11, '=')
put(94, 9, 'C'); put(107, 9, 'C'); put(118, 7, 'C')
put(97, 4, 'B'); put(110, 4, 'B'); put(122, 5, 'B')
put(108, 9, 'S'); put(125, 12, 'S')
fill(129, 130, 11, 11, '=')
put(89, 12, 'R')                    # mid checkpoint

# --- section 4: corridor to boss (132-179)
put(136, 12, 'C'); put(150, 12, 'C'); put(164, 12, 'C')
put(138, 6, 'G'); put(146, 12, 'S'); put(156, 12, 'S'); put(160, 5, 'B')
fill(142, 146, 10, 10, '='); fill(152, 156, 8, 8, '=')
put(170, 12, 'R')                   # checkpoint
fill(178, 179, 2, 9, "#")           # boss gate lintel

# --- section 5: boss arena (180-199)
fill(198, 199, 2, 13, '#')
fill(182, 184, 10, 10, '='); fill(193, 195, 10, 10, '=')
put(189, 3, 'K')

rows = [''.join(r) for r in g]
with open('js/level.js', 'w') as f:
    f.write('// 1 tile = 8px. 16 rows x %d cols. Regenerate with tools/make_level.py\n' % W)
    f.write('// # wall  = ledge  ^ spikes  b back wall  I pillar  W window\n')
    f.write('// P player  C candle  B bat  S skeleton  G ghost  K boss  R checkpoint\n')
    f.write('window.LEVEL1 = {\n  arenaX: 179,\n  map: [\n')
    for r in rows: f.write('    "%s",\n' % r)
    f.write('  ]\n};\n')
for r in rows: print(r)
