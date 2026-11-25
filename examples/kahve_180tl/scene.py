"""
48-second Hybrid Vox x Engraving mini-documentary demo:
"180 TL'lik Kahveden Ciftciye Ne Kaliyor?"

Works identically in both 9:16 vertical (1080x1920) and 16:9 widescreen (1920x1080)
at locked 24 FPS (1,152 frames), with zero personal paths and zero external APIs.

Run via `vox_kit` CLI:
  python3 -m vox_kit map-prep --countries BRA,COL,TUR --out examples/kahve_180tl/cache/map
  python3 -m vox_kit render examples/kahve_180tl/scene.py --aspect 9:16 --out examples/kahve_180tl/out/kahve-demo.mp4
  python3 -m vox_kit render examples/kahve_180tl/scene.py --aspect 16:9 --out examples/kahve_180tl/out/kahve-demo-16x9.mp4
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from vox_kit import (
    C_BEIGE,
    C_BLACK_PAPER,
    C_GREEN,
    C_INK,
    C_MUTED,
    C_RED,
    C_YELLOW,
    MapCamera,
    SoundMixer,
    TimedCaption,
    VideoConfig,
    apply_paper_overlay,
    build_cream_board,
    build_paper_overlay,
    captions_to_groups,
    clamp01,
    composite_smooth,
    draw_brass_pin,
    draw_red_ribbon,
    draw_subtitle_bar,
    ease_in_cubic,
    ease_out_cubic,
    get_font,
    make_bar_chart_card,
    make_horizontal_torn_curtain,
    make_procedural_halftone_icon,
    make_red_stamp_on_slip,
    make_torn_receipt,
    make_torn_strip,
    render_scene,
    smoothstep,
)

DURATION_SEC = 48.0
DEFAULT_FPS = 24
SCENE_DIR = Path(__file__).resolve().parent
DEFAULT_MAP_CACHE = SCENE_DIR / "cache" / "map"

# Key geographic coordinates (lon, lat)
BRA_PORT = (-46.3, -23.9)   # Santos / Minas Gerais coffee belt
COL_BELT = (-74.5, 4.8)     # Colombia Eje Cafetero
IST_CITY = (29.0, 41.0)     # Istanbul, Turkey

# 7-item cost breakdown for a 180 TL specialty/mid-tier cafe latte (Turkey 2026)
BREAKDOWN_ITEMS: List[Tuple[str, str, float, Tuple[int, int, int]]] = [
    ("Kira & Enerji", "58 TL", 58.0 / 58.0, C_RED),
    ("Barista İşçiliği", "49 TL", 49.0 / 58.0, C_YELLOW),
    ("KDV (%10) + POS", "21 TL", 21.0 / 58.0, C_INK),
    ("Kafe Net Kârı", "20 TL", 20.0 / 58.0, C_GREEN),
    ("Süt + Bardak", "14 TL", 14.0 / 58.0, C_MUTED),
    ("Nakliye & Kavurma", "12 TL", 12.0 / 58.0, C_MUTED),
    ("Çiftçi (22g)", "6 TL", 6.0 / 58.0, C_RED),
]

# Single-line (<=3 words, <=17 clean chars) narrative subtitles spanning all 48 seconds
TIMED_CAPTIONS: List[TimedCaption] = [
    TimedCaption(0.15, 1.50, "180 TL latte."),
    TimedCaption(1.65, 3.45, "Çiftçiye ne kalır?"),
    TimedCaption(3.60, 5.80, "Sadece 6 TL!"),
    TimedCaption(6.10, 7.90, "Brezilya'da doğar."),
    TimedCaption(8.05, 9.90, "22g yeşil çekirdek."),
    TimedCaption(10.15, 12.15, "10.500 km okyanus."),
    TimedCaption(12.30, 14.35, "Atlantik'i aşar."),
    TimedCaption(14.55, 16.80, "Çiftçiye 6 TL."),
    TimedCaption(17.10, 18.80, "Kalan 174 TL?"),
    TimedCaption(19.00, 20.45, "Nakliye ve süt."),
    TimedCaption(20.60, 21.95, "Vergi ve POS."),
    TimedCaption(22.10, 23.45, "Barista: 49 TL."),
    TimedCaption(23.60, 25.30, "Kira: 58 TL."),
    TimedCaption(25.50, 27.25, "20 TL kâr."),
    TimedCaption(27.40, 29.30, "Yarısı kira, işçi."),
    TimedCaption(29.60, 31.95, "İşte tam tablo."),
    TimedCaption(32.15, 34.25, "Tam 7 kalem."),
    TimedCaption(34.45, 36.30, "En dipte çiftçi."),
    TimedCaption(36.60, 37.95, "Şok karşılaştırma!"),
    TimedCaption(38.10, 39.35, "Çiftçi: 6 TL."),
    TimedCaption(39.50, 41.05, "Bardak: 5 TL."),
    TimedCaption(41.20, 42.80, "Neredeyse aynı!"),
    TimedCaption(43.10, 44.25, "0 After Effects."),
    TimedCaption(44.40, 45.60, "$0 API maliyeti."),
    TimedCaption(45.75, 47.85, "Tek Python skill."),
]

STATE: Dict[str, object] = {}


def _fit_width(im: Image.Image, max_w: int) -> Image.Image:
    """Proportionally downscale an element if it exceeds max_w so nothing ever overflows."""
    if im.width <= max_w:
        return im
    ratio = max_w / float(im.width)
    return im.resize(
        (max(4, int(round(im.width * ratio))), max(4, int(round(im.height * ratio)))),
        Image.Resampling.LANCZOS,
    )


def _make_vs_badge(size: int = 86) -> Image.Image:
    """Crisp circular yellow/ink VS badge for Beat 5."""
    s = max(48, int(size))
    im = Image.new("RGBA", (s + 16, s + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (s + 16) / 2.0
    r = s / 2.0
    d.ellipse([(c - r + 4, c - r + 5), (c + r + 4, c + r + 5)], fill=(10, 10, 12, 130))
    d.ellipse([(c - r, c - r), (c + r, c + r)], fill=(*C_YELLOW, 255), outline=(*C_BEIGE, 255), width=4)
    f = get_font("anton", int(round(s * 0.44)))
    bb = f.getbbox("VS")
    d.text((c - (bb[2] - bb[0]) / 2.0 - bb[0], c - (bb[3] - bb[1]) / 2.0 - bb[1]), "VS", font=f, fill=(*C_INK, 255))
    return im


def _make_footer_note(text: str, font_size: int = 30) -> Image.Image:
    """Crisp archival typewriter footer tag for Beat 6."""
    f = get_font("typewriter", font_size)
    bb = f.getbbox(text)
    tw, th = max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
    pad_x, pad_y = 26, 13
    im = Image.new("RGBA", (tw + pad_x * 2, th + pad_y * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(
        [(2, 2), (im.width - 3, im.height - 3)],
        radius=8,
        fill=(*C_BEIGE, 245),
        outline=(*C_INK, 220),
        width=2,
    )
    d.text((pad_x - bb[0], pad_y - bb[1]), text, font=f, fill=(*C_INK, 255))
    return im


def _impact_shake(t: float, hits: List[float], max_px: float = 4.0) -> Tuple[int, int]:
    """Damped 4 px stamp-impact tremor lasting 0.25s without single-frame spikes."""
    ox, oy = 0.0, 0.0
    for ht in hits:
        dt = t - ht
        if 0.0 <= dt < 0.26:
            env = math.exp(-dt * 12.0) * (1.0 - dt / 0.26)
            ox += math.sin(dt * 42.0) * max_px * env
            oy += math.cos(dt * 36.0) * (max_px * 0.85) * env
    return int(round(ox)), int(round(oy))


def _paste_with_shake(frame: Image.Image, sx: int, sy: int) -> Image.Image:
    """Apply subtle damped camera shake while keeping border edges clean."""
    if sx == 0 and sy == 0:
        return frame
    w, h = frame.size
    out = frame.copy()
    out.paste(frame, (sx, sy))
    return out


def get_config(aspect: str = "9:16", fps: int = DEFAULT_FPS, duration: float = DURATION_SEC) -> VideoConfig:
    return VideoConfig.from_aspect(aspect=aspect, fps=fps, duration=duration)


def get_init_args(cfg: VideoConfig) -> dict:
    return {
        "width": cfg.width,
        "height": cfg.height,
        "fps": cfg.fps,
        "duration": cfg.duration,
        "map_cache": str(DEFAULT_MAP_CACHE),
    }


def build_audio(wav_path: Path, config: VideoConfig) -> Path:
    """Synthesize royalty-free editorial documentary bed + 39 beat-synced organic SFX."""
    mixer = SoundMixer(duration=config.duration, seed=42)
    mixer.add_editorial_bed(bpm=108.0, gain=0.14)

    # Beat 1 (0.00 - 6.00s): Hook
    mixer.add_sfx(0.05, "slap", amp=0.85)
    mixer.add_sfx(0.25, "coin_clink", amp=0.95)
    mixer.add_sfx(1.60, "stamp_thud", amp=1.00)
    mixer.add_sfx(3.60, "scissor_snip", amp=0.90)
    mixer.add_sfx(3.70, "coin_clink", amp=0.85)

    # Beat 2 (6.00 - 17.00s): Natural Earth map journey
    mixer.add_sfx(6.00, "whoosh", amp=0.85, dur=0.42)
    mixer.add_sfx(6.20, "slap", amp=0.75)
    mixer.add_sfx(6.80, "type_tick", amp=0.95)
    mixer.add_sfx(7.15, "type_tick", amp=0.95)
    mixer.add_sfx(7.90, "slap", amp=0.80)
    mixer.add_sfx(8.40, "coin_clink", amp=0.75)
    mixer.add_sfx(10.05, "whoosh", amp=0.90, dur=0.58)
    mixer.add_sfx(10.45, "paper_rip", amp=0.85)
    mixer.add_sfx(12.20, "whoosh", amp=0.65, dur=0.45)
    mixer.add_sfx(14.50, "whoosh", amp=0.80, dur=0.38)
    mixer.add_sfx(14.80, "type_tick", amp=1.00)
    mixer.add_sfx(15.05, "stamp_thud", amp=1.00)

    # Beat 3 (17.00 - 29.50s): Torn receipt stack
    mixer.add_sfx(17.02, "paper_rip", amp=0.85)
    mixer.add_sfx(17.20, "slap", amp=0.85)
    mixer.add_sfx(18.85, "slap", amp=0.85)
    mixer.add_sfx(20.45, "slap", amp=0.88)
    mixer.add_sfx(22.05, "slap", amp=0.92)
    mixer.add_sfx(22.17, "coin_clink", amp=0.80)
    mixer.add_sfx(23.60, "slap", amp=0.95)
    mixer.add_sfx(23.72, "coin_clink", amp=0.90)
    mixer.add_sfx(25.50, "scissor_snip", amp=0.88)
    mixer.add_sfx(26.40, "stamp_thud", amp=1.00)

    # Beat 4 (29.50 - 36.50s): 7-bar breakdown chart
    mixer.add_sfx(29.55, "paper_rip", amp=0.85)
    mixer.add_sfx(30.10, "type_tick", amp=0.80)
    mixer.add_sfx(30.80, "type_tick", amp=0.80)
    mixer.add_sfx(31.50, "type_tick", amp=0.82)
    mixer.add_sfx(32.20, "type_tick", amp=0.82)
    mixer.add_sfx(33.00, "coin_clink", amp=0.85)
    mixer.add_sfx(33.80, "slap", amp=0.80)

    # Beat 5 (36.50 - 43.00s): Horizontal torn black curtain shock comparison
    mixer.add_sfx(36.50, "paper_rip", amp=1.00)
    mixer.add_sfx(37.30, "slap", amp=0.90)
    mixer.add_sfx(37.85, "slap", amp=0.90)
    mixer.add_sfx(39.50, "stamp_thud", amp=1.00)
    mixer.add_sfx(39.58, "coin_clink", amp=0.85)

    # Beat 6 (43.00 - 48.00s): Skill sign-off
    mixer.add_sfx(43.00, "paper_rip", amp=0.90)
    mixer.add_sfx(43.25, "slap", amp=0.85)
    mixer.add_sfx(43.80, "slap", amp=0.85)
    mixer.add_sfx(44.35, "slap", amp=0.90)
    mixer.add_sfx(45.20, "stamp_thud", amp=1.00)

    return mixer.export_wav(wav_path)


def init_worker(cfg_dict: dict) -> None:
    """Pre-build deterministic paper assets, icons, strips, receipts, stamps, and map camera."""
    w = int(cfg_dict["width"])
    h = int(cfg_dict["height"])
    fps = int(cfg_dict["fps"])
    dur = float(cfg_dict["duration"])
    is_wide = w > h

    STATE.clear()
    STATE["w"] = w
    STATE["h"] = h
    STATE["fps"] = fps
    STATE["dur"] = dur
    STATE["is_wide"] = is_wide

    STATE["board"] = build_cream_board(w, h, grid_step=88)
    STATE["tex"], STATE["dusts"] = build_paper_overlay(w, h, seed=42)
    STATE["map"] = MapCamera(Path(cfg_dict["map_cache"]))
    STATE["subs"] = captions_to_groups(TIMED_CAPTIONS, max_chars=20, duration=dur)

    max_strip_w = int(w * (0.46 if is_wide else 0.90))
    max_wide_strip_w = int(w * (0.76 if is_wide else 0.92))

    # --- Beat 1 assets ---
    STATE["b1_hdr"] = _fit_width(
        make_torn_strip(
            "TÜRKİYE · 2026 KAFE LATTE",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=44 if is_wide else 48,
            pad_x=44,
            pad_y=18,
            seed=101,
            icon="coffee",
        ),
        max_wide_strip_w,
    )
    STATE["b1_cup"] = make_procedural_halftone_icon(
        "coffee_cup",
        size=390 if is_wide else 345,
        accent=C_YELLOW,
        seed=102,
    )
    STATE["b1_price"] = _fit_width(
        make_torn_strip(
            "180 TL",
            bg=C_YELLOW,
            fg=C_INK,
            font_size=112 if is_wide else 120,
            pad_x=64,
            pad_y=20,
            red_underline=1.0,
            seed=103,
        ),
        max_strip_w,
    )
    STATE["b1_stamp"] = _fit_width(
        make_red_stamp_on_slip("ÇİFTÇİYE NE KALIR?", font_size=56 if is_wide else 62, seed=104, with_slip=True),
        int(w * (0.48 if is_wide else 0.90)),
    )
    STATE["b1_shock"] = _fit_width(
        make_torn_strip(
            "SADECE 6 TL · %3",
            bg=C_BEIGE,
            fg=C_RED,
            font_size=52 if is_wide else 56,
            pad_x=46,
            pad_y=18,
            red_underline=1.0,
            seed=105,
            icon="warning",
        ),
        max_strip_w,
    )

    # --- Beat 2 assets (Map) ---
    STATE["b2_origin_hdr"] = _fit_width(
        make_torn_strip(
            "BREZİLYA & KOLOMBİYA",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=46 if is_wide else 50,
            pad_x=46,
            pad_y=18,
            seed=201,
            icon="pin",
        ),
        max_wide_strip_w,
    )
    STATE["b2_bean"] = make_procedural_halftone_icon(
        "coffee_bean",
        size=210 if is_wide else 200,
        accent=C_YELLOW,
        seed=202,
    )
    STATE["b2_gram"] = _fit_width(
        make_torn_strip(
            "22g YEŞİL ÇEKİRDEK",
            bg=C_BEIGE,
            fg=C_INK,
            font_size=40 if is_wide else 44,
            pad_x=42,
            pad_y=15,
            seed=203,
        ),
        int(w * (0.36 if is_wide else 0.84)),
    )
    STATE["b2_ico"] = _fit_width(
        make_torn_strip(
            "ICO ~$5/KG · ÇİFTÇİ",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=36 if is_wide else 40,
            pad_x=42,
            pad_y=14,
            seed=204,
        ),
        int(w * (0.36 if is_wide else 0.84)),
    )
    STATE["b2_ship"] = make_procedural_halftone_icon(
        "cargo_ship",
        size=185 if is_wide else 175,
        accent=C_RED,
        seed=205,
    )
    STATE["b2_km"] = _fit_width(
        make_torn_strip(
            "10.500 KM · DENİZ YOLU",
            bg=C_RED,
            fg=C_BEIGE,
            font_size=46 if is_wide else 50,
            pad_x=48,
            pad_y=18,
            seed=206,
        ),
        max_wide_strip_w,
    )
    STATE["b2_tr_hdr"] = _fit_width(
        make_torn_strip(
            "İSTANBUL · TÜRKİYE",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=46 if is_wide else 50,
            pad_x=46,
            pad_y=18,
            seed=207,
            icon="pin",
        ),
        max_wide_strip_w,
    )
    STATE["b2_stamp"] = _fit_width(
        make_red_stamp_on_slip("ÇİFTÇİ PAYI: ~6 TL", font_size=58 if is_wide else 64, seed=208, with_slip=True),
        int(w * (0.52 if is_wide else 0.90)),
    )

    # --- Beat 3 assets (Receipts) ---
    STATE["b3_hdr"] = _fit_width(
        make_torn_strip(
            "KALAN 174 TL NEREDE?",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=46 if is_wide else 52,
            pad_x=46,
            pad_y=18,
            seed=301,
            icon="doc",
        ),
        max_wide_strip_w,
    )
    STATE["b3_specs"] = [
        ("#01", "Nakliye & Kavurma", "12 TL", C_INK, 17.20, 311),
        ("#02", "Süt, Bardak & Kapak", "14 TL", C_INK, 18.85, 312),
        ("#03", "KDV (%10) + POS", "21 TL", C_INK, 20.45, 313),
        ("#04", "Barista & Personel", "49 TL", C_YELLOW, 22.05, 314),
        ("#05", "Kira, Stopaj & Enerji", "58 TL", C_RED, 23.60, 315),
    ]
    rec_w = 840 if is_wide else 870
    rec_h = 94 if is_wide else 98
    STATE["b3_rec_w"] = rec_w
    STATE["b3_rec_h"] = rec_h
    # Pre-cache fully lit receipts for fast rendering after fill completes
    STATE["b3_lit_cache"] = [
        make_torn_receipt(idx, title, price, lit_p=1.0, seed=sd, badge_color=col, width=rec_w, height=rec_h)
        for idx, title, price, col, _, sd in STATE["b3_specs"]
    ]
    STATE["b3_roll"] = make_procedural_halftone_icon("receipt_roll", size=290, accent=C_YELLOW, seed=320)
    STATE["b3_coins"] = make_procedural_halftone_icon("coin_stack", size=195 if is_wide else 185, accent=C_YELLOW, seed=321)
    STATE["b3_profit"] = _fit_width(
        make_torn_strip(
            "+ KAFE NET KÂRI: 20 TL (%11)",
            bg=C_GREEN,
            fg=C_BEIGE,
            font_size=36 if is_wide else 38,
            pad_x=42,
            pad_y=15,
            seed=322,
            icon="check",
        ),
        int(w * (0.42 if is_wide else 0.90)),
    )
    STATE["b3_stamp"] = _fit_width(
        make_red_stamp_on_slip("KİRA + İŞÇİLİK = %59", font_size=52 if is_wide else 58, seed=323, with_slip=True),
        int(w * (0.44 if is_wide else 0.90)),
    )
    STATE["b3_sub107"] = _fit_width(
        make_torn_strip(
            "107 TL / 180 TL",
            bg=C_YELLOW,
            fg=C_INK,
            font_size=40 if is_wide else 42,
            pad_x=44,
            pad_y=13,
            red_underline=1.0,
            seed=324,
        ),
        int(w * (0.36 if is_wide else 0.68)),
    )

    # --- Beat 4 assets (Bar Chart) ---
    chart_w = 1040 if is_wide else 900
    chart_h = 680 if is_wide else 780
    STATE["b4_chart_w"] = chart_w
    STATE["b4_chart_h"] = chart_h
    STATE["b4_chart_full"] = _fit_width(
        make_bar_chart_card(
            "180 TL LATTE KIRILIMI (2026)",
            BREAKDOWN_ITEMS,
            progress=1.0,
            width=chart_w,
            height=chart_h,
            seed=401,
        ),
        int(w * (0.64 if is_wide else 0.96)),
    )
    STATE["b4_hdr"] = _fit_width(
        make_torn_strip(
            "7 KALEMDE TAM KIRILIM",
            bg=C_INK,
            fg=C_YELLOW,
            font_size=38 if is_wide else 46,
            pad_x=44,
            pad_y=16,
            seed=402,
        ),
        int(w * (0.34 if is_wide else 0.88)),
    )
    STATE["b4_total"] = _fit_width(
        make_torn_strip(
            "TOPLAM: 180 TL",
            bg=C_YELLOW,
            fg=C_INK,
            font_size=40 if is_wide else 44,
            pad_x=44,
            pad_y=14,
            red_underline=1.0,
            seed=403,
        ),
        int(w * (0.32 if is_wide else 0.68)),
    )
    STATE["b4_glass"] = make_procedural_halftone_icon(
        "magnifying_glass",
        size=210 if is_wide else 200,
        accent=C_RED,
        seed=404,
    )
    STATE["b4_coins"] = make_procedural_halftone_icon(
        "coin_stack",
        size=240 if is_wide else 185,
        accent=C_YELLOW,
        seed=405,
    )

    # --- Beat 5 assets (Horizontal torn black curtain comparison) ---
    split_y = 370 if is_wide else 685
    STATE["b5_split_y"] = split_y
    STATE["b5_curtain"] = make_horizontal_torn_curtain(w, h, split_y=split_y, fill_color=C_BLACK_PAPER, edge_color=C_BEIGE, seed=501)
    STATE["b5_bean"] = make_procedural_halftone_icon("coffee_bean", size=225 if is_wide else 235, accent=C_YELLOW, seed=502)
    STATE["b5_cup"] = make_procedural_halftone_icon("paper_cup", size=225 if is_wide else 235, accent=C_RED, seed=503)
    STATE["b5_lbl_farmer"] = _fit_width(
        make_torn_strip("ÇİFTÇİ: 6 TL", bg=C_YELLOW, fg=C_INK, font_size=42 if is_wide else 44, pad_x=38, pad_y=14, seed=504),
        int(w * (0.28 if is_wide else 0.45)),
    )
    STATE["b5_lbl_cup"] = _fit_width(
        make_torn_strip("BARDAK: 5 TL", bg=C_RED, fg=C_BEIGE, font_size=42 if is_wide else 44, pad_x=38, pad_y=14, seed=505),
        int(w * (0.28 if is_wide else 0.45)),
    )
    STATE["b5_vs"] = _make_vs_badge(86 if is_wide else 80)
    STATE["b5_stamp"] = _fit_width(
        make_red_stamp_on_slip("NEREDEYSE AYNI!", font_size=56 if is_wide else 66, seed=506, with_slip=True),
        int(w * (0.40 if is_wide else 0.88)),
    )

    # --- Beat 6 assets (Skill sign-off) ---
    STATE["b6_term"] = make_procedural_halftone_icon("code_terminal", size=330 if is_wide else 260, accent=C_YELLOW, seed=601)
    STATE["b6_s1"] = _fit_width(
        make_torn_strip("0 AFTER EFFECTS", bg=C_INK, fg=C_YELLOW, font_size=46 if is_wide else 50, pad_x=44, pad_y=16, seed=602, icon="check"),
        int(w * (0.46 if is_wide else 0.86)),
    )
    STATE["b6_s2"] = _fit_width(
        make_torn_strip("$0 API MALİYETİ", bg=C_BEIGE, fg=C_INK, font_size=46 if is_wide else 50, pad_x=44, pad_y=16, seed=603, icon="check"),
        int(w * (0.46 if is_wide else 0.86)),
    )
    STATE["b6_s3"] = _fit_width(
        make_torn_strip("24 FPS · SAF PYTHON", bg=C_YELLOW, fg=C_INK, font_size=46 if is_wide else 50, pad_x=44, pad_y=16, seed=604, icon="check"),
        int(w * (0.46 if is_wide else 0.86)),
    )
    STATE["b6_stamp"] = _fit_width(
        make_red_stamp_on_slip("SPHYREX-VOX-SKILL", font_size=56 if is_wide else 60, seed=605, with_slip=True),
        int(w * (0.48 if is_wide else 0.90)),
    )
    STATE["b6_note"] = _fit_width(
        _make_footer_note("MIT Open Source · Natural Earth 1:50m", font_size=28 if is_wide else 30),
        int(w * (0.46 if is_wide else 0.90)),
    )


def _render_beat1(frame: Image.Image, f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> None:
    """0.00 - 6.00s: Explosive Frame-0 Hook."""
    end_f = int(round(6.00 * fps))
    if is_wide:
        composite_smooth(frame, STATE["b1_hdr"], w * 0.50, h * 0.125, f, 0, end_f, fps=fps, in_dur=1, out_dur=6, slide_in=(0, -18), rot=-0.5)
        composite_smooth(frame, STATE["b1_cup"], w * 0.27, h * 0.525, f, 0, end_f, fps=fps, in_dur=1, out_dur=6, rot=-3.0, float_amp=5.0)
        composite_smooth(frame, STATE["b1_price"], w * 0.67, h * 0.32, f, int(round(0.25 * fps)), end_f, fps=fps, in_dur=6, out_dur=6, slide_in=(0, 30), rot=1.1)
        composite_smooth(frame, STATE["b1_stamp"], w * 0.67, h * 0.53, f, int(round(1.60 * fps)), end_f, fps=fps, in_dur=5, out_dur=6, rot=-2.4, stamp_pop=True)
        composite_smooth(frame, STATE["b1_shock"], w * 0.67, h * 0.74, f, int(round(3.60 * fps)), end_f, fps=fps, in_dur=6, out_dur=6, slide_in=(48, 12), rot=0.9)
    else:
        composite_smooth(frame, STATE["b1_hdr"], w * 0.50, h * 0.125, f, 0, end_f, fps=fps, in_dur=1, out_dur=6, slide_in=(0, -18), rot=-0.7)
        composite_smooth(frame, STATE["b1_cup"], w * 0.50, h * 0.305, f, 0, end_f, fps=fps, in_dur=1, out_dur=6, rot=-2.5, float_amp=5.5)
        composite_smooth(frame, STATE["b1_price"], w * 0.50, h * 0.485, f, int(round(0.25 * fps)), end_f, fps=fps, in_dur=6, out_dur=6, slide_in=(0, 28), rot=1.2)
        composite_smooth(frame, STATE["b1_stamp"], w * 0.50, h * 0.618, f, int(round(1.60 * fps)), end_f, fps=fps, in_dur=5, out_dur=6, rot=-2.6, stamp_pop=True)
        composite_smooth(frame, STATE["b1_shock"], w * 0.50, h * 0.735, f, int(round(3.60 * fps)), end_f, fps=fps, in_dur=6, out_dur=6, slide_in=(0, 40), rot=0.8)


def _render_beat2(f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> Image.Image:
    """6.00 - 17.00s: Natural Earth 1:50m World Map (BRA/COL -> 10,500 km -> IST/TUR)."""
    cam: MapCamera = STATE["map"]

    # Smooth camera keyframes across 6.00 -> 17.00s
    if t < 10.00:
        u = smoothstep((t - 6.00) / 4.00)
        lon = -62.0 + 4.0 * u
        lat = -9.5 + 1.5 * u
        zoom = (0.76 + 0.07 * u) if is_wide else (0.86 + 0.08 * u)
    elif t < 14.50:
        u = smoothstep((t - 10.00) / 4.50)
        lon = -58.0 + (29.0 - (-58.0)) * u
        # Gentle northward arch across the Atlantic
        lat = -8.0 + (37.5 - (-8.0)) * u + 4.0 * math.sin(math.pi * u)
        # Zoom out gently over mid-Atlantic so both continents & route breathe
        z_start = 0.83 if is_wide else 0.94
        z_mid = 0.52 if is_wide else 0.65
        z_end = 1.05 if is_wide else 1.15
        if u < 0.5:
            v = smoothstep(u * 2.0)
            zoom = z_start + (z_mid - z_start) * v
        else:
            v = smoothstep((u - 0.5) * 2.0)
            zoom = z_mid + (z_end - z_mid) * v
    else:
        u = smoothstep((t - 14.50) / 2.50)
        lon = 29.0 + 4.0 * u
        lat = 37.5 + 1.0 * u
        zoom = (1.05 + 0.14 * u) if is_wide else (1.15 + 0.14 * u)

    highlights: Dict[str, Tuple[float, Tuple[int, int, int]]] = {}
    bra_p = clamp01((t - 6.20) / 0.90)
    col_p = clamp01((t - 6.60) / 0.90)
    tur_p = clamp01((t - 14.55) / 0.85)
    if bra_p > 0.0:
        highlights["BRA"] = (bra_p, C_YELLOW)
    if col_p > 0.0:
        highlights["COL"] = (col_p, C_YELLOW)
    if tur_p > 0.0:
        highlights["TUR"] = (tur_p, C_YELLOW)

    cam_cx, cam_cy, _, _, _, _, eff_zoom = cam.compute_viewport(lon, lat, zoom, w, h)
    frame = cam.render_view(lon, lat, eff_zoom, w, h, highlights=highlights).convert("RGBA")

    # Geodesic red ribbon from Brazil to Istanbul (10.20 -> 14.20s reveal)
    ribbon_p = smoothstep((t - 10.20) / 4.00)
    arc_pts = cam.screen_arc_points(
        BRA_PORT[0], BRA_PORT[1],
        IST_CITY[0], IST_CITY[1],
        cam_cx, cam_cy, eff_zoom, w, h,
        n=96, lift=0.14,
    )
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    if ribbon_p > 0.01:
        draw_red_ribbon(od, arc_pts, reveal=ribbon_p, width=10 if is_wide else 11)

    # Brass pins at Brazil, Colombia, Istanbul
    pin_scale = 1.15 if is_wide else 1.25
    if t >= 6.75:
        a = int(255 * clamp01((t - 6.75) / 0.25))
        sc = pin_scale * (0.4 + 0.6 * ease_out_cubic((t - 6.75) / 0.25))
        bx, by = cam.project(BRA_PORT[0], BRA_PORT[1], cam_cx, cam_cy, eff_zoom, w, h)
        draw_brass_pin(od, bx, by, scale=sc, alpha=a)
    if t >= 7.10:
        a = int(255 * clamp01((t - 7.10) / 0.25))
        sc = pin_scale * (0.4 + 0.6 * ease_out_cubic((t - 7.10) / 0.25))
        cx_, cy_ = cam.project(COL_BELT[0], COL_BELT[1], cam_cx, cam_cy, eff_zoom, w, h)
        draw_brass_pin(od, cx_, cy_, scale=sc, alpha=a)
    if t >= 14.75:
        a = int(255 * clamp01((t - 14.75) / 0.25))
        sc = pin_scale * (0.4 + 0.6 * ease_out_cubic((t - 14.75) / 0.25))
        ix, iy = cam.project(IST_CITY[0], IST_CITY[1], cam_cx, cam_cy, eff_zoom, w, h)
        draw_brass_pin(od, ix, iy, scale=sc, alpha=a)

    frame.alpha_composite(overlay)

    # Gliding cargo ship riding the tip of the red ribbon (10.35 -> 14.35s)
    if 10.35 <= t < 14.40:
        ship_idx = min(len(arc_pts) - 1, max(0, int(round(ribbon_p * (len(arc_pts) - 1)))))
        sx, sy = arc_pts[ship_idx]
        bob = math.sin(t * 7.5) * 6.0
        composite_smooth(
            frame,
            STATE["b2_ship"],
            sx,
            sy - 36 + bob,
            f,
            int(round(10.35 * fps)),
            int(round(14.40 * fps)),
            fps=fps,
            in_dur=6,
            out_dur=6,
            slide_in=(0, 12),
            rot=-4.0 + 3.0 * math.sin(t * 4.5),
        )

    # Beat 2 sub-beat overlays
    f_61 = int(round(6.15 * fps))
    f_100 = int(round(10.05 * fps))
    f_104 = int(round(10.45 * fps))
    f_144 = int(round(14.45 * fps))
    f_146 = int(round(14.60 * fps))
    f_150 = int(round(15.05 * fps))
    f_170 = int(round(17.00 * fps))

    if is_wide:
        composite_smooth(frame, STATE["b2_origin_hdr"], w * 0.50, h * 0.115, f, f_61, f_100, fps=fps, rot=-0.6)
        composite_smooth(frame, STATE["b2_bean"], w * 0.80, h * 0.36, f, int(round(7.40 * fps)), f_100, fps=fps, rot=4.0, float_amp=5.0)
        composite_smooth(frame, STATE["b2_gram"], w * 0.80, h * 0.57, f, int(round(7.90 * fps)), f_100, fps=fps, slide_in=(40, 0), rot=-0.8)
        composite_smooth(frame, STATE["b2_ico"], w * 0.80, h * 0.70, f, int(round(8.40 * fps)), f_100, fps=fps, slide_in=(40, 0), rot=0.8)

        composite_smooth(frame, STATE["b2_km"], w * 0.50, h * 0.13, f, f_104, f_144, fps=fps, slide_in=(0, -24), rot=-0.7)

        composite_smooth(frame, STATE["b2_tr_hdr"], w * 0.50, h * 0.12, f, f_146, f_170, fps=fps, rot=-0.5)
        composite_smooth(frame, STATE["b2_stamp"], w * 0.50, h * 0.70, f, f_150, f_170, fps=fps, rot=-2.2, stamp_pop=True)
    else:
        composite_smooth(frame, STATE["b2_origin_hdr"], w * 0.50, h * 0.12, f, f_61, f_100, fps=fps, rot=-0.7)
        composite_smooth(frame, STATE["b2_bean"], w * 0.22, h * 0.655, f, int(round(7.40 * fps)), f_100, fps=fps, rot=5.0, float_amp=5.0)
        composite_smooth(frame, STATE["b2_gram"], w * 0.62, h * 0.625, f, int(round(7.90 * fps)), f_100, fps=fps, slide_in=(38, 0), rot=-0.8)
        composite_smooth(frame, STATE["b2_ico"], w * 0.62, h * 0.71, f, int(round(8.40 * fps)), f_100, fps=fps, slide_in=(38, 0), rot=0.9)

        composite_smooth(frame, STATE["b2_km"], w * 0.50, h * 0.135, f, f_104, f_144, fps=fps, slide_in=(0, -24), rot=-0.8)

        composite_smooth(frame, STATE["b2_tr_hdr"], w * 0.50, h * 0.125, f, f_146, f_170, fps=fps, rot=-0.6)
        composite_smooth(frame, STATE["b2_stamp"], w * 0.50, h * 0.69, f, f_150, f_170, fps=fps, rot=-2.4, stamp_pop=True)

    return frame


def _render_beat3(frame: Image.Image, f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> None:
    """17.00 - 29.50s: Where does the remaining 174 TL go? (Torn receipts + %59 stamp)."""
    f_start = int(round(17.05 * fps))
    f_end = int(round(29.50 * fps))

    hdr_y = h * (0.105 if is_wide else 0.108)
    composite_smooth(frame, STATE["b3_hdr"], w * 0.50, hdr_y, f, f_start, f_end, fps=fps, slide_in=(0, -24), rot=-0.5)

    specs = STATE["b3_specs"]
    lit_cache = STATE["b3_lit_cache"]
    rec_w = STATE["b3_rec_w"]
    rec_h = STATE["b3_rec_h"]

    for i, (idx_tag, title, price, col, t_in, sd) in enumerate(specs):
        sf = int(round(t_in * fps))
        if f < sf:
            continue
        lit_p = clamp01((t - (t_in + 0.12)) / 0.45)
        if lit_p >= 0.999:
            rec_im = lit_cache[i]
        else:
            rec_im = make_torn_receipt(idx_tag, title, price, lit_p=lit_p, seed=sd, badge_color=col, width=rec_w, height=rec_h)

        rot_i = -0.6 if i % 2 == 0 else 0.55
        if is_wide:
            rx = w * 0.295
            ry = 250 + i * 124
            composite_smooth(frame, rec_im, rx, ry, f, sf, f_end, fps=fps, in_dur=6, out_dur=6, slide_in=(-45, 0), rot=rot_i)
        else:
            rx = w * 0.50
            ry = 345 + i * 122
            composite_smooth(frame, rec_im, rx, ry, f, sf, f_end, fps=fps, in_dur=6, out_dur=6, slide_in=(0, 32), rot=rot_i)

    # Right column (16:9) or clean lower band (9:16) — zero overlap over receipts!
    f_profit = int(round(25.50 * fps))
    f_stamp = int(round(26.40 * fps))
    f_sub = int(round(26.85 * fps))
    if is_wide:
        composite_smooth(frame, STATE["b3_roll"], w * 0.77, h * 0.43, f, int(round(17.40 * fps)), int(round(25.45 * fps)), fps=fps, rot=-3.5, float_amp=5.0)
        composite_smooth(frame, STATE["b3_coins"], w * 0.77, h * 0.69, f, int(round(22.10 * fps)), int(round(25.45 * fps)), fps=fps, rot=3.0, float_amp=4.0)

        composite_smooth(frame, STATE["b3_profit"], w * 0.76, h * 0.30, f, f_profit, f_end, fps=fps, slide_in=(38, 0), rot=-0.7)
        composite_smooth(frame, STATE["b3_stamp"], w * 0.76, h * 0.51, f, f_stamp, f_end, fps=fps, rot=-2.5, stamp_pop=True)
        composite_smooth(frame, STATE["b3_sub107"], w * 0.76, h * 0.71, f, f_sub, f_end, fps=fps, slide_in=(0, 24), rot=0.9)
    else:
        composite_smooth(frame, STATE["b3_profit"], w * 0.50, 1025, f, f_profit, f_end, fps=fps, slide_in=(0, 28), rot=-0.6)
        composite_smooth(frame, STATE["b3_stamp"], w * 0.50, 1210, f, f_stamp, f_end, fps=fps, rot=-2.4, stamp_pop=True)
        composite_smooth(frame, STATE["b3_sub107"], w * 0.50, 1385, f, f_sub, f_end, fps=fps, slide_in=(0, 24), rot=0.9)


def _render_beat4(frame: Image.Image, f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> None:
    """29.50 - 36.50s: Animated 7-item Breakdown Bar Chart + Magnifying Glass & Coin Stack."""
    f_start = int(round(29.55 * fps))
    f_end = int(round(36.50 * fps))

    bar_prog = clamp01((t - 29.85) / 3.20)
    if bar_prog >= 0.999:
        chart_im = STATE["b4_chart_full"]
    else:
        raw_chart = make_bar_chart_card(
            "180 TL LATTE KIRILIMI (2026)",
            BREAKDOWN_ITEMS,
            progress=bar_prog,
            width=STATE["b4_chart_w"],
            height=STATE["b4_chart_h"],
            seed=401,
        )
        chart_im = _fit_width(raw_chart, int(w * (0.64 if is_wide else 0.96)))

    # Smooth magnifying glass sweep down to the tiny bottom "Çiftçi (22g): 6 TL" bar
    scan_u = smoothstep((t - 31.20) / 3.40)

    if is_wide:
        composite_smooth(frame, chart_im, w * 0.365, h * 0.445, f, f_start, f_end, fps=fps, in_dur=7, out_dur=6, slide_in=(0, 26), rot=-0.4)
        composite_smooth(frame, STATE["b4_hdr"], w * 0.815, h * 0.22, f, int(round(29.70 * fps)), f_end, fps=fps, slide_in=(36, 0), rot=0.7)
        composite_smooth(frame, STATE["b4_total"], w * 0.815, h * 0.365, f, int(round(33.75 * fps)), f_end, fps=fps, slide_in=(36, 0), rot=-0.9)
        composite_smooth(frame, STATE["b4_coins"], w * 0.815, h * 0.64, f, int(round(30.40 * fps)), f_end, fps=fps, rot=3.5, float_amp=5.0)

        # Magnifying glass sweeps over open gray track area without obscuring right-side TL numbers
        gx = w * (0.50 - 0.16 * scan_u)
        gy = h * (0.52 + 0.21 * scan_u)
        composite_smooth(frame, STATE["b4_glass"], gx, gy, f, int(round(30.80 * fps)), f_end, fps=fps, out_dur=4, rot=-14.0 + 10.0 * scan_u, float_amp=3.5)
    else:
        composite_smooth(frame, STATE["b4_hdr"], w * 0.50, h * 0.115, f, f_start, f_end, fps=fps, out_dur=4, slide_in=(0, -22), rot=-0.6)
        composite_smooth(frame, chart_im, w * 0.50, h * 0.435, f, f_start, f_end, fps=fps, in_dur=7, out_dur=4, slide_in=(0, 28), rot=-0.35)
        composite_smooth(frame, STATE["b4_coins"], w * 0.21, h * 0.708, f, int(round(30.40 * fps)), f_end, fps=fps, out_dur=4, rot=-4.0, float_amp=4.5)
        composite_smooth(frame, STATE["b4_total"], w * 0.58, h * 0.715, f, int(round(33.75 * fps)), f_end, fps=fps, out_dur=4, slide_in=(32, 0), rot=0.9)

        gx = w * (0.68 - 0.22 * scan_u)
        gy = h * (0.53 + 0.095 * scan_u)
        composite_smooth(frame, STATE["b4_glass"], gx, gy, f, int(round(30.80 * fps)), f_end, fps=fps, out_dur=4, rot=-12.0 + 8.0 * scan_u, float_amp=3.5)


def _render_beat5(f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> Image.Image:
    """36.50 - 43.00s: Uncut top map + rising horizontal torn black curtain shock comparison."""
    cam: MapCamera = STATE["map"]

    # Frame the top map so Atlantic ribbon + yellow Turkey + Istanbul pin sit clearly in the uncut top band
    u_drift = clamp01((t - 36.50) / 6.50)
    if is_wide:
        lon = -6.0 + 8.0 * u_drift
        lat = 6.0 + 2.5 * u_drift
        zoom = 0.43 + 0.03 * u_drift
    else:
        lon = 15.0 + 7.0 * u_drift
        lat = 18.0 + 2.0 * u_drift
        zoom = 0.64 + 0.03 * u_drift

    cam_cx, cam_cy, _, _, _, _, eff_zoom = cam.compute_viewport(lon, lat, zoom, w, h)
    frame = cam.render_view(
        lon,
        lat,
        eff_zoom,
        w,
        h,
        highlights={"BRA": (1.0, C_YELLOW), "COL": (1.0, C_YELLOW), "TUR": (1.0, C_YELLOW)},
    ).convert("RGBA")

    arc_pts = cam.screen_arc_points(
        BRA_PORT[0], BRA_PORT[1],
        IST_CITY[0], IST_CITY[1],
        cam_cx, cam_cy, eff_zoom, w, h,
        n=96, lift=0.14,
    )
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    draw_red_ribbon(od, arc_pts, reveal=1.0, width=9 if is_wide else 10)
    bx, by = cam.project(BRA_PORT[0], BRA_PORT[1], cam_cx, cam_cy, eff_zoom, w, h)
    ix, iy = cam.project(IST_CITY[0], IST_CITY[1], cam_cx, cam_cy, eff_zoom, w, h)
    draw_brass_pin(od, bx, by, scale=1.05, alpha=255)
    draw_brass_pin(od, ix, iy, scale=1.05, alpha=255)
    frame.alpha_composite(ov)

    # Rising horizontal torn black curtain (36.50 -> 37.25s)
    rise_p = ease_out_cubic(clamp01((t - 36.50) / 0.72))
    curtain: Image.Image = STATE["b5_curtain"]
    split_y: int = STATE["b5_split_y"]
    curtain_y_offset = int(round((1.0 - rise_p) * (h - split_y + 40)))
    if curtain_y_offset < h:
        frame.alpha_composite(curtain, (0, max(0, curtain_y_offset)))

    f_left = int(round(37.25 * fps))
    f_right = int(round(37.75 * fps))
    f_vs = int(round(37.55 * fps))
    f_stamp = int(round(39.50 * fps))
    f_end = int(round(43.00 * fps))

    if is_wide:
        composite_smooth(frame, STATE["b5_bean"], w * 0.215, h * 0.535, f, f_left, f_end, fps=fps, slide_in=(-35, 16), rot=-4.0, float_amp=4.5)
        composite_smooth(frame, STATE["b5_lbl_farmer"], w * 0.215, h * 0.735, f, f_left + 2, f_end, fps=fps, slide_in=(0, 22), rot=-0.9)

        composite_smooth(frame, STATE["b5_cup"], w * 0.785, h * 0.535, f, f_right, f_end, fps=fps, slide_in=(35, 16), rot=4.0, float_amp=4.5)
        composite_smooth(frame, STATE["b5_lbl_cup"], w * 0.785, h * 0.735, f, f_right + 2, f_end, fps=fps, slide_in=(0, 22), rot=0.9)

        composite_smooth(frame, STATE["b5_vs"], w * 0.50, h * 0.56, f, f_vs, f_stamp + 2, fps=fps, in_dur=5, out_dur=4)
        composite_smooth(frame, STATE["b5_stamp"], w * 0.50, h * 0.62, f, f_stamp, f_end, fps=fps, rot=-2.8, stamp_pop=True)
    else:
        composite_smooth(frame, STATE["b5_bean"], w * 0.265, 895, f, f_left, f_end, fps=fps, slide_in=(-30, 18), rot=-4.0, float_amp=4.5)
        composite_smooth(frame, STATE["b5_lbl_farmer"], w * 0.265, 1085, f, f_left + 2, f_end, fps=fps, slide_in=(0, 24), rot=-1.1)

        composite_smooth(frame, STATE["b5_cup"], w * 0.735, 895, f, f_right, f_end, fps=fps, slide_in=(30, 18), rot=4.0, float_amp=4.5)
        composite_smooth(frame, STATE["b5_lbl_cup"], w * 0.735, 1085, f, f_right + 2, f_end, fps=fps, slide_in=(0, 24), rot=1.1)

        composite_smooth(frame, STATE["b5_vs"], w * 0.50, 915, f, f_vs, f_end, fps=fps, in_dur=5, out_dur=5)
        composite_smooth(frame, STATE["b5_stamp"], w * 0.50, 1320, f, f_stamp, f_end, fps=fps, rot=-2.6, stamp_pop=True)

    return frame


def _render_beat6(frame: Image.Image, f: int, t: float, w: int, h: int, fps: int, is_wide: bool) -> None:
    """43.00 - 48.00s: Skill Sign-off & Open Source Stamp."""
    f_end = int(round(48.50 * fps))  # Stay solid through the final frame (no empty fade-out)

    # Retracting torn black curtain reveals the parchment desk (43.00 -> 43.42s)
    if t < 43.45:
        drop_p = ease_in_cubic(clamp01((t - 43.00) / 0.42))
        curtain: Image.Image = STATE["b5_curtain"]
        split_y: int = STATE["b5_split_y"]
        cy_off = int(round(drop_p * (h - split_y + 40)))
        if cy_off < h:
            frame.alpha_composite(curtain, (0, max(0, cy_off)))

    f_term = int(round(43.08 * fps))
    f_s1 = int(round(43.25 * fps))
    f_s2 = int(round(43.80 * fps))
    f_s3 = int(round(44.35 * fps))
    f_stamp = int(round(45.20 * fps))
    f_note = int(round(45.45 * fps))

    if is_wide:
        composite_smooth(frame, STATE["b6_term"], w * 0.27, h * 0.43, f, f_term, f_end, fps=fps, out_dur=1, rot=-2.5, float_amp=4.5)
        composite_smooth(frame, STATE["b6_note"], w * 0.27, h * 0.72, f, f_note, f_end, fps=fps, out_dur=1, slide_in=(0, 16))

        composite_smooth(frame, STATE["b6_s1"], w * 0.69, h * 0.19, f, f_s1, f_end, fps=fps, out_dur=1, slide_in=(42, 0), rot=-0.6)
        composite_smooth(frame, STATE["b6_s2"], w * 0.69, h * 0.335, f, f_s2, f_end, fps=fps, out_dur=1, slide_in=(42, 0), rot=0.6)
        composite_smooth(frame, STATE["b6_s3"], w * 0.69, h * 0.48, f, f_s3, f_end, fps=fps, out_dur=1, slide_in=(42, 0), rot=-0.5)
        composite_smooth(frame, STATE["b6_stamp"], w * 0.69, h * 0.695, f, f_stamp, f_end, fps=fps, out_dur=1, rot=-2.2, stamp_pop=True)
    else:
        composite_smooth(frame, STATE["b6_term"], w * 0.50, 295, f, f_term, f_end, fps=fps, out_dur=1, rot=-2.2, float_amp=4.5)
        composite_smooth(frame, STATE["b6_s1"], w * 0.50, 560, f, f_s1, f_end, fps=fps, out_dur=1, slide_in=(0, 26), rot=-0.7)
        composite_smooth(frame, STATE["b6_s2"], w * 0.50, 725, f, f_s2, f_end, fps=fps, out_dur=1, slide_in=(0, 26), rot=0.7)
        composite_smooth(frame, STATE["b6_s3"], w * 0.50, 890, f, f_s3, f_end, fps=fps, out_dur=1, slide_in=(0, 26), rot=-0.6)
        composite_smooth(frame, STATE["b6_stamp"], w * 0.50, 1145, f, f_stamp, f_end, fps=fps, out_dur=1, rot=-2.3, stamp_pop=True)
        composite_smooth(frame, STATE["b6_note"], w * 0.50, 1380, f, f_note, f_end, fps=fps, out_dur=1, slide_in=(0, 14))


def render_frame(f: int) -> bytes:
    w: int = STATE["w"]
    h: int = STATE["h"]
    fps: int = STATE["fps"]
    is_wide: bool = STATE["is_wide"]
    t = f / float(fps)

    if t < 6.00:
        frame = STATE["board"].convert("RGBA")
        _render_beat1(frame, f, t, w, h, fps, is_wide)
    elif t < 17.00:
        frame = _render_beat2(f, t, w, h, fps, is_wide)
    elif t < 29.50:
        frame = STATE["board"].convert("RGBA")
        _render_beat3(frame, f, t, w, h, fps, is_wide)
    elif t < 36.50:
        frame = STATE["board"].convert("RGBA")
        _render_beat4(frame, f, t, w, h, fps, is_wide)
    elif t < 43.00:
        frame = _render_beat5(f, t, w, h, fps, is_wide)
    else:
        frame = STATE["board"].convert("RGBA")
        _render_beat6(frame, f, t, w, h, fps, is_wide)

    # Damped 4 px impact tremor on key stamp hits
    sx, sy = _impact_shake(t, [1.60, 15.05, 26.40, 39.50, 45.20], max_px=4.0)
    if sx != 0 or sy != 0:
        frame = _paste_with_shake(frame, sx, sy)

    # Rock-steady single-line editorial subtitles (zero jitter)
    draw_subtitle_bar(frame, t, STATE["subs"], w, h)

    return apply_paper_overlay(frame, STATE["tex"], STATE["dusts"], f).tobytes()


def render_to_file(
    out_mp4: Path,
    aspect: str = "9:16",
    fps: int = DEFAULT_FPS,
    workers: Optional[int] = None,
    normalize: bool = True,
) -> Path:
    import tempfile

    cfg = VideoConfig.from_aspect(aspect=aspect, fps=fps, duration=DURATION_SEC, workers=workers)
    with tempfile.TemporaryDirectory(prefix="vox_audio_") as td:
        audio_wav = Path(td) / "mix.wav"
        build_audio(audio_wav, cfg)
        return render_scene(
            cfg,
            init_worker,
            get_init_args(cfg),
            render_frame,
            audio_wav,
            out_mp4,
            normalize=normalize,
        )


if __name__ == "__main__":
    out_default = SCENE_DIR / "out" / "kahve-demo.mp4"
    render_to_file(out_default, aspect="9:16", fps=DEFAULT_FPS)
