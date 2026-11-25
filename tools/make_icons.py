from PIL import Image, ImageDraw
from sprite_palette import GREEN as P
def icon(size):
    s = 32; im = Image.new("RGB", (s, s), P[3]); d = ImageDraw.Draw(im)
    d.ellipse([16, 4, 27, 15], fill=P[0]); d.rectangle([19,7,20,8], fill=P[1]); d.rectangle([23,11,24,12], fill=P[1])
    for x0,x1,top in [(3,8,12),(9,22,18),(23,28,10),(13,17,13)]:
        d.rectangle([x0, top, x1, 28], fill=P[2])
        for bx in range(x0, x1+1, 2): d.point((bx, top-1), fill=P[2])
    for x,y in [(5,15),(25,13),(15,16),(12,21),(19,21)]: d.rectangle([x,y,x,y+1], fill=P[1])
    d.rectangle([0,28,31,31], fill=P[2]); d.line([0,28,31,28], fill=P[1])
    return im.resize((size,size), Image.NEAREST)
icon(192).save("icons/icon-192.png"); icon(512).save("icons/icon-512.png")
