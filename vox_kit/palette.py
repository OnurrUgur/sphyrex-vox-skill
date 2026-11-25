"""Fixed Hybrid Vox x Engraving v6 color palette, font loader, and easing curves."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import ImageFont

# =========================================================================
# Fixed Palette (Hybrid Vox x Engraving v6)
# =========================================================================
C_BOARD: Tuple[int, int, int] = (239, 234, 224)        # #EFEAE0 Warm Parchment
C_BEIGE: Tuple[int, int, int] = (244, 239, 229)        # #F4EFE5 Cream Paper
C_INK: Tuple[int, int, int] = (26, 25, 29)             # #1A191D Deep Ink
C_BLACK_PAPER: Tuple[int, int, int] = (20, 20, 23)     # #141417 Torn Black Paper
C_YELLOW: Tuple[int, int, int] = (235, 186, 44)        # #EBBA2C Mustard Yellow
C_RED: Tuple[int, int, int] = (208, 46, 42)            # #D02E2A Stamp Red
C_RED_DARK: Tuple[int, int, int] = (156, 28, 26)       # #9C1C1A Deep Stamp Red
C_TAPE: Tuple[int, int, int] = (232, 221, 192)         # #E8DDC0 Masking Tape
C_BRASS: Tuple[int, int, int] = (212, 168, 72)         # #D4A848 Brass Pin
C_MUTED: Tuple[int, int, int] = (112, 107, 99)         # #706B63 Archival Muted Ink
C_GREEN: Tuple[int, int, int] = (47, 143, 107)         # #2F8F6B Patina Green

PALETTE: Dict[str, Tuple[int, int, int]] = {
    "board": C_BOARD,
    "beige": C_BEIGE,
    "ink": C_INK,
    "black_paper": C_BLACK_PAPER,
    "yellow": C_YELLOW,
    "red": C_RED,
    "red_dark": C_RED_DARK,
    "tape": C_TAPE,
    "brass": C_BRASS,
    "muted": C_MUTED,
    "green": C_GREEN,
}

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_assets_dir() -> Path:
    """Locate the package assets directory without relying on user-specific paths."""
    env_dir = os.environ.get("VOX_KIT_ASSETS")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if p.exists():
            return p
    pkg_root = Path(__file__).resolve().parent
    for candidate in (pkg_root.parent / "assets", pkg_root / "assets"):
        if candidate.exists():
            return candidate
    return pkg_root.parent / "assets"


def _bundled_font(filename: str) -> Path:
    return get_assets_dir() / "fonts" / filename


def _font_candidates(key: str) -> List[Path]:
    """Return ordered font file candidates: bundled assets first, then cross-platform system fonts."""
    k = key.lower().strip()
    bundled_map: Dict[str, List[str]] = {
        "anton": ["Anton-Regular.ttf"],
        "sora": ["Sora-SemiBold.ttf", "Sora-Medium.ttf"],
        "sora_medium": ["Sora-Medium.ttf", "Sora-SemiBold.ttf"],
        "cinzel": ["Cinzel-Black.ttf"],
        "caslon": ["Cinzel-Black.ttf"],
        "serif_bold": ["Sora-SemiBold.ttf", "Cinzel-Black.ttf"],
        "serif_italic": ["Sora-Medium.ttf"],
        "typewriter": ["Sora-SemiBold.ttf", "Sora-Medium.ttf"],
        "marker": ["Anton-Regular.ttf"],
    }
    system_map: Dict[str, List[str]] = {
        "caslon": [
            "/System/Library/Fonts/Supplemental/BigCaslon.ttf",
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ],
        "serif_bold": [
            "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ],
        "serif_italic": [
            "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        ],
        "typewriter": [
            "/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc",
            "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        ],
        "marker": [
            "/System/Library/Fonts/MarkerFelt.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "anton": [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "sora": [
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "sora_medium": [
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
        "cinzel": [
            "/System/Library/Fonts/Supplemental/BigCaslon.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ],
    }

    candidates: List[Path] = []
    # Prefer bundled fonts for bundled brand keys; for editorial serif/typewriter,
    # try authentic system fonts first if present, then bundled fonts so output stays crisp everywhere.
    if k in ("anton", "sora", "sora_medium", "cinzel"):
        for fn in bundled_map.get(k, []):
            candidates.append(_bundled_font(fn))
        for sp in system_map.get(k, []):
            candidates.append(Path(sp))
    else:
        for sp in system_map.get(k, []):
            candidates.append(Path(sp))
        for fn in bundled_map.get(k, []):
            candidates.append(_bundled_font(fn))

    # Universal bundled fallbacks before Pillow default bitmap font
    for fallback_fn in ("Sora-SemiBold.ttf", "Anton-Regular.ttf", "Sora-Medium.ttf", "Cinzel-Black.ttf"):
        p = _bundled_font(fallback_fn)
        if p not in candidates:
            candidates.append(p)
    return candidates


def get_font(key: str, size: int) -> ImageFont.ImageFont:
    """Load and cache a font by semantic key and pixel size with safe cross-platform fallbacks."""
    sz = max(8, int(round(size)))
    cache_key = (key, sz)
    cached = _FONT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    for candidate in _font_candidates(key):
        if candidate.is_file():
            try:
                font = ImageFont.truetype(str(candidate), sz)
                _FONT_CACHE[cache_key] = font
                return font
            except OSError:
                continue

    # Final Pillow fallback (supports size kwarg on Pillow >= 10.1)
    try:
        font = ImageFont.load_default(size=sz)
    except TypeError:
        font = ImageFont.load_default()
    _FONT_CACHE[cache_key] = font
    return font


# =========================================================================
# Easing Functions
# =========================================================================
def clamp01(u: float) -> float:
    return 0.0 if u < 0.0 else (1.0 if u > 1.0 else float(u))


def smoothstep(u: float) -> float:
    u = clamp01(u)
    return u * u * (3.0 - 2.0 * u)


def ease_out_cubic(u: float) -> float:
    u = clamp01(u)
    return 1.0 - (1.0 - u) ** 3


def ease_in_cubic(u: float) -> float:
    u = clamp01(u)
    return u * u * u


def ease_out_back(u: float, overshoot: float = 0.85) -> float:
    u = clamp01(u)
    c3 = overshoot + 1.0
    return 1.0 + c3 * ((u - 1.0) ** 3) + overshoot * ((u - 1.0) ** 2)
