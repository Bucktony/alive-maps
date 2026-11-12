"""Step 2 of a city build: tree cover from Meta / WRI Global Canopy Height (1 m, CC BY 4.0).

These cities have no street-tree census in the build, so tree cover comes from satellite-derived canopy height.
Usage: python3 canopy_city.py <city> <folder with the .tif tiles> <canopy.npz>
       python3 canopy_city.py <city>            prints the tile addresses to download first
Tiles: https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/chm/<quadkey>.tif
Needs rasterio, mercantile and numpy.
Output: share of each 4 x 4 pixel block (about 3.4 m on the ground) with canopy 3 m or taller, as 0 to 255.
"""
import sys, math, numpy as np, mercantile
from cities import CITIES
BB = CITIES[sys.argv[1]]['bb']
QUADS = sorted(mercantile.quadkey(t) for t in mercantile.tiles(BB[1], BB[0], BB[3], BB[2], 9))
if len(sys.argv) < 4:
    for q in QUADS: print('https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/alsgedi_global_v6_float/chm/%s.tif' % q)
    sys.exit()
import rasterio
from rasterio.windows import Window
R = 6378137.0
def mx(lon): return math.radians(lon) * R
def my(lat): return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * R
RES = 1.1943285669558747; F = 4; MINH = 3
x0, x1, y0, y1 = mx(BB[1]), mx(BB[3]), my(BB[0]), my(BB[2])
W = int(math.ceil((x1 - x0) / (RES * F))); H = int(math.ceil((y1 - y0) / (RES * F)))
out = np.zeros((H, W), dtype=np.uint8)
for q in QUADS:
    with rasterio.open('%s/%s.tif' % (sys.argv[2], q)) as r:
        b = r.bounds
        # pixel range of this tile that falls in the box, snapped to the output grid
        c0 = max(0, int(round((max(b.left, x0) - x0) / (RES * F)))); c1 = min(W, int(round((min(b.right, x1) - x0) / (RES * F))))
        r0 = max(0, int(round((y1 - min(b.top, y1)) / (RES * F)))); r1 = min(H, int(round((y1 - max(b.bottom, y0)) / (RES * F))))
        if c1 <= c0 or r1 <= r0: continue
        px0 = int(round((x0 + c0 * RES * F - b.left) / RES)); py0 = int(round((b.top - (y1 - r0 * RES * F)) / RES))
        for rr in range(r0, r1, 512):
            n = min(512, r1 - rr)
            win = Window(px0, py0 + (rr - r0) * F, (c1 - c0) * F, n * F)
            a = r.read(1, window=win, boundless=True, fill_value=0)
            m = (a >= MINH) & (a < 255)
            out[rr:rr + n, c0:c1] = (m.reshape(n, F, c1 - c0, F).mean(axis=(1, 3)) * 255).astype(np.uint8)
        print(q, 'rows', r0, r1, 'cols', c0, c1, flush=True)
np.savez_compressed(sys.argv[3], canopy=out, x0=x0, y1=y1, res=RES * F)
print('grid', out.shape, 'mean canopy share %.3f' % (out.mean() / 255))
