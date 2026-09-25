#!/usr/bin/env python3
"""Render the dependency-chain demo GIF from a captured run.

Input is `demo-events.json` -- the founder-facing event stream from a real run
against a live Floci, the same file the site's live board replays. Rendering it
here rather than screen-recording the browser keeps the asset reproducible: the
GIF is a pure function of the captured events plus the design tokens below, so
re-running this script after a palette change regenerates a matching asset.

Usage:  python3 docs/assets/render-demo-gif.py
Writes: docs/assets/demo-dependency-chain.gif

Requires Pillow. Everything else is stdlib.
"""

import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
EVENTS = HERE / "demo-events.json"
OUT = HERE / "demo-dependency-chain.gif"

# Design tokens -- kept in sync with the `:root` block in docs/index.html.
BG = "#fafafa"
FG = "#0a0a0a"
MUTED = "#666666"
CARD_BG = "#ffffff"
BORDER = "#ebebeb"
ACCENT = "#dc2626"
ACCENT_FG = "#ffffff"
PASS_BG = "#fef2f2"
PASS_FG = "#b91c1c"
WORKING_BG = "#f0f0f0"
WORKING_FG = "#525252"
WINDOW_CHROME = "#f0f0f0"
DOT_IDLE = "#d4d4d4"
RADIUS_CARD = 20

# Render at 2x and downsample, so the GIF's 256-colour palette still gets
# antialiased edges on the rounded corners and text.
S = 2
W, H = 900, 452

PROMPT = "When someone uploads a photo, resize it, then send them a confirmation email."
REPLY = "That needs three things. Setting them up and verifying each one:"

FONT_DIR = pathlib.Path("/System/Library/Fonts/Supplemental")


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    path = FONT_DIR / name
    if path.exists():
        return ImageFont.truetype(str(path), size * S)
    return ImageFont.load_default(size * S)


F_BODY = font(14)
F_BODY_B = font(14, bold=True)
F_SMALL = font(12)
F_PILL = font(11, bold=True)
F_CHROME = font(12)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def pill(draw, x, y, text, bg, fg):
    """Draw a right-edge-anchored status pill; returns its left edge."""
    pad = 9 * S
    w = draw.textlength(text, font=F_PILL) + pad * 2
    h = 20 * S
    draw.rounded_rectangle([x - w, y, x, y + h], radius=h // 2, fill=bg)
    draw.text((x - w + pad, y + 4 * S), text, font=F_PILL, fill=fg)
    return x - w


def render(rows):
    """One frame. `rows` is the board state: a list of capability dicts."""
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)

    m = 20 * S
    win = [m, m, W * S - m, H * S - m]
    d.rounded_rectangle(win, radius=RADIUS_CARD * S, fill=CARD_BG, outline=BORDER, width=S)

    # Title bar.
    chrome_h = 40 * S
    d.rounded_rectangle(
        [win[0], win[1], win[2], win[1] + chrome_h + RADIUS_CARD * S],
        radius=RADIUS_CARD * S,
        fill=WINDOW_CHROME,
    )
    d.rectangle([win[0], win[1] + chrome_h, win[2], win[1] + chrome_h + S], fill=BORDER)
    d.rectangle(
        [win[0] + S, win[1] + chrome_h + S, win[2] - S, win[1] + chrome_h + RADIUS_CARD * S],
        fill=CARD_BG,
    )

    dot_y = win[1] + chrome_h // 2
    for i, colour in enumerate((ACCENT, DOT_IDLE, DOT_IDLE)):
        cx = win[0] + (18 + i * 16) * S
        d.ellipse([cx - 5 * S, dot_y - 5 * S, cx + 5 * S, dot_y + 5 * S], fill=colour)

    title = "New chat"
    d.text(
        ((W * S - d.textlength(title, font=F_CHROME)) / 2, dot_y - 8 * S),
        title,
        font=F_CHROME,
        fill=MUTED,
    )

    conn = "Connected to Floci"
    conn_w = d.textlength(conn, font=F_CHROME)
    d.text((win[2] - 18 * S - conn_w, dot_y - 8 * S), conn, font=F_CHROME, fill=ACCENT)
    cx = win[2] - 18 * S - conn_w - 12 * S
    d.ellipse([cx - 4 * S, dot_y - 4 * S, cx + 4 * S, dot_y + 4 * S], fill=ACCENT)

    pad = 24 * S
    left = win[0] + pad
    right = win[2] - pad
    y = win[1] + chrome_h + 24 * S

    # User message -- right-aligned accent bubble.
    bub_max = int((right - left) * 0.72)
    lines = wrap(d, PROMPT, F_BODY, bub_max - 28 * S)
    bw = max(d.textlength(ln, font=F_BODY) for ln in lines) + 28 * S
    bh = len(lines) * 21 * S + 24 * S
    d.rounded_rectangle([right - bw, y, right, y + bh], radius=14 * S, fill=ACCENT)
    for i, ln in enumerate(lines):
        d.text((right - bw + 14 * S, y + 12 * S + i * 21 * S), ln, font=F_BODY, fill=ACCENT_FG)
    y += bh + 22 * S

    # Assistant reply.
    for ln in wrap(d, REPLY, F_BODY, right - left):
        d.text((left, y), ln, font=F_BODY, fill=FG)
        y += 21 * S
    y += 12 * S

    # Board rows.
    for row in rows:
        passed = row["status"] == "working"
        label_w = right - left - 130 * S
        label_lines = wrap(d, row["label"], F_BODY_B, label_w)
        rh = 20 * S + len(label_lines) * 19 * S + (18 * S if passed else 0)
        d.rounded_rectangle(
            [left, y, right, y + rh], radius=12 * S, fill=CARD_BG, outline=BORDER, width=S
        )
        ty = y + 11 * S
        for ln in label_lines:
            d.text((left + 14 * S, ty), ln, font=F_BODY_B, fill=FG)
            ty += 19 * S
        if passed:
            d.text((left + 14 * S, ty + 1 * S), row["proof"], font=F_SMALL, fill=MUTED)
        if passed:
            pill(d, right - 14 * S, y + 11 * S, "VERIFIED", PASS_BG, PASS_FG)
        else:
            pill(d, right - 14 * S, y + 11 * S, "SETTING UP", WORKING_BG, WORKING_FG)
        y += rh + 10 * S

    footer = "Nothing says VERIFIED until it has been re-checked against the live service."
    d.text((left, win[3] - 26 * S), footer, font=F_SMALL, fill=MUTED)

    return img.resize((W, H), Image.LANCZOS)


def main():
    events = json.loads(EVENTS.read_text())

    frames, durations = [], []
    rows = []
    frames.append(render(rows))
    durations.append(1100)

    for ev in events:
        founder = ev["founder"]
        entry = {
            "capability": ev["capability"],
            "label": founder["label"],
            "status": founder["status"],
            "proof": founder.get("proof", ""),
        }
        for i, existing in enumerate(rows):
            if existing["capability"] == entry["capability"]:
                rows[i] = entry
                break
        else:
            rows.append(entry)
        frames.append(render(rows))
        durations.append(900)

    durations[-1] = 3000

    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
