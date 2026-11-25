"""Multiprocessing ffmpeg renderer, video QA checker (broken frames + LUFS), and contact sheets."""
from __future__ import annotations

import importlib.util
import json
import math
import multiprocessing as mp
import os
import pickle
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from .sfx import _safe_media_path, apply_loudnorm

_VALID_PRESETS = frozenset(
    {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}
)

ASPECT_PRESETS: Dict[str, Tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}


@dataclass(frozen=True)
class VideoConfig:
    """Video render dimensions, frame rate, duration, and encoder settings."""

    width: int = 1080
    height: int = 1920
    fps: int = 24
    duration: float = 10.0
    workers: Optional[int] = None
    crf: int = 17
    preset: str = "medium"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or (self.width % 2) != 0 or (self.height % 2) != 0:
            raise ValueError(f"Video dimensions must be positive even integers, got {self.width}x{self.height}")
        if self.fps <= 0 or self.fps > 240:
            raise ValueError(f"fps must be between 1 and 240, got {self.fps}")
        if not math.isfinite(self.duration) or self.duration <= 0:
            raise ValueError(f"duration must be positive and finite, got {self.duration}")
        if not (0 <= int(self.crf) <= 51):
            raise ValueError(f"crf must be between 0 and 51, got {self.crf}")
        if self.preset not in _VALID_PRESETS:
            raise ValueError(f"Unsupported x264 preset {self.preset!r}. Choose from: {sorted(_VALID_PRESETS)}")

    @property
    def total_frames(self) -> int:
        return max(1, int(round(self.duration * self.fps)))

    @classmethod
    def from_aspect(
        cls,
        aspect: str = "9:16",
        fps: int = 24,
        duration: float = 10.0,
        workers: Optional[int] = None,
        crf: int = 17,
        preset: str = "medium",
    ) -> "VideoConfig":
        key = str(aspect).strip()
        if key not in ASPECT_PRESETS:
            raise ValueError(f"Unsupported aspect {aspect!r}. Choose from: {sorted(ASPECT_PRESETS)}")
        w, h = ASPECT_PRESETS[key]
        return cls(
            width=w,
            height=h,
            fps=int(fps),
            duration=float(duration),
            workers=workers,
            crf=int(crf),
            preset=str(preset),
        )


def _to_rgb24_bytes(frame_out: Union[bytes, bytearray, np.ndarray, Image.Image], w: int, h: int) -> bytes:
    if isinstance(frame_out, (bytes, bytearray)):
        raw = bytes(frame_out)
    elif isinstance(frame_out, np.ndarray):
        arr = np.ascontiguousarray(frame_out, dtype=np.uint8)
        raw = arr.tobytes()
    elif isinstance(frame_out, Image.Image):
        im = frame_out.convert("RGB")
        if im.size != (w, h):
            im = im.resize((w, h), Image.Resampling.BILINEAR)
        raw = im.tobytes()
    else:
        raise TypeError(f"frame_fn must return bytes, ndarray, or PIL.Image; got {type(frame_out).__name__}")
    expected = w * h * 3
    if len(raw) != expected:
        raise ValueError(f"Frame byte size mismatch: expected {expected} ({w}x{h}x3), got {len(raw)}")
    return raw


def _is_picklable(obj: Any) -> bool:
    try:
        pickle.dumps(obj)
        return True
    except Exception:
        return False


