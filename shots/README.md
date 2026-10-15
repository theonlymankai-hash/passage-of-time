# Shots — music-locked renders of the tree

A **shot** is a short clip where the seasons and the camera are authored
against the music, and rendered off the clock, frame by frame. The output is
frame-exact. No screen capture, no directory picker, nobody at the keyboard.

First shot: `reddit-v3` (2026-10-15), 27.2 s, 4:5 (1080×1350), 30 fps, for
r/GaussianSplatting. The user's brief: camera that zooms in and out on the
music "like people dancing around each other", seasons changing on the
phrases, moving from the first second, loops.

## Run it

```bash
# 1. author the timeline (musical grid + seasons + camera, per frame)
"/d/Projects/Sisi baby blue/.venv/Scripts/python.exe" gen_shot.py --name reddit-v3
# 2. sanity-check the camera path against the scan (writes out/plan_<name>.png)
"/d/Projects/Sisi baby blue/.venv/Scripts/python.exe" plan_view.py reddit-v3 0 4.6 9.3
# 3. serve the app + frame catcher  (launch.json "tree-render", port 3012)
python render_server.py 3012
# 4. preview stills, then the full render (headless Edge on the GPU, ~75 s)
powershell -File render.ps1 -Shot reddit-v3 -Out preview -Frames "0,138,279,558"
powershell -File render.ps1 -Shot reddit-v3 -Out reddit-v3
# 5. frames + the matching music cut -> MP4
bash encode.sh reddit-v3        # -> out/reddit-v3.mp4 (master, CRF 16)
```

For social, re-encode the master at CRF 21 with a 22 Mbps cap. Splat noise is
high-entropy, so CRF 16 comes out around 290 MB for 27 s, and Reddit
recompresses to 5–10 Mbps anyway.

## How the pieces fit

- `gen_shot.py` holds every musical decision. The page only plays its numbers
  (`f.phase / theta / dist / camY / tgtY / audio`, one value per frame).
- `index.html?shot=<name>`: skips the cover and the reveal, sets the canvas
  size, drives the season, beat pulse and camera from the JSON, and POSTs each
  frame. `&frames=a,b,c` renders stills only; `&from=N` resumes (see below).
- `render_server.py`: static server plus `/frame`, `/done`, `/log` (a
  headless JS error lands in `renders/<out>/ERROR.txt`).

## The music (reddit-v3)

Track `married-life-toms-mucenieks-piano.mp3`, **a piano cover by Toms
Mucenieks** of Giacchino's "Married Life" (Up). Credit both.

- Window: the 25 s with the most change, scored over the whole track (chroma
  novelty 0.40, dynamics 0.25, onsets 0.20, loudness 0.15). 29–54 s won with
  0.93; the next best scored 0.77. The cut then snaps to downbeats:
  30.093 → 57.307 s, 12 bars.
- Grid: the choreo detector's beats are half-beats (161 bpm). The real pulse
  is a 3/4 waltz at 80.75 bpm, so take every 2nd beat (the parity with the
  stronger onsets), then every 3rd for downbeats (the phase with the strongest
  first beat).
- Phrases: checkerboard novelty on the chroma self-similarity matrix. The
  strongest boundaries are at bars 4 and 8 (9.06 s, 18.23 s).

Seasons land on those boundaries: winter 0 → thaw 4.41 → summer 9.06 →
autumn 18.23 → dusk 22.73 → winter again at 27.21, which is frame 0.

## Gotchas, each one cost a render

1. **Phase must be `%5` before the shaders.** The timeline phase is
   cumulative (the year wraps, 4.6 → 9.6). Feed 7.15 raw and every season
   renders as night and snow.
2. **The usable ground is ONLY the mound (r < 4).** r 4–5 is a near-empty gap
   ring, and the east field is barely reconstructed. A portrait frame from
   d > ~6 puts its bottom edge into grey void. Wide shots therefore stay at
   d ≤ 6.0, with a higher, level camera.
3. **The west hedge (az ~200–340) starts at r ~5.5–6.** A wide camera there
   sits INSIDE it, and the frame fills with huge discs. Fix: an azimuth cap
   (5.4) eased in with a soft-min. Also on the west, the mound's scanned
   ground stops at r ~2.5, so wide shots there aim ~3° up.
   `plan_view.py` shows all of this in one picture. Look at it before
   rendering.
4. **Headless, not the Browser pane.** A hidden pane pauses
   `requestAnimationFrame`, and the splat loader stalls forever.
5. **`toDataURL`, not `toBlob`.** In a long headless run, toBlob's callback
   (it rides the compositor) simply never fires: the first full render
   stopped dead at frame 197. And retry each POST: a local POST dropped once
   in ~400 frames.
6. **Don't stitch resumed renders.** Replaying skipped frames gets close
   (34.5 dB PSNR on the overlap) but not identical, so there could be a pop at
   the seam. A full render is only ~75 s, so re-render in one pass.

## Verdicts

- v1: every frame night/snow (bug 1). Rejected.
- v2: seasons right, but grey void on wide shots and a blob storm at 4.6 s
  and 18.6 s (bugs 2–3). Rejected.
- v3: clean through 24 samples across the clip. Delivered 2026-10-15.
