"""Public API for sphyrex-vox-skill (`vox_kit`)."""
from __future__ import annotations

from .elements import (
    apply_vox_colored_cutout,
    composite_smooth,
    draw_brass_pin,
    draw_check,
    draw_red_ribbon,
    draw_star,
    make_bar_chart_card,
    make_procedural_halftone_icon,
    make_red_stamp_on_slip,
    make_search_slip,
    make_step_card,
    make_torn_receipt,
    make_torn_strip,
)
from .map_engine import MapCamera, MapProjection, build_map_cache, paint_region
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
    C_TAPE,
    C_YELLOW,
    PALETTE,
    clamp01,
    ease_in_cubic,
    ease_out_back,
    ease_out_cubic,
    get_assets_dir,
    get_font,
    smoothstep,
)
from .paper import (
    add_paper_shadow,
    apply_paper_overlay,
    build_cream_board,
    build_paper_overlay,
    make_horizontal_torn_curtain,
    make_masking_tape,
    torn_rect_polygon,
)
from .renderer import (
    ASPECT_PRESETS,
    VideoConfig,
    check_video,
    make_contact_sheet,
    probe_video,
    render_scene,
)
from .sfx import SoundMixer, apply_loudnorm
from .subtitles import TimedCaption, captions_to_groups, draw_subtitle_bar, group_whisper_words

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Palette & easing
    "C_BOARD",
    "C_BEIGE",
    "C_INK",
    "C_BLACK_PAPER",
    "C_YELLOW",
    "C_RED",
    "C_RED_DARK",
    "C_TAPE",
    "C_BRASS",
    "C_MUTED",
    "C_GREEN",
    "PALETTE",
    "get_assets_dir",
    "get_font",
    "clamp01",
    "smoothstep",
    "ease_out_cubic",
    "ease_in_cubic",
    "ease_out_back",
    # Paper
    "build_paper_overlay",
    "apply_paper_overlay",
    "build_cream_board",
    "torn_rect_polygon",
    "make_masking_tape",
    "add_paper_shadow",
    "make_horizontal_torn_curtain",
    # Elements
    "draw_star",
    "draw_check",
    "make_torn_strip",
    "make_red_stamp_on_slip",
    "apply_vox_colored_cutout",
    "draw_brass_pin",
    "draw_red_ribbon",
    "make_torn_receipt",
    "make_step_card",
    "make_search_slip",
    "make_bar_chart_card",
    "make_procedural_halftone_icon",
    "composite_smooth",
    # Map engine
    "MapProjection",
    "build_map_cache",
    "MapCamera",
    "paint_region",
    # SFX
    "SoundMixer",
    "apply_loudnorm",
    # Subtitles
    "TimedCaption",
    "group_whisper_words",
    "captions_to_groups",
    "draw_subtitle_bar",
    # Renderer & QA
    "ASPECT_PRESETS",
    "VideoConfig",
    "render_scene",
    "probe_video",
    "check_video",
    "make_contact_sheet",
]
