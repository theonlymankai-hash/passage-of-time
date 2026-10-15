"""Choreograph a music-locked shot of the tree and write it as per-frame data.

    python gen_shot.py [--name reddit-v1] [--w 1080 --h 1350 --fps 30]

The page (index.html?shot=<name>) only PLAYS these numbers; every musical
decision lives here so a cut can be re-timed or re-styled without touching
the renderer.

Musical grid comes from the existing choreo beat list (half-beat detector,
161 bpm) reduced to the real waltz pulse (80.8 bpm, 3/4). The cut starts on a
downbeat and runs exactly BARS bars, so the last frame lands on the next
downbeat and both the seasons and the camera close into a loop.

Seasons land on the structural boundaries measured inside this window
(chroma self-similarity novelty, strongest at bars 4 and 8):
    bar 0 winter · bar 2 thaw->spring · bar 4 summer · bar 8 autumn ·
    bar 10 dusk/leaf-fall -> winter by bar 12 (== bar 0).

Camera = a dance partner circling the tree: integer turns (loops), a lilting
step on every beat (strongest on ONE), in/out every bar that arrives on the
downbeat and is WIDE on each season change, waltz rise-and-fall per bar.
"""
import argparse, json, math, os
import numpy as np, librosa

AUDIO = r"D:\CLAUDE\TreeSeasons\music\married-life-toms-mucenieks-piano.mp3"
CHOREO = r"D:\CLAUDE\TreeSeasons\assets\choreo\married-life.json"
HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--name", default="reddit-v1")
ap.add_argument("--start", type=float, default=29.0, help="cut starts at the first downbeat at/after this")
ap.add_argument("--bars", type=int, default=12)
ap.add_argument("--w", type=int, default=1080)
ap.add_argument("--h", type=int, default=1350)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--turns", type=float, default=2.0)
a = ap.parse_args()

# ---- musical grid ----------------------------------------------------------
y, sr = librosa.load(AUDIO, sr=22050, mono=True)
hop = 512
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
def strength(t):
    i = int(t * sr / hop)
    return onset[max(i - 2, 0):i + 3].max()

half = np.array(json.load(open(CHOREO))["beats"])
w = half[(half >= a.start - 6) & (half <= a.start + a.bars * 2.4 + 8)]
par = [np.mean([strength(t) for t in w[p::2]]) for p in (0, 1)]
q = w[int(np.argmax(par))::2]                       # real quarter pulse
bph = [np.mean([strength(t) for t in q[p::3]]) for p in range(3)]
qi0 = int(np.argmax(bph))
down_all = q[qi0::3]
d0 = int(np.argmax(down_all >= a.start - 1e-6))
D = down_all[d0:d0 + a.bars + 1]                    # bars 0..BARS
assert len(D) == a.bars + 1, "track too short for that many bars"
T0, DUR = float(D[0]), float(D[-1] - D[0])
Q = q[(q >= T0 - 1e-6) & (q < D[-1] - 1e-6)]
down_set = set(np.round(D, 4))
Dl, Ql = D - T0, Q - T0                               # local times

N = int(round(DUR * a.fps))
T = np.arange(N) / a.fps

# musical time: bar index, piecewise-linear between measured downbeats
m = np.interp(T, Dl, np.arange(len(Dl)))

# ---- seasons (cumulative phase; the app takes %5) -------------------------
# (bar, phase) — the change happens over ~half a bar AFTER each boundary, then
# the season keeps drifting so nothing ever sits still.
P0 = 4.45
SEASON = [  # bar, phase at that bar, transition length in bars
    (0.0, P0,          0.0),
    (2.0, P0 + 0.25,   0.0),    # winter drift until the thaw
    (2.6, 5.95,        0.6),    # thaw -> spring on the bar-2 boundary
    (4.0, 6.55,        0.0),    # spring grows
    (4.55, 7.15,       0.55),   # SUMMER lands on phrase B
    (8.0, 7.85,        0.0),    # summer: the long hold, warming
    (8.5, 8.15,        0.5),    # AUTUMN lands on phrase C
    (10.0, 8.50,       0.0),
    (10.5, 8.78,       0.5),    # dusk, leaves falling
    (11.0, 9.30,       0.0),
    (12.0, P0 + 5.0,   0.0),    # winter again == frame 0
]
def phase_at(mm):
    for (b0, p0, _), (b1, p1, tr) in zip(SEASON, SEASON[1:]):
        if b0 <= mm <= b1:
            u = (mm - b0) / max(b1 - b0, 1e-9)
            if tr > 0:                       # fast eased change (smootherstep)
                u = u * u * u * (u * (u * 6 - 15) + 10)
            return p0 + (p1 - p0) * u
    return SEASON[-1][1]
