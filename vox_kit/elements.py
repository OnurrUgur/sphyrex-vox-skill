"""Editorial paper-collage visual elements, procedural halftone icons, charts, and compositing."""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .palette import (
    C_BEIGE,
    C_BLACK_PAPER,
    C_BOARD,
    C_BRASS,
    C_GREEN,
    C_INK,
    C_MUTED,
    C_RED,
    C_RED_DARK,
    C_YELLOW,
    clamp01,
    ease_in_cubic,
    ease_out_back,
    ease_out_cubic,
    get_font,
)
from .paper import add_paper_shadow, make_masking_tape, torn_rect_polygon


def _safe_alpha_composite(base: Image.Image, overlay: Image.Image, dest_x: int, dest_y: int) -> None:
    """Alpha-composite overlay onto base even when dest_x/dest_y are negative or partially offscreen."""
    bw, bh = base.size
    ow, oh = overlay.size
    src_x0 = max(0, -dest_x)
    src_y0 = max(0, -dest_y)
    src_x1 = min(ow, bw - dest_x)
    src_y1 = min(oh, bh - dest_y)
    if src_x1 <= src_x0 or src_y1 <= src_y0:
        return
    dst_x = max(0, dest_x)
    dst_y = max(0, dest_y)
    if src_x0 == 0 and src_y0 == 0 and src_x1 == ow and src_y1 == oh:
        base.alpha_composite(overlay, (dst_x, dst_y))
    else:
        cropped = overlay.crop((src_x0, src_y0, src_x1, src_y1))
        base.alpha_composite(cropped, (dst_x, dst_y))


def draw_star(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_out: float,
    r_in: float,
    fill,
    outline,
) -> None:
    """Draw a 5-point archival star."""
    pts = [
        (
            cx + math.cos(-math.pi / 2.0 + i * math.pi / 5.0) * (r_out if i % 2 == 0 else r_in),
            cy + math.sin(-math.pi / 2.0 + i * math.pi / 5.0) * (r_out if i % 2 == 0 else r_in),
        )
        for i in range(10)
    ]
    d.polygon(pts, fill=fill, outline=outline)


def draw_check(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    radius: float = 20.0,
    fill: Tuple[int, int, int] = C_GREEN,
    stroke: Tuple[int, int, int] = C_BEIGE,
    outline: Tuple[int, int, int] = C_INK,
    width: int = 5,
) -> None:
    """Draw a patina-green approval badge with a bold crisp checkmark."""
    r = float(radius)
    d.ellipse(
        [(cx - r, cy - r), (cx + r, cy + r)],
        fill=(*fill, 255),
        outline=(*outline, 255),
        width=max(2, int(round(r * 0.15))),
    )
    d.line(
        [
            (cx - r * 0.45, cy),
            (cx - r * 0.10, cy + r * 0.40),
            (cx + r * 0.52, cy - r * 0.38),
        ],
        fill=(*stroke, 255),
        width=width,
        joint="curve",
    )


