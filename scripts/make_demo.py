"""Render docs/demo/field-notes-demo.mp4 from REAL session data (no screen recorder here).

Every string on screen was produced by the app on 2026-10-11: walk-5 CLI output,
data/journals/walk_5.md, and `make offline-demo`. Waveform is the actual demo clip.
Paper-theme stills, 1280x720, 24 fps, H.264. No audio track (deliberate: quiet).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 24
PAPER, CARD, INK, MUTED, MOSS, RUST = (
    (244, 239, 227), (251, 248, 240), (31, 42, 31),
    (79, 90, 72), (47, 93, 52), (154, 63, 29),
)
ROOT = Path(__file__).resolve().parent.parent
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_B = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
HELV = "/System/Library/Fonts/Helvetica.ttc"
MENLO = "/System/Library/Fonts/Menlo.ttc"


def font(path, size, idx=0):
    return ImageFont.truetype(path, size, index=idx)


F_TITLE = font(GEORGIA_B, 92)
F_H = font(GEORGIA_B, 54)
F_BODY = font(GEORGIA, 34)
F_SMALL = font(GEORGIA, 28)
F_UI = font(HELV, 30)
F_MONO = font(MENLO, 26)


def card(draw_extra=None, bg=PAPER):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    if draw_extra:
        draw_extra(d)
    return img


def wrap(d, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def text_block(frames, lines, x=140, y=150, gap=8, hold_s=1.0):
    img = card()
    d = ImageDraw.Draw(img)
    yy = y
    for (txt, fnt, col) in lines:
        for ln in wrap(d, txt, fnt, W - 2 * x):
            d.text((x, yy), ln, font=fnt, fill=col)
            yy += fnt.size + gap
    frames += [img] * int(FPS * hold_s)
    return frames


# --- scene 1: title ---
frames = []
img = card()
d = ImageDraw.Draw(img)
d.text((140, 220), "Field Notes", font=F_TITLE, fill=INK)
d.text((140, 330), "an offline bird journal", font=font(GEORGIA, 44), fill=MUTED)
d.text((140, 420), "record outside · recap at home · Touch Grass",
       font=F_UI, fill=MOSS)
frames += [img] * int(FPS * 3)

# --- scene 2: real terminal output (walk 5, 2026-10-11) ---
frames = text_block(frames, [
    ("$ fieldnotes analyze blackbird-southern-finland.ogg --lat 60.17 --lon 24.94 --date 2025-05-15", F_MONO, MUTED),
    ("walk 5: 4 detections in 8 windows (2 gated as silence)", F_MONO, INK),
    ("0.0s  Eurasian Blackbird  conf=0.78  [first_ever]", F_MONO, INK),
    ("6.0s  Eurasian Blackbird  conf=1.00  [repeat]", F_MONO, INK),
    ("12.0s  Eurasian Blackbird  conf=0.88  [repeat]", F_MONO, INK),
    ("21.0s  Eurasian Blackbird  conf=1.00  [repeat]", F_MONO, INK),
], hold_s=7.0)

# --- scene 3: real waveform + detection windows ---
audio, sr = sf.read(str(ROOT / "docs/demo/blackbird-southern-finland.ogg"), always_2d=True)
mono = audio.mean(axis=1)
cols = 1160
step = max(1, len(mono) // cols)
env = np.abs(mono[: cols * step].reshape(cols, step)).max(axis=1)
env = env / (env.max() or 1)


def wave(d):
    d.text((60, 40), "24.8 seconds · 8 listening windows · 4 with detections",
           font=F_UI, fill=MUTED)
    x0, x1, ym, amp = 60, 1220, 400, 260
    dur = len(mono) / sr
    for i, (s, e) in enumerate([(0, 3), (6, 9), (12, 15), (21, 24)]):
        d.rectangle([x0 + s / dur * (x1 - x0), ym - amp - 20,
                     x0 + e / dur * (x1 - x0), ym + amp + 20],
                    fill=(47, 93, 52, 40), outline=MOSS, width=2)
    for i in range(9):
        x = x0 + i * 3 / dur * (x1 - x0)
        d.line([x, ym - amp - 20, x, ym + amp + 20], fill=(217, 208, 188), width=1)
    for i, v in enumerate(env):
        x = x0 + i
        d.line([x, ym - v * amp, x, ym + v * amp], fill=INK, width=1)
    d.text((60, 620), "0s", font=F_UI, fill=MUTED)
    d.text((1150, 620), "25s", font=F_UI, fill=MUTED)


frames += [card(wave)] * int(FPS * 9)

# --- scene 4: specimen card ---
frames = text_block(frames, [
    ("Eurasian Blackbird", F_H, INK),
    ("Turdus merula", font(GEORGIA, 36), MUTED),
    ("confident · 1.00 · detected in 4 of 8 listening windows", F_BODY, INK),
    ("[ new to my list ]", F_BODY, RUST),
], hold_s=6.0)

# --- scene 5: real journal (walk 5, template fallback) ---
journal = (ROOT / "data/journals/walk_5.md").read_text()
frames = text_block(frames, [(journal, F_SMALL, INK)], hold_s=12.0)

# --- scene 6: real offline-demo output ---
frames = text_block(frames, [
    ("$ make offline-demo", F_MONO, MUTED),
    ("analyzed 1 windows -> 2 detections (Lesser Redpoll, Common Redpoll)", F_MONO, INK),
    ("journal [template:…] (425 chars), external connection attempts: 0", F_MONO, INK),
    ("OFFLINE DEMO OK", font(MENLO, 34), MOSS),
], hold_s=6.0)

# --- scene 7: closing ---
img = card()
d = ImageDraw.Draw(img)
d.text((140, 300), "Done here? Close the laptop.", font=font(GEORGIA, 54), fill=INK)
d.text((140, 380), "The birds are outside.", font=font(GEORGIA, 54), fill=MOSS)
frames += [img] * int(FPS * 4)

out = ROOT / "docs/demo/field-notes-demo.mp4"
proc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
     "-movflags", "+faststart", str(out)],
    stdin=subprocess.PIPE,
)
for f in frames:
    proc.stdin.write(f.tobytes())
proc.stdin.close()
proc.wait()
n = len(frames)
print(f"wrote {out} ({out.stat().st_size // 1024} KB, {n // FPS}s, {n} frames)")