phase = np.array([phase_at(x) for x in m])

# ---- camera ----------------------------------------------------------------
# dolly: horizontal distance per bar, cosine-eased so each in/out ARRIVES on
# the downbeat. Wide on every season change, pushed in between.
DOLLY = [7.8, 4.6, 8.0, 4.4, 9.4, 4.8, 3.7, 5.4, 9.6, 4.4, 7.4, 4.8, 7.8]
def ease_keys(keys, mm):
    i = min(int(mm), len(keys) - 2); u = mm - i
    u = 0.5 - 0.5 * math.cos(math.pi * u)
    return keys[i] + (keys[i + 1] - keys[i]) * u
dist = np.array([ease_keys(DOLLY, x) for x in m])
near = np.clip((9.6 - dist) / (9.6 - 3.7), 0, 1)       # 0 wide .. 1 close

# waltz rise-and-fall: lowest on ONE, rises through two-three
frac = m - np.floor(m)
bob = 0.5 - 0.5 * np.cos(2 * np.pi * frac)
cam_y = 0.95 - 0.55 * near + 0.16 * bob                # eye level, lower when close
tgt_y = 0.55 + 0.32 * near                             # close = look up into the crown

# orbit: a step on every beat (alpha pulse, strongest on ONE), integrated and
# scaled to an exact number of turns so the loop closes
tau = 0.20
omega = np.ones(N)
for qt in Ql:
    amp = 1.1 if round(qt + T0, 4) in down_set else 0.45
    s = (T - qt) / tau
    omega += np.where(s > 0, amp * s * np.exp(1 - s), 0.0)
ang = np.concatenate([[0.0], np.cumsum(omega[:-1])])
ang = ang / (ang[-1] + omega[-1]) * (2 * math.pi * a.turns)
THETA0 = math.atan2(6.5, 8.0)                          # the authored front
theta = THETA0 - ang                                   # same direction as autoRotate

# beat envelope -> the scene's own audio pulse (leaves, sky, snow kick)
aud = np.zeros(N)
for qt in Ql:
    amp = 1.0 if round(qt + T0, 4) in down_set else 0.55
    dt = T - qt
    aud = np.maximum(aud, np.where(dt >= 0, amp * np.exp(-dt * 6.0), 0.0))
aud *= 0.45

out = dict(
    name=a.name, w=a.w, h=a.h, fps=a.fps, frames=N, dur=round(DUR, 4),
    audio=dict(file=os.path.basename(AUDIO), t0=round(T0, 4), t1=round(float(D[-1]), 4)),
    grid=dict(downbeats=[round(x, 3) for x in Dl], quarters=[round(x, 3) for x in Ql],
              bpm=round(60 / float(np.median(np.diff(Q))), 2)),
    seasons=[dict(bar=b, t=round(float(np.interp(b, np.arange(len(Dl)), Dl)), 3), phase=p)
             for b, p, _ in SEASON],
    dolly=DOLLY, turns=a.turns,
    f=dict(phase=np.round(phase, 4).tolist(), theta=np.round(theta, 5).tolist(),
           dist=np.round(dist, 4).tolist(), camY=np.round(cam_y, 4).tolist(),
           tgtY=np.round(tgt_y, 4).tolist(), audio=np.round(aud, 4).tolist()),
)
path = os.path.join(HERE, a.name + ".json")
json.dump(out, open(path, "w"))
print(f"{path}\n  cut {T0:.3f}->{D[-1]:.3f}s = {DUR:.3f}s, {N} frames @ {a.fps}fps, "
      f"{a.w}x{a.h}, {out['grid']['bpm']} bpm")
print("  downbeats:", " ".join(f"{x:.2f}" for x in Dl))
for s in out["seasons"]:
    print(f"    bar {s['bar']:>4}  t={s['t']:6.2f}s  phase {s['phase']:.2f}")