def make_torn_strip(
    text: str,
    bg: Tuple[int, int, int] = C_BEIGE,
    fg: Tuple[int, int, int] = C_INK,
    font_key: str = "anton",
    font_size: int = 60,
    pad_x: int = 48,
    pad_y: int = 22,
    tape_corners: bool = True,
    red_underline: float = 0.0,
    seed: int = 11,
    icon: str = "",
) -> Image.Image:
    """Torn paper headline strip with outside-corner masking tape (tape never overlaps letters)."""
    f = get_font(font_key, font_size)
    bb = f.getbbox(text)
    tw, th = max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
    icon_w = max(54, int(round(font_size * 1.05))) if icon else 0
    # Guarantee enough horizontal padding when tape is enabled so tape stays strictly on outer corners
    eff_pad_x = max(pad_x, 42) if tape_corners else pad_x
    cw = tw + icon_w + eff_pad_x * 2
    ch = th + pad_y * 2 + (16 if red_underline > 0.0 else 0)
    margin = 44
    im = Image.new("RGBA", (cw + margin * 2, ch + margin * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    poly = torn_rect_polygon(margin, margin, margin + cw, margin + ch, amp=4.6, step=15.0, seed=seed)
    d.polygon(poly, fill=(*bg, 255))
    d.line(poly + [poly[0]], fill=(182, 174, 162, 185), width=2)

    ix = margin + eff_pad_x + int(icon_w * 0.34)
    iy = margin + ch // 2
    if icon == "apple":
        d.rounded_rectangle([(ix - 20, iy - 22), (ix + 20, iy + 22)], radius=9, fill=(*C_INK, 255))
        d.line([(ix - 9, iy + 9), (ix, iy - 11), (ix + 9, iy + 9)], fill=(*C_BEIGE, 255), width=4)
        d.line([(ix - 6, iy + 2), (ix + 6, iy + 2)], fill=(*C_BEIGE, 255), width=3)
    elif icon == "play":
        d.polygon([(ix - 15, iy - 20), (ix + 20, iy), (ix - 15, iy + 20)], fill=(*C_RED, 255), outline=(*C_INK, 255))
    elif icon == "puzzle":
        d.rounded_rectangle([(ix - 20, iy - 18), (ix + 16, iy + 18)], radius=6, fill=(*C_INK, 255))
        d.ellipse([(ix + 8, iy - 9), (ix + 24, iy + 9)], fill=(*C_INK, 255))
        d.ellipse([(ix - 10, iy - 26), (ix + 8, iy - 10)], fill=(*C_INK, 255))
    elif icon == "doc":
        d.rectangle([(ix - 18, iy - 22), (ix + 18, iy + 22)], fill=(*C_YELLOW, 255), outline=(*C_INK, 255), width=4)
        for dy in (-10, 0, 10):
            d.line([(ix - 10, iy + dy), (ix + 10, iy + dy)], fill=(*C_INK, 255), width=3)
    elif icon == "check":
        draw_check(d, ix, iy, radius=20.0, fill=C_GREEN, stroke=C_BEIGE, outline=C_INK, width=5)
    elif icon == "coffee":
        d.rounded_rectangle([(ix - 17, iy - 14), (ix + 15, iy + 18)], radius=5, fill=(*C_INK, 255))
        d.arc([(ix + 8, iy - 8), (ix + 24, iy + 10)], start=-90, end=90, fill=(*C_INK, 255), width=4)
        d.line([(ix - 6, iy - 22), (ix - 6, iy - 16)], fill=(*C_RED, 255), width=3)
        d.line([(ix + 4, iy - 24), (ix + 4, iy - 17)], fill=(*C_RED, 255), width=3)
    elif icon == "pin":
        draw_brass_pin(d, ix, iy, scale=1.15, alpha=255)
    elif icon == "warning":
        d.polygon([(ix, iy - 20), (ix + 20, iy + 18), (ix - 20, iy + 18)], fill=(*C_RED, 255), outline=(*C_INK, 255))
        d.line([(ix, iy - 7), (ix, iy + 6)], fill=(*C_BEIGE, 255), width=4)
        d.ellipse([(ix - 2, iy + 10), (ix + 2, iy + 14)], fill=(*C_BEIGE, 255))

    tx = margin + eff_pad_x + icon_w - bb[0]
    ty = margin + pad_y - bb[1]
    d.text((tx, ty), text, font=f, fill=(*fg, 255))

    if red_underline > 0.02:
        ux0 = margin + eff_pad_x + icon_w - 4
        ux1 = ux0 + int((tw + 8) * clamp01(red_underline))
        uy = margin + pad_y + th + 12
        d.line([(ux0, uy), (ux1, uy - 2)], fill=(*C_RED, 255), width=9)

    out = add_paper_shadow(im, pad=16)
    if tape_corners:
        t1 = make_masking_tape(84, 24, angle=-34, seed=seed + 1)
        t2 = make_masking_tape(84, 24, angle=32, seed=seed + 2)
        _safe_alpha_composite(out, t1, 10, 10)
        _safe_alpha_composite(out, t2, out.width - t2.width - 10, out.height - t2.height - 10)
    return out


def make_red_stamp_on_slip(
    text: str,
    font_size: int = 80,
    seed: int = 33,
    with_slip: bool = True,
) -> Image.Image:
    """Worn red rubber stamp; placed on a torn cream archival slip by default for 200% contrast."""
    f = get_font("anton", font_size)
    bb = f.getbbox(text)
    tw, th = max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
    pad_x, pad_y = 34, 18
    sw, sh = tw + pad_x * 2, th + pad_y * 2
    st = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([(4, 4), (sw - 4, sh - 4)], radius=12, outline=(*C_RED, 245), width=9)
    sd.rounded_rectangle([(15, 15), (sw - 15, sh - 15)], radius=6, outline=(*C_RED, 190), width=3)
    sd.text((pad_x - bb[0], pad_y - bb[1]), text, font=f, fill=(*C_RED, 245))

    arr = np.array(st, dtype=np.float32)
    rng = np.random.default_rng(seed)
    nlow = Image.fromarray(
        (rng.uniform(0.58, 1.15, (max(4, sh // 6), max(4, sw // 6))) * 255.0).clip(0, 255).astype(np.uint8)
    ).resize((sw, sh), Image.Resampling.BILINEAR)
    arr[:, :, 3] = np.clip(
        arr[:, :, 3] * (np.array(nlow, dtype=np.float32) / 255.0) * (0.48 + 0.52 * (rng.random((sh, sw)) > 0.06)),
        0,
        255,
    )
    st = Image.fromarray(arr.astype(np.uint8), "RGBA")

    if not with_slip:
        return st

    cw, ch = sw + 56, sh + 46
    m = 36
    bg = Image.new("RGBA", (cw + m * 2, ch + m * 2), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    poly = torn_rect_polygon(m, m, m + cw, m + ch, amp=4.8, step=15.0, seed=seed + 7)
    bd.polygon(poly, fill=(*C_BEIGE, 255))
    bd.line(poly + [poly[0]], fill=(182, 174, 160, 180), width=2)
    st_rot = st.rotate(-2.2, resample=Image.Resampling.BICUBIC, expand=True)
    _safe_alpha_composite(bg, st_rot, (bg.width - st_rot.width) // 2, (bg.height - st_rot.height) // 2)
    out = add_paper_shadow(bg, pad=16)
    _safe_alpha_composite(out, make_masking_tape(84, 24, angle=-32, seed=seed + 11), 10, 10)
    return out


def apply_vox_colored_cutout(
    src_rgba: Image.Image,
    white_px: int = 7,
    accent_color: Tuple[int, int, int] = C_YELLOW,
    accent_px: int = 9,
) -> Image.Image:
    """Convert any RGBA graphic into a halftone archival cutout with scissor border, colored rim, and shadow."""
    src = src_rgba.convert("RGBA")
    pad = white_px + accent_px + 26
    w, h = src.size
    arr = np.array(src, dtype=np.float32)
    alpha = arr[:, :, 3]
    gray = np.clip((0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2] - 128.0) * 1.28 + 128.0, 0, 255)
    yy, xx = np.mgrid[0:h, 0:w]
    screen = (np.sin((xx + yy) * (math.pi / 4.8)) * np.sin((xx - yy) * (math.pi / 4.8)) + 1.0) * 127.5
    mixed = np.clip(0.70 * gray + 0.30 * ((gray > screen).astype(np.float32) * 255.0), 18, 246)
    body = Image.fromarray(np.dstack([mixed, mixed * 0.985, mixed * 0.955, alpha]).astype(np.uint8), "RGBA")

    fw, fh = w + pad * 2, h + pad * 2
    m0 = Image.new("L", (fw, fh), 0)
    m0.paste(body.split()[3], (pad, pad))
    m_white = m0.filter(ImageFilter.MaxFilter(max(3, white_px * 2 + 1))) if white_px > 0 else m0
    m_accent = m_white.filter(ImageFilter.MaxFilter(max(3, accent_px * 2 + 1))) if accent_px > 0 else m_white
    shad = Image.new("L", (fw, fh), 0)
    shad.paste(m_accent, (8, 11))
    shad = shad.filter(ImageFilter.GaussianBlur(9))

    out = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    out.paste(
        Image.new("RGBA", (fw, fh), (*C_INK, 255)),
        (0, 0),
        Image.fromarray((np.array(shad, dtype=np.float32) * 0.38).astype(np.uint8), "L"),
    )
    if accent_px > 0:
        out.paste(Image.new("RGBA", (fw, fh), (*accent_color, 255)), (0, 0), m_accent)
    if white_px > 0:
        out.paste(Image.new("RGBA", (fw, fh), (*C_BEIGE, 255)), (0, 0), m_white)
    out.alpha_composite(body, (pad, pad))
    return out


def draw_brass_pin(d: ImageDraw.ImageDraw, x: float, y: float, scale: float = 1.0, alpha: int = 255) -> None:
    """Draw an archival brass map push-pin."""
    r = 15.0 * max(0.05, scale)
    a = max(0, min(255, int(alpha)))
    d.ellipse([(x - r + 5, y - r + 7), (x + r + 5, y + r + 7)], fill=(20, 18, 18, int(a * 0.42)))
    d.ellipse([(x - r, y - r), (x + r, y + r)], fill=(168, 126, 44, a), outline=(*C_INK, a), width=3)
    d.ellipse([(x - r * 0.72, y - r * 0.72), (x + r * 0.72, y + r * 0.72)], fill=(*C_BRASS, a))
    d.ellipse([(x - r * 0.44, y - r * 0.46), (x - r * 0.05, y - r * 0.08)], fill=(252, 238, 190, a))


def draw_red_ribbon(
    overlay: ImageDraw.ImageDraw,
    pts: Sequence[Tuple[float, float]],
    reveal: float,
    width: int = 10,
) -> None:
    """Draw a progressive red string/ribbon route with subtle paper shadow."""
    if reveal <= 0.01 or len(pts) < 2:
        return
    count = max(2, int(round(len(pts) * clamp01(reveal))))
    sub = list(pts[:count])
    overlay.line([(p[0] + 5, p[1] + 7) for p in sub], fill=(24, 18, 18, 115), width=width + 2, joint="curve")
    overlay.line(sub, fill=(*C_RED_DARK, 245), width=width, joint="curve")
    overlay.line(sub, fill=(*C_RED, 255), width=max(4, width - 4), joint="curve")


def make_torn_receipt(
    idx_tag: str,
    title: str,
    right_txt: str,
    lit_p: float = 1.0,
    seed: int = 11,
    badge_color: Tuple[int, int, int] = C_YELLOW,
    width: int = 860,
    height: int = 118,
) -> Image.Image:
    """Torn paper ledger/receipt row with dark index box and animated highlight badge."""
    w, h = max(320, int(width)), max(72, int(height))
    m = 32
    im = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    poly = torn_rect_polygon(m, m, m + w, m + h, amp=4.0, step=15.0, seed=seed)
    d.polygon(poly, fill=(*C_BEIGE, 255))
    d.line(poly + [poly[0]], fill=(*C_INK, 235), width=3)

    idx_w = max(56, int(round(w * 0.092)))
    pad_v = max(14, int(round(h * 0.21)))
    d.rectangle([(m + 18, m + pad_v), (m + 18 + idx_w, m + h - pad_v)], fill=(*C_INK, 255))
    fi = get_font("typewriter", max(18, int(round(h * 0.25))))
    bi = fi.getbbox(idx_tag)
    d.text(
        (
            m + 18 + (idx_w - (bi[2] - bi[0])) // 2 - bi[0],
            m + pad_v + ((h - 2 * pad_v) - (bi[3] - bi[1])) // 2 - bi[1],
        ),
        idx_tag,
        font=fi,
        fill=(*C_YELLOW, 255),
    )

    f_title = get_font("serif_bold", max(22, int(round(h * 0.35))))
    bt = f_title.getbbox(title)
    d.text(
        (m + 38 + idx_w, m + (h - (bt[3] - bt[1])) // 2 - bt[1]),
        title,
        font=f_title,
        fill=(*C_INK, 255),
    )

    badge_w = max(140, int(round(w * 0.295)))
    bx0, by0, bx1, by1 = m + w - badge_w - 22, m + 20, m + w - 22, m + h - 20
    d.rectangle([(bx0, by0), (bx1, by1)], fill=(224, 218, 206, 255), outline=(*C_INK, 255), width=3)
    if lit_p > 0.02:
        p = ease_out_cubic(lit_p)
        fill_w = max(1, int((bx1 - bx0 - 6) * p))
        d.rectangle([(bx0 + 3, by0 + 3), (bx0 + 3 + fill_w, by1 - 3)], fill=(*badge_color, 255))
    fp = get_font("anton", max(24, int(round(h * 0.35))))
    bb = fp.getbbox(right_txt)
    is_dark_badge = badge_color in (C_RED, C_RED_DARK, C_INK, C_BLACK_PAPER, C_GREEN)
    col_p = (
        (*C_BEIGE, 255)
        if (is_dark_badge and lit_p > 0.25)
        else ((*C_INK, 255) if lit_p > 0.15 else (*C_MUTED, 255))
    )
    d.text(
        (
            bx0 + (bx1 - bx0 - (bb[2] - bb[0])) // 2 - bb[0],
            by0 + (by1 - by0 - (bb[3] - bb[1])) // 2 - bb[1],
        ),
        right_txt,
        font=fp,
        fill=col_p,
    )

    out = add_paper_shadow(im, pad=14)
    _safe_alpha_composite(out, make_masking_tape(74, 24, angle=-28, seed=seed + 5), 10, 8)
    return out


def make_step_card(
    num: str,
    title: str,
    sub: str,
    highlight: bool = False,
    seed: int = 33,
    width: int = 860,
    height: int = 148,
) -> Image.Image:
    """Large readable numbered editorial step card (designed for >=2.5s screen readability)."""
    w, h = max(360, int(width)), max(96, int(height))
    m = 34
    im = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    poly = torn_rect_polygon(m, m, m + w, m + h, amp=4.4, step=15.0, seed=seed)
    d.polygon(poly, fill=(*(C_YELLOW if highlight else C_BEIGE), 255))
    d.line(poly + [poly[0]], fill=(*C_INK, 240), width=3)

    num_w = max(72, int(round(w * 0.13)))
    d.rectangle([(m + 20, m + 22), (m + 20 + num_w, m + h - 22)], fill=(*C_INK, 255))
    fn = get_font("anton", max(32, int(round(h * 0.44))))
    bn = fn.getbbox(num)
    d.text(
        (
            m + 20 + (num_w - (bn[2] - bn[0])) // 2 - bn[0],
            m + 22 + ((h - 44) - (bn[3] - bn[1])) // 2 - bn[1],
        ),
        num,
        font=fn,
        fill=(*C_YELLOW, 255),
    )

    tx = m + 46 + num_w
    d.text((tx, m + int(round(h * 0.16))), title, font=get_font("anton", max(26, int(round(h * 0.35)))), fill=(*C_INK, 255))
    d.text(
        (tx, m + int(round(h * 0.62))),
        sub,
        font=get_font("serif_bold", max(18, int(round(h * 0.20)))),
        fill=(*(C_INK if highlight else C_MUTED), 255),
    )

    out = add_paper_shadow(im, pad=14)
    _safe_alpha_composite(out, make_masking_tape(72, 22, angle=-32, seed=seed + 1), 8, 8)
    return out


def make_search_slip(
    query: str,
    f: int,
    start_f: int,
    width: int = 820,
    height: int = 122,
) -> Image.Image:
    """Animated typewriter search-bar slip with blinking cursor."""
    w, h = max(320, int(width)), max(76, int(height))
    m = 36
    im = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    poly = torn_rect_polygon(m, m, m + w, m + h, amp=4.5, step=15.0, seed=91)
    d.polygon(poly, fill=(*C_BEIGE, 255))
    d.line(poly + [poly[0]], fill=(*C_INK, 225), width=3)

    age = max(0, int(f) - int(start_f))
    box_s = max(48, h - 44)
    d.rectangle(
        [(m + 22, m + 22), (m + 22 + box_s, m + h - 22)],
        fill=(*(C_RED if 8 <= age <= 16 else C_INK), 255),
    )
    mx, my = m + 22 + box_s // 2 - 3, m + h // 2 - 2
    r_glass = max(9, int(round(box_s * 0.19)))
    d.ellipse([(mx - r_glass, my - r_glass), (mx + r_glass, my + r_glass)], outline=(*C_BEIGE, 255), width=5)
    d.line([(mx + r_glass - 4, my + r_glass - 4), (mx + r_glass + 8, my + r_glass + 8)], fill=(*C_BEIGE, 255), width=6)

    q_show = query[: max(0, int(age * 2.5) + 4)]
    fq = get_font("typewriter", max(20, int(round(h * 0.31))))
    qx = m + 42 + box_s
    qy = m + int(round(h * 0.31))
    d.text((qx, qy), q_show, font=fq, fill=(*C_INK, 255))
    if (age // 5) % 2 == 0:
        qw = (fq.getbbox(q_show)[2] - fq.getbbox(q_show)[0]) if q_show else 0
        d.rectangle([(qx + qw + 6, qy), (qx + qw + 10, qy + int(round(h * 0.36)))], fill=(*C_RED, 255))

    out = add_paper_shadow(im, pad=16)
    _safe_alpha_composite(out, make_masking_tape(84, 24, angle=-32, seed=92), 10, 8)
    _safe_alpha_composite(out, make_masking_tape(84, 24, angle=28, seed=93), out.width - 100, 10)
    return out


def make_bar_chart_card(
    title: str,
    items: Sequence[Tuple[str, str, float, Tuple[int, int, int]]],
    progress: float = 1.0,
    width: int = 900,
    height: int = 620,
    seed: int = 51,
) -> Image.Image:
    """
    Animated torn-paper horizontal bar chart card.

    items: sequence of (label, value_str, ratio_0_to_1, color_rgb)
    """
    w, h = max(420, int(width)), max(280, int(height))
    m = 44
    im = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    poly = torn_rect_polygon(m, m, m + w, m + h, amp=5.0, step=16.0, seed=seed)
    d.polygon(poly, fill=(*C_BEIGE, 255))
    d.line(poly + [poly[0]], fill=(*C_INK, 235), width=3)

    # Top archival title band
    hdr_h = max(56, int(round(h * 0.12)))
    d.rectangle([(m + 30, m + 26), (m + w - 30, m + 26 + hdr_h)], fill=(*C_INK, 255))
    ft = get_font("anton", max(24, int(round(hdr_h * 0.56))))
    bt = ft.getbbox(title)
    d.text(
        (m + 52, m + 26 + (hdr_h - (bt[3] - bt[1])) // 2 - bt[1]),
        title,
        font=ft,
        fill=(*C_YELLOW, 255),
    )

    n = max(1, len(items))
    body_top = m + 44 + hdr_h
    body_bot = m + h - 34
    avail_h = max(80, body_bot - body_top)
    row_h = avail_h / n

    chart_x0 = m + 36
    chart_x1 = m + w - 180
    chart_w = max(120, chart_x1 - chart_x0)

    # Vertical archival reference guide lines (25%, 50%, 75%, 100%)
    for frac in (0.25, 0.50, 0.75, 1.0):
        gx = int(round(chart_x0 + chart_w * frac))
        d.line([(gx, body_top), (gx, body_bot)], fill=(214, 207, 194, 220), width=2)

    p = ease_out_cubic(clamp01(progress))
    lbl_sz = max(18, min(32, int(round(row_h * 0.27))))
    val_sz = max(20, min(38, int(round(row_h * 0.34))))
    f_lbl = get_font("serif_bold", lbl_sz)
    f_val = get_font("anton", val_sz)

    for idx, (label, val_str, ratio, col_rgb) in enumerate(items):
        ry = body_top + idx * row_h
        d.text((chart_x0, ry + 2), str(label), font=f_lbl, fill=(*C_INK, 255))

        bar_y0 = ry + lbl_sz + 10
        bar_h = max(20, min(46, int(round(row_h * 0.42))))
        bar_y1 = min(ry + row_h - 8, bar_y0 + bar_h)

        # Recessed track
        d.rectangle([(chart_x0, bar_y0), (chart_x1, bar_y1)], fill=(228, 222, 210, 255), outline=(196, 189, 176, 255), width=2)

        r_eff = clamp01(float(ratio)) * p
        bw = max(10, int(round(chart_w * r_eff)))
        if r_eff > 0.005:
            b_poly = torn_rect_polygon(chart_x0, bar_y0, chart_x0 + bw, bar_y1, amp=2.2, step=12.0, seed=seed + 20 + idx)
            d.polygon([(px + 4, py + 5) for px, py in b_poly], fill=(20, 18, 18, 70))
            d.polygon(b_poly, fill=(*col_rgb, 255))
            # Subtle engraved diagonal hatching inside bar
            hatch_col = (244, 239, 229, 70) if col_rgb in (C_INK, C_BLACK_PAPER, C_RED, C_RED_DARK) else (26, 25, 29, 45)
            for hx in range(int(chart_x0) + 12, int(chart_x0 + bw) - 6, 18):
                d.line([(hx, bar_y0 + 3), (hx - 10, bar_y1 - 3)], fill=hatch_col, width=2)
            d.line(b_poly + [b_poly[0]], fill=(*C_INK, 230), width=3)

        # Right-side bold value label
        bv = f_val.getbbox(str(val_str))
        vy = bar_y0 + ((bar_y1 - bar_y0) - (bv[3] - bv[1])) // 2 - bv[1]
        d.text((chart_x1 + 18, vy), str(val_str), font=f_val, fill=(*C_INK, 255))

    out = add_paper_shadow(im, pad=18)
    _safe_alpha_composite(out, make_masking_tape(88, 24, angle=-34, seed=seed + 1), 10, 10)
    _safe_alpha_composite(out, make_masking_tape(88, 24, angle=32, seed=seed + 2), out.width - 104, 10)
    return out


def _add_cross_hatch(
    im: Image.Image,
    bbox: Tuple[int, int, int, int],
    step: int = 12,
    alpha_mask: Optional[Image.Image] = None,
    double: bool = False,
) -> None:
    """Apply engraving-style diagonal hatch lines constrained by alpha_mask."""
    w, h = im.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = bbox
    span = (x1 - x0) + (y1 - y0)
    for k in range(-span, span, max(5, step)):
        ld.line([(x0 + k, y0), (x0 + k - (y1 - y0), y1)], fill=(*C_INK, 125), width=2)
        if double:
            ld.line([(x0 + k, y0), (x0 + k + (y1 - y0), y1)], fill=(*C_INK, 90), width=2)
    if alpha_mask is not None:
        arr_l = np.array(layer, dtype=np.uint8)
        arr_m = np.array(alpha_mask, dtype=np.float32) / 255.0
        arr_l[:, :, 3] = (arr_l[:, :, 3].astype(np.float32) * arr_m).astype(np.uint8)
        layer = Image.fromarray(arr_l, "RGBA")
    im.alpha_composite(layer)


def make_procedural_halftone_icon(
    kind: str,
    size: int = 320,
    accent: Tuple[int, int, int] = C_YELLOW,
    seed: int = 19,
) -> Image.Image:
    """
    Generate zero-dependency engraved/halftone editorial cutout icons.

    Supported kinds:
      coffee_cup, coffee_bean, cargo_ship, paper_cup, coin_stack,
      receipt_roll, magnifying_glass, scissors, code_terminal
    """
    s = max(96, int(size))
    k = kind.lower().strip()
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(4, int(round(s * 0.024)))
    ink = (*C_INK, 255)
    paper = (232, 226, 214, 255)
    mid = (162, 156, 146, 255)
    dark = (74, 70, 68, 255)
    c = s / 2.0

    def p(fx: float, fy: float) -> Tuple[float, float]:
        return (fx * s, fy * s)

    if k == "coffee_cup":
        # Saucer
        d.ellipse([p(0.10, 0.72), p(0.90, 0.88)], fill=mid, outline=ink, width=lw)
        d.ellipse([p(0.22, 0.75), p(0.78, 0.84)], fill=paper, outline=ink, width=max(2, lw // 2))
        # Handle
        d.arc([p(0.64, 0.34), p(0.89, 0.64)], start=-90, end=90, fill=ink, width=int(lw * 2.1))
        d.arc([p(0.67, 0.39), p(0.84, 0.59)], start=-90, end=90, fill=paper, width=max(3, lw))
        # Cup body
        cup_poly = [p(0.20, 0.30), p(0.74, 0.30), p(0.67, 0.75), p(0.27, 0.75)]
        d.polygon(cup_poly, fill=paper, outline=ink)
        d.line(cup_poly + [cup_poly[0]], fill=ink, width=lw)
        # Rim & coffee liquid
        d.ellipse([p(0.20, 0.25), p(0.74, 0.35)], fill=dark, outline=ink, width=lw)
        # Steam waves
        for sx in (0.35, 0.47, 0.59):
            pts = [p(sx + 0.02 * math.sin(i * 1.4), 0.22 - i * 0.045) for i in range(4)]
            d.line(pts, fill=ink, width=max(3, lw - 1), joint="curve")
        # Hatching on shaded right half of cup
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).polygon([p(0.48, 0.34), p(0.72, 0.34), p(0.66, 0.74), p(0.48, 0.74)], fill=255)
        _add_cross_hatch(im, (int(s * 0.46), int(s * 0.32), int(s * 0.74), int(s * 0.75)), step=max(7, s // 30), alpha_mask=mask, double=True)

    elif k == "coffee_bean":
        bean = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bean)
        bd.ellipse([p(0.20, 0.12), p(0.80, 0.88)], fill=mid, outline=ink, width=lw + 1)
        # Highlight crescent on left
        bd.arc([p(0.27, 0.20), p(0.73, 0.80)], start=115, end=245, fill=paper, width=max(4, lw + 2))
        # Center S-crevice
        crevice = [p(0.50 + 0.045 * math.sin((i / 10.0) * math.pi * 2.0), 0.16 + 0.68 * (i / 10.0)) for i in range(11)]
        bd.line(crevice, fill=ink, width=int(lw * 1.5), joint="curve")
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([p(0.49, 0.14), p(0.79, 0.86)], fill=255)
        _add_cross_hatch(bean, (int(s * 0.48), int(s * 0.14), int(s * 0.80), int(s * 0.86)), step=max(7, s // 28), alpha_mask=mask, double=True)
        im = bean.rotate(-22, resample=Image.Resampling.BICUBIC)

    elif k == "cargo_ship":
        # Container stacks
        d.rectangle([p(0.24, 0.36), p(0.40, 0.54)], fill=paper, outline=ink, width=lw)
        d.rectangle([p(0.40, 0.30), p(0.58, 0.54)], fill=mid, outline=ink, width=lw)
        d.rectangle([p(0.58, 0.38), p(0.74, 0.54)], fill=paper, outline=ink, width=lw)
        # Bridge & smokestack
        d.rectangle([p(0.68, 0.22), p(0.80, 0.54)], fill=paper, outline=ink, width=lw)
        d.rectangle([p(0.72, 0.14), p(0.78, 0.22)], fill=dark, outline=ink, width=lw)
        d.rectangle([p(0.71, 0.27), p(0.78, 0.33)], fill=dark)
        # Hull
        hull = [p(0.08, 0.54), p(0.92, 0.54), p(0.84, 0.76), p(0.18, 0.76)]
        d.polygon(hull, fill=dark, outline=ink)
        d.line(hull + [hull[0]], fill=ink, width=lw)
        d.line([p(0.13, 0.65), p(0.88, 0.65)], fill=paper, width=max(3, lw - 1))
        # Waves below
        for wy in (0.79, 0.85):
            wpts = [p(0.08 + 0.84 * (i / 14.0), wy + 0.018 * math.sin(i * 1.6)) for i in range(15)]
            d.line(wpts, fill=ink, width=max(3, lw - 1), joint="curve")
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).polygon(hull, fill=255)
        _add_cross_hatch(im, (int(s * 0.08), int(s * 0.54), int(s * 0.92), int(s * 0.76)), step=max(7, s // 30), alpha_mask=mask)

    elif k == "paper_cup":
        # Takeaway lid
        d.polygon([p(0.24, 0.14), p(0.76, 0.14), p(0.80, 0.23), p(0.20, 0.23)], fill=paper, outline=ink)
        d.line([p(0.24, 0.14), p(0.76, 0.14), p(0.80, 0.23), p(0.20, 0.23), p(0.24, 0.14)], fill=ink, width=lw)
        d.rectangle([p(0.18, 0.23), p(0.82, 0.30)], fill=mid, outline=ink, width=lw)
        # Tapered cup body
        cup = [p(0.23, 0.30), p(0.77, 0.30), p(0.68, 0.88), p(0.32, 0.88)]
        d.polygon(cup, fill=paper, outline=ink)
        d.line(cup + [cup[0]], fill=ink, width=lw)
        # Kraft cardboard sleeve
        sleeve = [p(0.26, 0.45), p(0.74, 0.45), p(0.71, 0.70), p(0.29, 0.70)]
        d.polygon(sleeve, fill=mid, outline=ink)
        d.line(sleeve + [sleeve[0]], fill=ink, width=lw)
        d.ellipse([p(0.42, 0.50), p(0.58, 0.65)], fill=paper, outline=ink, width=max(3, lw - 1))
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).polygon(sleeve, fill=255)
        _add_cross_hatch(im, (int(s * 0.26), int(s * 0.45), int(s * 0.74), int(s * 0.70)), step=max(6, s // 34), alpha_mask=mask)

    elif k == "coin_stack":
        # Back tall stack (5 coins)
        for i in range(5):
            cy = 0.76 - i * 0.11
            d.rectangle([p(0.16, cy - 0.06), p(0.56, cy + 0.03)], fill=mid, outline=ink, width=lw)
            d.ellipse([p(0.16, cy - 0.11), p(0.56, cy - 0.01)], fill=paper, outline=ink, width=lw)
            for rx in (0.22, 0.28, 0.34, 0.40, 0.46, 0.51):
                d.line([p(rx, cy - 0.01), p(rx, cy + 0.03)], fill=ink, width=max(2, lw // 2))
        # Front shorter stack (3 coins)
        for i in range(3):
            cy = 0.82 - i * 0.11
            d.rectangle([p(0.44, cy - 0.06), p(0.84, cy + 0.03)], fill=dark, outline=ink, width=lw)
            d.ellipse([p(0.44, cy - 0.11), p(0.84, cy - 0.01)], fill=paper, outline=ink, width=lw)
            for rx in (0.50, 0.56, 0.62, 0.68, 0.74, 0.79):
                d.line([p(rx, cy - 0.01), p(rx, cy + 0.03)], fill=ink, width=max(2, lw // 2))
        d.ellipse([p(0.52, 0.51), p(0.76, 0.57)], outline=ink, width=max(2, lw // 2))

    elif k == "receipt_roll":
        # Zig-zag torn top & bottom receipt
        pts: List[Tuple[float, float]] = []
        n_teeth = 8
        for i in range(n_teeth + 1):
            tx = 0.22 + 0.56 * (i / n_teeth)
            ty = 0.12 if i % 2 == 0 else 0.16
            pts.append(p(tx, ty))
        pts.append(p(0.78, 0.84))
        for i in range(n_teeth, -1, -1):
            tx = 0.22 + 0.56 * (i / n_teeth)
            ty = 0.88 if i % 2 == 0 else 0.84
            pts.append(p(tx, ty))
        d.polygon(pts, fill=paper, outline=ink)
        d.line(pts + [pts[0]], fill=ink, width=lw)
        # Header bar & ledger lines (abstract, zero text)
        d.rectangle([p(0.30, 0.23), p(0.70, 0.30)], fill=dark)
        for idx, ry in enumerate((0.38, 0.47, 0.56, 0.65, 0.75)):
            d.line([p(0.30, ry), p(0.55 if idx % 2 == 0 else 0.50, ry)], fill=ink, width=max(3, lw - 1))
            d.line([p(0.61, ry), p(0.70, ry)], fill=ink, width=max(3, lw - 1))
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rectangle([p(0.62, 0.16), p(0.77, 0.84)], fill=255)
        _add_cross_hatch(im, (int(s * 0.62), int(s * 0.16), int(s * 0.77), int(s * 0.84)), step=max(7, s // 30), alpha_mask=mask)

    elif k == "magnifying_glass":
        # Handle
        d.line([p(0.58, 0.58), p(0.86, 0.86)], fill=ink, width=int(lw * 4.2))
        d.line([p(0.60, 0.60), p(0.84, 0.84)], fill=mid, width=int(lw * 2.2))
        # Outer rim
        d.ellipse([p(0.12, 0.12), p(0.66, 0.66)], fill=dark, outline=ink, width=lw)
        # Lens glass
        d.ellipse([p(0.19, 0.19), p(0.59, 0.59)], fill=paper, outline=ink, width=lw)
        # Specular reflection arc
        d.arc([p(0.24, 0.24), p(0.54, 0.54)], start=195, end=260, fill=ink, width=max(3, lw))
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).ellipse([p(0.38, 0.20), p(0.58, 0.58)], fill=255)
        _add_cross_hatch(im, (int(s * 0.38), int(s * 0.20), int(s * 0.58), int(s * 0.58)), step=max(7, s // 30), alpha_mask=mask)

    elif k == "scissors":
        # Upper & lower blades
        b1 = [p(0.46, 0.47), p(0.88, 0.20), p(0.84, 0.32), p(0.50, 0.55)]
        b2 = [p(0.46, 0.53), p(0.88, 0.80), p(0.84, 0.68), p(0.50, 0.45)]
        d.polygon(b1, fill=paper, outline=ink)
        d.line(b1 + [b1[0]], fill=ink, width=lw)
        d.polygon(b2, fill=mid, outline=ink)
        d.line(b2 + [b2[0]], fill=ink, width=lw)
        # Handles
        d.line([p(0.48, 0.50), p(0.30, 0.34)], fill=ink, width=int(lw * 1.8))
        d.line([p(0.48, 0.50), p(0.30, 0.66)], fill=ink, width=int(lw * 1.8))
        d.ellipse([p(0.12, 0.16), p(0.36, 0.40)], fill=dark, outline=ink, width=lw)
        d.ellipse([p(0.18, 0.22), p(0.30, 0.34)], fill=(0, 0, 0, 0), outline=ink, width=lw)
        d.ellipse([p(0.12, 0.60), p(0.36, 0.84)], fill=dark, outline=ink, width=lw)
        d.ellipse([p(0.18, 0.66), p(0.30, 0.78)], fill=(0, 0, 0, 0), outline=ink, width=lw)
        # Pivot rivet
        d.ellipse([p(0.45, 0.46), p(0.53, 0.54)], fill=paper, outline=ink, width=lw)

    elif k == "code_terminal":
        # Archival CRT / terminal window
        d.rounded_rectangle([p(0.10, 0.16), p(0.90, 0.84)], radius=max(10, s // 22), fill=paper, outline=ink, width=lw)
        d.rectangle([p(0.10, 0.16), p(0.90, 0.29)], fill=dark, outline=ink, width=lw)
        for bx in (0.17, 0.24, 0.31):
            d.ellipse([p(bx - 0.02, 0.205), p(bx + 0.02, 0.245)], fill=paper)
        # Prompt chevron >_
        d.line([p(0.20, 0.40), p(0.30, 0.48), p(0.20, 0.56)], fill=ink, width=int(lw * 1.6), joint="curve")
        d.line([p(0.36, 0.56), p(0.52, 0.56)], fill=ink, width=int(lw * 1.6))
        # Abstract code bars
        d.line([p(0.20, 0.67), p(0.72, 0.67)], fill=mid, width=int(lw * 1.2))
        d.line([p(0.20, 0.75), p(0.58, 0.75)], fill=mid, width=int(lw * 1.2))
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rectangle([p(0.60, 0.31), p(0.88, 0.82)], fill=255)
        _add_cross_hatch(im, (int(s * 0.60), int(s * 0.31), int(s * 0.88), int(s * 0.82)), step=max(7, s // 30), alpha_mask=mask)

    else:
        raise ValueError(
            f"Unknown procedural icon kind: {kind!r}. Choose from: "
            "coffee_cup, coffee_bean, cargo_ship, paper_cup, coin_stack, "
            "receipt_roll, magnifying_glass, scissors, code_terminal"
        )

    # Subtle deterministic ink grain so procedural icon matches archival print texture
    rng = np.random.default_rng(seed)
    arr = np.array(im, dtype=np.float32)
    nz = arr[:, :, 3] > 20
    noise = rng.normal(0.0, 6.0, (s, s)).astype(np.float32)
    for ch in range(3):
        arr[:, :, ch] = np.where(nz, np.clip(arr[:, :, ch] + noise, 10, 250), arr[:, :, ch])
    im = Image.fromarray(arr.astype(np.uint8), "RGBA")

    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    white_px = max(4, int(round(s * 0.022)))
    accent_px = max(5, int(round(s * 0.028)))
    return apply_vox_colored_cutout(im, white_px=white_px, accent_color=accent, accent_px=accent_px)


def composite_smooth(
    base: Image.Image,
    piece: Image.Image,
    cx: float,
    cy: float,
    f: int,
    start_f: int,
    end_f: int,
    fps: int = 24,
    in_dur: int = 6,
    out_dur: int = 5,
    slide_in: Tuple[float, float] = (0.0, 32.0),
    slide_out: Tuple[float, float] = (0.0, -24.0),
    base_scale: float = 1.0,
    rot: float = 0.0,
    float_amp: float = 0.0,
    stamp_pop: bool = False,
) -> None:
    """Smoothly enter, hold (with optional gentle float), and exit an RGBA collage element."""
    if f < start_f or f >= end_f:
        return
    age, rem = f - start_f, end_f - f
    if age < in_dur:
        u = age / max(1, in_dur)
        if stamp_pop:
            e = ease_out_cubic(u)
            sc = base_scale * (1.26 - 0.26 * e)
            dx, dy = slide_in[0] * (1.0 - e), slide_in[1] * (1.0 - e)
            alpha = clamp01(u * 3.2)
        else:
            eb = ease_out_back(u, overshoot=0.82)
            sc = base_scale * (0.93 + 0.07 * eb)
            dx, dy = slide_in[0] * (1.0 - eb), slide_in[1] * (1.0 - eb)
            alpha = clamp01(u * 2.6)
    elif rem <= out_dur and out_dur > 1:
        e_out = ease_in_cubic(1.0 - rem / max(1, out_dur))
        sc = base_scale * (1.0 - 0.04 * e_out)
        dx, dy = slide_out[0] * e_out, slide_out[1] * e_out
        alpha = clamp01(1.0 - e_out * 1.15)
    else:
        sc, dx, dy, alpha = base_scale, 0.0, 0.0, 1.0

    if float_amp > 0.0 and alpha > 0.2:
        dy += math.sin((f / max(1, fps)) * 2.3) * float_amp
    if alpha <= 0.02 or sc <= 0.01:
        return

    im = piece
    if abs(sc - 1.0) > 0.004:
        im = im.resize(
            (max(4, int(round(im.width * sc))), max(4, int(round(im.height * sc)))),
            Image.Resampling.BICUBIC,
        )
    if abs(rot) > 0.04:
        im = im.rotate(rot, resample=Image.Resampling.BICUBIC, expand=True)
    if alpha < 0.995:
        im = im.copy()
        im.putalpha(im.split()[3].point(lambda p: int(p * alpha)))

    dest_x = int(round(cx + dx - im.width / 2.0))
    dest_y = int(round(cy + dy - im.height / 2.0))
    _safe_alpha_composite(base, im, dest_x, dest_y)
