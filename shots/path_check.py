"""Measure, from the baked points, where a camera path goes wrong.

For each frame of a shot: (1) obstruction — points just in front of the lens
(those render as huge discs); (2) floor — whether the bottom edge of the frame
lands on scanned ground or on the grey void beyond it. Also builds, per
azimuth, the safe maximum distance, which gen_shot.py clamps the dolly to.
    python path_check.py reddit-v2
"""
import json, math, os, sys
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(os.path.dirname(HERE), "assets")
man = json.load(open(os.path.join(A, "manifest.json")))
C = man["center"]

def load(name):
    raw = np.fromfile(os.path.join(A, name), dtype=np.uint8).reshape(-1, 24)
    xyz = raw[:, :12].copy().view("<f4").reshape(-1, 3)
    a = raw[:, 15].astype(np.float32) / 255
    return xyz[a > 0.15]

P = np.vstack([load("winter.bin"), load("leaves.bin")])
tree = cKDTree(P)
G = P[P[:, 1] < -0.45]                         # ground band (ground y ~ -0.85)
gtree = cKDTree(G[:, [0, 2]])
FOV, ASP = math.radians(50), 1080 / 1350

def frame_issues(cam, tgt):
    f = tgt - cam; f /= np.linalg.norm(f)
    # obstruction: points within 1.4 ahead, inside a 30deg cone
    idx = tree.query_ball_point(cam, 1.4)
    obs = 0
    if idx:
        v = P[idx] - cam; d = np.linalg.norm(v, axis=1)
        obs = int(((v @ f) > d * math.cos(math.radians(30))).sum())
    # floor: bottom edge rays (centre + corners) -> hit y=-0.85 -> ground density there
    right = np.cross(f, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, f)
    th = math.tan(FOV / 2); thx = th * ASP
    voids = 0
    for sx in (-0.9, 0, 0.9):
        r = f - up * th * 0.97 + right * thx * sx
        if r[1] >= -1e-3: continue
        s = (-0.85 - cam[1]) / r[1]
        hit = cam + r * s
        if len(gtree.query_ball_point(hit[[0, 2]], 0.35)) < 25:
            voids += 1
    return obs, voids

if __name__ == "__main__":
    S = json.load(open(os.path.join(HERE, sys.argv[1] + ".json")))
    F = S["f"]
    bad = []
    for i in range(0, S["frames"], 3):
        th, r = F["theta"][i], F["dist"][i]
        cam = np.array([C[0] + r * math.sin(th), F["camY"][i], C[2] + r * math.cos(th)])
        tgt = np.array([C[0], F["tgtY"][i], C[2]])
        o, v = frame_issues(cam, tgt)
        if o > 40 or v:
            bad.append((i, i / S["fps"], math.degrees(th) % 360, r, o, v))
    print(f"{len(bad)} of {S['frames']//3} sampled frames have issues")
    for b in bad[:60]:
        print(f"  f{b[0]:4d} t={b[1]:5.2f}s az={b[2]:5.1f} d={b[3]:4.2f}  obstruct={b[4]:4d}  void_edges={b[5]}")
