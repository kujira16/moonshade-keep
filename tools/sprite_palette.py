"""The game palette, with the original PNG colors accepted on input."""

GREEN = ((224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32))
LEGACY_GREEN = ((155, 188, 15), (139, 172, 15), (48, 98, 48), (15, 56, 15))
SHADE_BY_RGB = {rgb: i for palette in (LEGACY_GREEN, GREEN)
                for i, rgb in enumerate(palette, 1)}
