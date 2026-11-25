// 1 tile = 8px. 16 rows x 200 cols. Regenerate with tools/make_level.py
// # wall  = ledge  ^ spikes  b back wall  I pillar  W window
// P player  C candle  B bat  S skeleton  G ghost  K boss  R checkpoint
window.LEVEL1 = {
  arenaX: 179,
  map: [
    "....................................####################################################################################################################################################################",
    "....................................####################################################################################################################################################################",
    "..................................####bbbbbbbbbbbbIbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "..................................####bbbbbbWbbbbbIbbbbbbbWbbbbbbbIbbbbbWbbbbbbbbbbbbbbbbbbbbbbbWbbbbbbbIbbbbbWbbbbbbbIbbbbbbbbbbbbbbbbbbbbbWbbbbbbbIbbbbbWbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbKbbbbbbbb##",
    "....................................##bbbbbbbbbbbbIbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbBbbbbbbIbbbbbBbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "....................................##bbbbbbbbbbbbIbbbbbbbCbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbIbbbBbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbBbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "..............B.....................##bbbbbbbbbbbbIbbbbbbbbbbbbbbbIbbbbbbbbbGbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbGbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "....................................##bbbbbbbbbbbbIbbbbb======bbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "....................................##bbbbbbbbbbbbCbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbCbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbb=====bbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "....................................##bbbbbbbbbbbbIbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbCbbbbbbbbbIbbCSbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##bbbbbbbbbbbbbbbbbb##",
    "....................................##bbbbbbbbbb======bbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbb######bbbbbbbbbbbbbbbbbbbbb=====bIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb===bbbbbbbb===bb##",
    "...............................==...##bbbbbbbbbbbbIbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbb==bbbbb########bbbb########bbb######====bbbb==bbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##",
    "...P....C.......C.......C..S........bbbbbb##bbCbbbIbbbbSbbbbbbbbbbIbCbSbbbbbbbbbCbbbbbbbbRbb########bbbb########bbb######bbbbSbbbbbbbbbbCbbbbbbbbbSbIbCbbbbbSbbbbbbbCbbbbbRbbbbbbbbbbbbbbbbbbbbbbbbbbb##",
    "....................................bbbb####bbbbbbIbbbbbbbbbbbb^^^Ibbbbbbbbbbbbbbbbbbbbbbbbb########^^^^########^^^######bbbbbbbbbbbbbbbbbbbbbbbbbbbIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb##",
    "##############################....##################################################....########################################....####################################################################",
    "##############################....##################################################....########################################....####################################################################",
  ]
};