def render_scene(
    config: VideoConfig,
    init_fn: Optional[Callable[[Any], Any]],
    init_args: Any,
    frame_fn: Callable[[int], Union[bytes, np.ndarray, Image.Image]],
    audio_wav: Optional[Union[str, Path]],
    out_mp4: Union[str, Path],
    normalize: bool = True,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """
    Render frames in parallel (or in-process for short clips), pipe RGB24 to ffmpeg,
    and optionally apply 2-pass EBU R128 loudnorm (-14 LUFS, -1.5 dBTP).
    """
    out_path = _safe_media_path(out_mp4)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = config.total_frames

    has_audio = audio_wav is not None
    audio_path = _safe_media_path(audio_wav) if has_audio else None
    if audio_path is not None and not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if normalize and has_audio:
        with tempfile.NamedTemporaryFile(
            prefix=f".{out_path.stem}.vox_raw_",
            suffix=out_path.suffix,
            dir=str(out_path.parent),
            delete=False,
        ) as tf:
            raw_mp4 = Path(tf.name)
    else:
        raw_mp4 = out_path

    ff_cmd: List[str] = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{config.width}x{config.height}",
        "-r",
        str(config.fps),
        "-i",
        "-",
    ]
    if audio_path is not None:
        ff_cmd.extend(["-i", str(audio_path)])
    ff_cmd.extend(
        [
            "-c:v",
            "libx264",
            "-crf",
            str(config.crf),
            "-pix_fmt",
            "yuv420p",
            "-preset",
            config.preset,
            "-movflags",
            "+faststart",
        ]
    )
    if has_audio:
        ff_cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])
    ff_cmd.append(str(raw_mp4))

    default_workers = min(6, max(2, (os.cpu_count() or 4) - 2)) if total >= 48 else 1
    workers = config.workers if config.workers is not None else default_workers
    workers = max(1, int(workers))

    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        use_pool = workers > 1 and total >= 12
        pool_ctx = None
        if use_pool:
            if sys.platform != "win32":
                try:
                    pool_ctx = mp.get_context("fork")
                except ValueError:
                    pool_ctx = None
            if (
                pool_ctx is None
                and _is_picklable(frame_fn)
                and (init_fn is None or _is_picklable(init_fn))
                and _is_picklable(init_args)
            ):
                mod_name = getattr(frame_fn, "__module__", "")
                if mod_name and importlib.util.find_spec(mod_name) is not None:
                    pool_ctx = mp.get_context()

        if pool_ctx is not None:
            init_tuple = (init_args,) if init_fn is not None else ()
            with pool_ctx.Pool(
                workers,
                initializer=init_fn,
                initargs=init_tuple,
            ) as pool:
                chunk = max(1, min(8, total // (workers * 2) or 1))
                for idx, frame_out in enumerate(pool.imap(frame_fn, range(total), chunksize=chunk)):
                    proc.stdin.write(_to_rgb24_bytes(frame_out, config.width, config.height))
                    if progress_cb is not None:
                        progress_cb(idx + 1, total)
        else:
            if init_fn is not None:
                init_fn(init_args)
            for idx in range(total):
                frame_out = frame_fn(idx)
                proc.stdin.write(_to_rgb24_bytes(frame_out, config.width, config.height))
                if progress_cb is not None:
                    progress_cb(idx + 1, total)
    except BaseException:
        try:
            proc.stdin.close()
        except OSError:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        if raw_mp4.exists() and raw_mp4 != out_path:
            raw_mp4.unlink()
        raise
    else:
        try:
            proc.stdin.close()
        except OSError:
            pass

    ret = proc.wait()
    if ret != 0:
        if raw_mp4.exists() and raw_mp4 != out_path:
            raw_mp4.unlink()
        raise RuntimeError(f"ffmpeg video encode failed with exit code {ret}")

    if normalize and has_audio:
        try:
            apply_loudnorm(raw_mp4, out_path, target_i=-14.0, target_tp=-1.5)
        finally:
            if raw_mp4.exists() and raw_mp4 != out_path:
                raw_mp4.unlink()

    return out_path


def _parse_fps(rate_str: str) -> float:
    if not rate_str or rate_str == "0/0":
        return 0.0
    if "/" in rate_str:
        num, den = rate_str.split("/", 1)
        d = float(den)
        return float(num) / d if d > 0 else 0.0
    return float(rate_str)


def probe_video(mp4_path: Union[str, Path]) -> Dict[str, Any]:
    """Read video stream metadata (width, height, real fps, duration) using ffprobe."""
    p = _safe_media_path(mp4_path)
    if not p.is_file():
        raise FileNotFoundError(f"Video file not found: {p}")
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,duration,nb_frames",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            "-i",
            str(p),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(res.stdout)
    streams = info.get("streams") or []
    if not streams:
        raise RuntimeError(f"No video stream found in {p}")
    st = streams[0]
    fps = _parse_fps(st.get("avg_frame_rate") or "") or _parse_fps(st.get("r_frame_rate") or "") or 24.0
    dur = float(st.get("duration") or info.get("format", {}).get("duration") or 0.0)
    return {
        "width": int(st.get("width", 0)),
        "height": int(st.get("height", 0)),
        "fps": round(fps, 3),
        "duration": round(dur, 3),
    }


def check_video(
    mp4_path: Union[str, Path],
    lufs_min: float = -16.0,
    lufs_max: float = -12.0,
) -> Dict[str, Any]:
    """
    Scan rendered video for single-frame visual glitches and verify audio loudness (-16..-12 LUFS).
    Reads actual FPS via ffprobe instead of hardcoding 30 FPS.
    """
    p = _safe_media_path(mp4_path)
    meta = probe_video(p)
    fps = meta["fps"] or 24.0

    # 1. Single-frame glitch scan (neighbor-similarity detector)
    sw, sh = 192, 108
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(p),
            "-vf",
            f"scale={sw}:{sh},format=gray",
            "-f",
            "rawvideo",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    assert proc.stdout is not None
    frames: List[np.ndarray] = []
    frame_bytes = sw * sh
    while True:
        chunk = proc.stdout.read(frame_bytes)
        if len(chunk) < frame_bytes:
            break
        frames.append(np.frombuffer(chunk, np.uint8).astype(np.int16))
    proc.stdout.close()
    decode_rc = proc.wait()

    def _diff(a: int, b: int) -> float:
        return float(np.abs(frames[a] - frames[b]).mean())

    broken: List[Dict[str, Any]] = []
    for i in range(1, len(frames) - 1):
        da = _diff(i - 1, i)
        db = _diff(i, i + 1)
        dc = _diff(i - 1, i + 1)
        if da > 6.0 and db > 6.0 and dc < da * 0.35 and dc < db * 0.35:
            broken.append(
                {
                    "frame": i,
                    "time_s": round(i / fps, 3),
                    "diff_prev": round(da, 2),
                    "diff_next": round(db, 2),
                    "diff_neighbors": round(dc, 2),
                }
            )

    # 2. Integrated LUFS + True Peak measurement
    aud = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(p),
            "-af",
            "loudnorm=print_format=summary",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    i_matches = re.findall(r"Input Integrated:\s+(-?[\d.]+|-inf)", aud.stderr)
    tp_matches = re.findall(r"Input True Peak:\s+(-?[\d.]+|-inf)", aud.stderr)

    errors: List[str] = []
    if decode_rc != 0 or not frames:
        errors.append(f"Failed to decode video frames cleanly (ffmpeg exit={decode_rc}, frames={len(frames)})")
    if broken:
        errors.append(f"Found {len(broken)} broken single-frame glitch(es)")

    lufs: Optional[float] = None
    true_peak: Optional[float] = None
    lufs_ok = False
    if not i_matches:
        errors.append("No audio stream or loudness could not be measured")
    else:
        raw_i = i_matches[-1]
        lufs = float(raw_i) if raw_i != "-inf" else -99.0
        if tp_matches:
            raw_tp = tp_matches[-1]
            true_peak = float(raw_tp) if raw_tp != "-inf" else -99.0
        lufs_ok = lufs_min <= lufs <= lufs_max
        if not lufs_ok:
            errors.append(
                f"Loudness {lufs:.1f} LUFS is outside target window [{lufs_min:.1f}, {lufs_max:.1f}] LUFS"
            )

    return {
        "ok": len(errors) == 0,
        "path": str(p),
        "width": meta["width"],
        "height": meta["height"],
        "fps": fps,
        "duration": meta["duration"],
        "total_frames": len(frames),
        "broken_frames": broken,
        "lufs": round(lufs, 2) if lufs is not None else None,
        "true_peak_dbtp": round(true_peak, 2) if true_peak is not None else None,
        "lufs_ok": lufs_ok,
        "errors": errors,
    }


def make_contact_sheet(
    mp4_path: Union[str, Path],
    out_dir: Union[str, Path],
    fps: float = 1.0,
    grid: str = "8x2",
    tile_width: int = 270,
) -> List[Path]:
    """Generate tiled JPEG contact sheets for visual QA inspection."""
    grid_s = str(grid).strip()
    m_grid = re.match(r"^(\d{1,2})x(\d{1,2})$", grid_s)
    if not m_grid or int(m_grid.group(1)) < 1 or int(m_grid.group(2)) < 1:
        raise ValueError(f"Invalid grid format {grid!r}; expected positive '<cols>x<rows>', e.g. '8x2'")
    fps_val = float(fps)
    if not math.isfinite(fps_val) or fps_val <= 0.0:
        raise ValueError(f"fps must be positive and finite, got {fps!r}")
    p = _safe_media_path(mp4_path)
    meta = probe_video(p)
    tw = max(64, min(1024, int(tile_width)))
    vw, vh = max(1, meta["width"]), max(1, meta["height"])
    th = max(64, (int(round(tw * vh / vw)) // 2) * 2)

    odir = _safe_media_path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)
    # Remove only numeric sheet_NN.jpg outputs from previous runs (never user files like sheet_custom.jpg)
    for old in odir.glob("sheet_*.jpg"):
        if re.fullmatch(r"sheet_\d+\.jpg", old.name):
            old.unlink()

    out_pattern = odir / "sheet_%02d.jpg"
    vf = f"fps={fps_val:.4f},scale={tw}:{th},tile={grid_s}"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(p),
            "-vf",
            vf,
            "-q:v",
            "3",
            str(out_pattern),
        ],
        check=True,
    )
    return sorted(f for f in odir.glob("sheet_*.jpg") if re.fullmatch(r"sheet_\d+\.jpg", f.name))
