"""Plan-view map of the scan with a shot's camera path on it.
    python plan_view.py reddit-v2 [t1 t2 ...]   (times to mark)
grey = ground (y<-0.45), green = foliage at camera height (0<y<1.4),
path coloured blue->red over time, marked times as white circles.
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(os.path.dirname(HERE), "assets")
C = json.load(open(os.path.join(A, "manifest.json")))["center"]
def load(name):
    raw = np.fromfile(os.path.join(A, name), dtype=np.uint8).reshape(-1, 24)
    xyz = raw[:, :12].copy().view("<f4").reshape(-1, 3)
    return xyz[raw[:, 15] > 40]
P = np.vstack([load("winter.bin"), load("leaves.bin")])
EXT, PX = 11.0, 800                       # +-11 units, 800 px
def to_px(x, z):
    return ((x - C[0] + EXT) / (2 * EXT) * PX, (z - C[2] + EXT) / (2 * EXT) * PX)
def hist(m):
    h, _, _ = np.histogram2d(P[m, 0] - C[0], P[m, 2] - C[2], bins=PX, range=[[-EXT, EXT], [-EXT, EXT]])
    return h.T
g = hist(P[:, 1] < -0.45); f = hist((P[:, 1] > 0.0) & (P[:, 1] < 1.4))
img = np.zeros((PX, PX, 3), np.float32)
img += (np.clip(np.log1p(g) / 3.0, 0, 1) * 0.55)[..., None]
fl = np.clip(np.log1p(f) / 2.5, 0, 1)
img[..., 1] = np.maximum(img[..., 1], fl * 0.9); img[..., 0] *= (1 - fl * 0.6); img[..., 2] *= (1 - fl * 0.6)
im = Image.fromarray((img * 255).astype(np.uint8)); d = ImageDraw.Draw(im)
for rr in (2, 4, 6, 8, 10):              # radius rings
    c0 = to_px(C[0] - rr, C[2] - rr); c1 = to_px(C[0] + rr, C[2] + rr)
    d.ellipse([c0, c1], outline=(70, 70, 90))
    d.text(to_px(C[0] + rr * 0.7071, C[2] - rr * 0.7071), f"r{rr}", fill=(140, 140, 170))
S = json.load(open(os.path.join(HERE, sys.argv[1] + ".json"))); F = S["f"]; N = S["frames"]
pts = []
for i in range(N):
    th, r = F["theta"][i], F["dist"][i]
    pts.append(to_px(C[0] + r * math.sin(th), C[2] + r * math.cos(th)))
for i in range(N - 1):
    u = i / N; d.line([pts[i], pts[i + 1]], fill=(int(60 + 195 * u), 80, int(255 - 195 * u)), width=2)
for t in map(float, sys.argv[2:]):
    i = min(int(t * S["fps"]), N - 1); x, z = pts[i]
    d.ellipse([x - 7, z - 7, x + 7, z + 7], outline=(255, 255, 255), width=2); d.text((x + 9, z - 6), f"{t}s", fill=(255, 255, 255))
d.text((8, 8), f"{sys.argv[1]}  grey=ground  green=foliage@cam height  path blue->red", fill=(220, 220, 220))
out = os.path.join(HERE, "out", f"plan_{sys.argv[1]}.png"); im.save(out); print(out)
