"""Per-azimuth limits around the tree, from the baked points.

  bush_r  : nearest radius (beyond the canopy, r>4.6) where foliage stands at
            camera height — the camera must stay inside this or it sits IN a bush
  ground_r: how far scanned ground extends in that direction
Writes azimuth_limits.json (1-deg bins), used by gen_shot.py to clamp the dolly.
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(os.path.dirname(HERE), "assets")
C = json.load(open(os.path.join(A, "manifest.json")))["center"]

def load(name):
    raw = np.fromfile(os.path.join(A, name), dtype=np.uint8).reshape(-1, 24)
    xyz = raw[:, :12].copy().view("<f4").reshape(-1, 3)
    return xyz[raw[:, 15] > 40]

P = np.vstack([load("winter.bin"), load("leaves.bin")])
dx, dz = P[:, 0] - C[0], P[:, 2] - C[2]
r = np.hypot(dx, dz)
az = (np.degrees(np.arctan2(dx, dz)) + 360) % 360      # same convention as theta
y = P[:, 1]

BINS = 360; W = 6                                         # +-6 deg wedge
bush, ground = np.zeros(BINS), np.zeros(BINS)
for b in range(BINS):
    d = np.abs(((az - b) + 180) % 360 - 180) < W
    # foliage at camera height band (y 0.0..1.4), outside the canopy
    m = d & (r > 4.6) & (y > 0.0) & (y < 1.4)
    h, e = np.histogram(r[m], bins=np.arange(4.6, 16, 0.25))
    hit = np.nonzero(h > 60)[0]
    bush[b] = e[hit[0]] if len(hit) else 16.0
    g = d & (y < -0.45)
    hg, eg = np.histogram(r[g], bins=np.arange(0, 16, 0.25))
    ok = np.nonzero(hg > 150)[0]
    # last radius before the first gap in dense ground
    run = 0
    for k in range(len(hg)):
        if hg[k] > 150: run = eg[k + 1]
        elif run > 0: break
    ground[b] = run

json.dump(dict(bush_r=np.round(bush, 2).tolist(), ground_r=np.round(ground, 2).tolist()),
          open(os.path.join(HERE, "azimuth_limits.json"), "w"))
print(" az   bush_r  ground_r")
for b in range(0, 360, 15):
    print(f"{b:4d}   {bush[b]:5.2f}    {ground[b]:5.2f}")
