"""Paper grain overlays, archival boards, torn polygons, masking tape, shadows, and curtains."""
from __future__ import annotations

import math
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .palette import C_BEIGE, C_BLACK_PAPER, C_BOARD, C_INK, C_TAPE


def build_paper_overlay(w: int, h: int, seed: int = 42) -> Tuple[np.ndarray, List[np.ndarray]]:
    """Build subtle archival paper grain + vignette texture and 3 film-dust boil layers."""
    rng = np.random.default_rng(seed)
    lw = max(4, w // 24)
    lh = max(4, h // 24)
    low = rng.normal(0.972, 0.022, (lh, lw)).astype(np.float32)
    low_img = Image.fromarray(np.clip(low * 255.0, 0, 255).astype(np.uint8)).resize(
        (w, h), Image.Resampling.BICUBIC
    )
    tex = np.array(low_img, dtype=np.float32) / 255.0
    tex = np.clip(tex + rng.normal(0.0, 0.012, (h, w)).astype(np.float32), 0.85, 1.0)

    xx = np.arange(w, dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)
    nx = (xx - w / 2.0) / max(1.0, w / 2.0)
    ny = (yy - h / 2.0) / max(1.0, h / 2.0)
    vig = np.clip(1.0 - 0.14 * np.maximum(0.0, nx[None, :] ** 2 + ny[:, None] ** 2 - 0.48), 0.74, 1.0)
    tex *= vig

    dusts: List[np.ndarray] = []
    n_specks = max(12, int(round(26 * (w * h) / (1080 * 1920))))
    for k in range(3):
        drng = np.random.default_rng(seed + 100 + k)
        dimg = Image.new("L", (w, h), 255)
        dd = ImageDraw.Draw(dimg)
        for _ in range(n_specks):
            dx = int(drng.integers(0, max(1, w)))
            dy = int(drng.integers(0, max(1, h)))
            rr = int(drng.integers(1, 3))
            dd.ellipse([(dx - rr, dy - rr), (dx + rr, dy + rr)], fill=int(drng.integers(175, 226)))
        dusts.append(np.array(dimg, dtype=np.float32) / 255.0)
    return tex, dusts


def apply_paper_overlay(
    frame: Image.Image,
    tex: np.ndarray,
    dusts: List[np.ndarray],
    frame_idx: int = 0,
) -> np.ndarray:
    """Multiply paper grain and 6fps dust boil onto an RGB/RGBA frame, returning uint8 RGB array."""
    rgb = np.array(frame.convert("RGB"), dtype=np.float32)
    dust = dusts[(frame_idx // 4) % len(dusts)] if dusts else 1.0
    rgb *= (tex * dust)[:, :, None]
    return np.clip(rgb, 0.0, 255.0).astype(np.uint8)


def build_cream_board(w: int, h: int, grid_step: int = 90) -> Image.Image:
    """Warm parchment archival board with subtle millimeter drafting grid."""
    im = Image.new("RGB", (w, h), C_BOARD)
    d = ImageDraw.Draw(im)
    step = max(24, int(grid_step))
    start = min(60, step // 2)
    grid_col = (230, 224, 213)
    for x in range(start, w, step):
        d.line([(x, 0), (x, h)], fill=grid_col, width=1)
    for y in range(start, h, step):
        d.line([(0, y), (w, y)], fill=grid_col, width=1)
    return im


def torn_rect_polygon(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    amp: float = 4.8,
    step: float = 15.0,
    seed: int = 1,
) -> List[Tuple[float, float]]:
    """Generate a deterministic hand-torn paper rectangle polygon."""
    rng = np.random.default_rng(seed)
    pts: List[Tuple[float, float]] = []
    nx = max(4, int(abs(x1 - x0) / max(2.0, step)))
    ny = max(4, int(abs(y1 - y0) / max(2.0, step)))
    for i in range(nx):
        pts.append((x0 + (x1 - x0) * (i / nx), y0 + float(rng.uniform(-amp, amp))))
    for i in range(ny):
        pts.append((x1 + float(rng.uniform(-amp, amp)), y0 + (y1 - y0) * (i / ny)))
    for i in range(nx):
        pts.append((x1 - (x1 - x0) * (i / nx), y1 + float(rng.uniform(-amp, amp))))
    for i in range(ny):
        pts.append((x0 + float(rng.uniform(-amp, amp)), y1 - (y1 - y0) * (i / ny)))
    return pts


def make_masking_tape(
    length: int = 96,
    width: int = 28,
    angle: float = -32.0,
    seed: int = 7,
) -> Image.Image:
    """Semi-transparent textured masking tape strip with torn ends."""
    pad = 10
    im = Image.new("RGBA", (length + pad * 2, width + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = torn_rect_polygon(pad, pad, pad + length, pad + width, amp=2.6, step=9.0, seed=seed)
    d.polygon(pts, fill=(*C_TAPE, 195))
    rng = np.random.default_rng(seed + 9)
    low_y = pad + 3
    high_y = max(low_y + 1, pad + width - 3)
    for _ in range(12):
        y = int(rng.integers(low_y, high_y))
        d.line([(pad + 4, y), (pad + length - 4, y)], fill=(252, 246, 228, 62), width=1)
    return im.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)


def add_paper_shadow(
    body_rgba: Image.Image,
    pad: int = 20,
    offset: Tuple[int, int] = (7, 10),
    blur: int = 9,
    opacity: float = 0.36,
) -> Image.Image:
    """Add soft directional archival drop shadow behind an RGBA paper cutout."""
    w, h = body_rgba.size
    fw, fh = w + pad * 2, h + pad * 2
    shad = Image.new("L", (fw, fh), 0)
    shad.paste(body_rgba.split()[3], (pad + offset[0], pad + offset[1]))
    if blur > 0:
        shad = shad.filter(ImageFilter.GaussianBlur(blur))
    s_arr = np.clip(np.array(shad, dtype=np.float32) * opacity, 0, 255).astype(np.uint8)
    out = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (fw, fh), (*C_INK, 255)), (0, 0), Image.fromarray(s_arr, "L"))
    out.alpha_composite(body_rgba, (pad, pad))
    return out


def make_horizontal_torn_curtain(
    w: int,
    h: int,
    split_y: int,
    fill_color: Tuple[int, int, int] = C_BLACK_PAPER,
    edge_color: Tuple[int, int, int] = C_BEIGE,
    seed: int = 79,
) -> Image.Image:
    """Horizontal torn paper curtain rising from the bottom so top maps remain 100% uncut."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    pts: List[Tuple[float, float]] = []
    step_x = max(12, int(round(w / 50.0)))
    x = -20
    while x <= w + 20:
        jy = float(rng.uniform(-15.0, 15.0)) + 13.0 * math.sin(x / 160.0)
        pts.append((float(x), float(split_y) + jy))
        x += step_x
    pts.extend([(float(w + 20), float(h + 20)), (-20.0, float(h + 20))])
    d.polygon([(p[0], p[1] - 10.0) for p in pts], fill=(10, 10, 12, 95))
    d.polygon([(p[0], p[1] - 4.0) for p in pts], fill=(*edge_color, 240))
    d.polygon(pts, fill=(*fill_color, 255))
    return im
