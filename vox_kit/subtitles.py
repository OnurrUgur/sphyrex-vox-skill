"""Rock-steady single-line subtitles with active-word highlight and zero vertical jitter."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from PIL import Image, ImageDraw

from .palette import C_BEIGE, C_INK, C_YELLOW, get_font

WordTuple = Tuple[float, float, str]
SubGroup = Tuple[float, float, List[WordTuple]]


@dataclass(frozen=True)
class TimedCaption:
    """Caption segment for voiceover-free / music-only editorial videos."""

    start: float
    end: float
    text: str


def _clean_len_text(word: str) -> str:
    return word.replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip()


def _normalize_words(words: Iterable[Union[WordTuple, Sequence, dict]]) -> List[WordTuple]:
    out: List[WordTuple] = []
    for item in words:
        if isinstance(item, dict):
            s = float(item.get("start", item.get("s", 0.0)))
            e = float(item.get("end", item.get("e", s + 0.2)))
            w = str(item.get("word", item.get("text", item.get("w", "")))).strip()
        else:
            s, e, w = float(item[0]), float(item[1]), str(item[2]).strip()
        if w:
            out.append((s, max(s + 0.02, e), w))
    out.sort(key=lambda x: x[0])
    return out


def group_whisper_words(
    words: Iterable[Union[WordTuple, Sequence, dict]],
    max_chars: int = 17,
    max_gap: float = 0.45,
    duration: Optional[float] = None,
) -> List[SubGroup]:
    """Group word timestamps into guaranteed single-line bars (<= max_chars) with zero flicker."""
    norm = _normalize_words(words)
    if not norm:
        return []

    groups: List[SubGroup] = []
    cur: List[WordTuple] = []

    for w in norm:
        if duration is not None and w[0] > duration:
            break
        clean_w = _clean_len_text(w[2])
        cur_txt = " ".join(_clean_len_text(x[2]) for x in cur)
        gap_too_big = bool(cur and (w[0] - cur[-1][1]) > max_gap)
        too_long = bool(cur and (len(cur_txt) + 1 + len(clean_w)) > max_chars)

        if cur and (len(cur) >= 3 or too_long or gap_too_big):
            groups.append((cur[0][0], cur[-1][1], list(cur)))
            cur = []

        cur.append(w)
        if w[2][-1:] in ".?!":
            groups.append((cur[0][0], cur[-1][1], list(cur)))
            cur = []

    if cur:
        groups.append((cur[0][0], cur[-1][1], list(cur)))

    if not groups:
        return []

    end_limit = duration if duration is not None else (groups[-1][1] + 0.25)
    smoothed: List[SubGroup] = []
    for i, (b0, e0, kk) in enumerate(groups):
        if i + 1 < len(groups):
            nxt_b = groups[i + 1][0]
            if nxt_b - e0 <= max_gap:
                e_fin = nxt_b
            else:
                e_fin = min(nxt_b, e0 + 0.14)
        else:
            e_fin = min(end_limit, e0 + 0.35) if duration is not None else e0 + 0.20
            e_fin = max(e_fin, e0)
        smoothed.append((b0, e_fin, kk))
    return smoothed


def captions_to_groups(
    captions: Iterable[Union[TimedCaption, Tuple[float, float, str]]],
    max_chars: int = 17,
    max_gap: float = 0.45,
    duration: Optional[float] = None,
) -> List[SubGroup]:
    """Convert TimedCaption or (start_s, end_s, text) items into word-timed subtitle groups."""
    word_list: List[WordTuple] = []
    for cap in captions:
        if isinstance(cap, TimedCaption):
            s0, e0, text = float(cap.start), float(cap.end), cap.text
        else:
            s0, e0, text = float(cap[0]), float(cap[1]), str(cap[2])
        tokens = [tok for tok in text.strip().split() if tok]
        if not tokens or e0 <= s0:
            continue
        weights = [max(2, len(_clean_len_text(tok))) for tok in tokens]
        tot_w = float(sum(weights))
        span = e0 - s0
        cur_t = s0
        for tok, wt in zip(tokens, weights):
            dt = span * (wt / tot_w)
            word_list.append((cur_t, cur_t + dt, tok))
            cur_t += dt
    return group_whisper_words(word_list, max_chars=max_chars, max_gap=max_gap, duration=duration)


def draw_subtitle_bar(
    frame: Image.Image,
    t: float,
    sub_groups: Sequence[SubGroup],
    w: int,
    h: int,
) -> None:
    """Draw a fixed dark archival subtitle strip with yellow active-word highlight (0 px jitter)."""
    sub_g = next((kk for b, e, kk in sub_groups if b <= t < e), None)
    if not sub_g:
        return

    is_landscape = w > h
    short_side = min(w, h)
    font_size = max(16, int(round(short_side * (0.044 if is_landscape else 0.046))))
    fs_sub = get_font("sora", font_size)

    gap_w = max(8, int(round(font_size * 0.36)))
    pad_x = max(18, int(round(font_size * 0.72)))
    bar_h = max(36, int(round(font_size * 1.84)))

    ws = [max(1, fs_sub.getbbox(word)[2] - fs_sub.getbbox(word)[0]) for _, _, word in sub_g]
    tot_w = sum(ws) + gap_w * (len(sub_g) - 1)

    margin_x = max(20, int(round(w * 0.033)))
    bx0 = max(margin_x, int(round(w / 2.0 - tot_w / 2.0 - pad_x)))
    bx1 = min(w - margin_x, int(round(w / 2.0 + tot_w / 2.0 + pad_x)))

    if is_landscape:
        by0 = int(round(h * 0.855))
    else:
        by0 = int(round(h * 0.802))
    by1 = min(h - 16, by0 + bar_h)

    sd = ImageDraw.Draw(frame)
    sh_x = max(3, int(round(font_size * 0.12)))
    sh_y = max(4, int(round(font_size * 0.16)))
    border_w = max(2, int(round(font_size * 0.08)))

    sd.rectangle([(bx0 + sh_x, by0 + sh_y), (bx1 + sh_x, by1 + sh_y)], fill=(*C_INK, 110))
    sd.rectangle([(bx0, by0), (bx1, by1)], fill=(*C_INK, 255), outline=(*C_YELLOW, 255), width=border_w)

    # Fixed vertical baseline computed from reference glyphs so the bar never jitters vertically
    ref_bb = fs_sub.getbbox("HgŞÇ")
    ref_h = max(1, ref_bb[3] - ref_bb[1])
    text_y = by0 + (by1 - by0 - ref_h) // 2 - ref_bb[1]

    cx_s = w / 2.0 - tot_w / 2.0
    for idx, (wb, _, wtxt) in enumerate(sub_g):
        active = t >= wb - 0.04
        passed = idx + 1 < len(sub_g) and t >= sub_g[idx + 1][0] - 0.04
        is_now = active and not passed
        col = (*C_YELLOW, 255) if is_now else ((*C_BEIGE, 255) if active else (145, 140, 134, 255))
        sd.text((cx_s, text_y), wtxt, font=fs_sub, fill=col)
        cx_s += ws[idx] + gap_w
