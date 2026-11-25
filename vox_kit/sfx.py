"""Procedural organic SFX synthesis, royalty-free editorial music bed, audio mixer, and 2-pass loudnorm."""
from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Optional, Union

import numpy as np


def _safe_media_path(path: Union[str, Path]) -> Path:
    """Resolve media paths to absolute filesystem paths so leading '-' or protocols cannot inject ffmpeg flags."""
    raw = str(path)
    if "\x00" in raw:
        raise ValueError("Media path contains null byte")
    return Path(raw).expanduser().resolve()


class SoundMixer:
    """Deterministic NumPy audio mixer with organic paper/collage SFX and optional editorial bed."""

    def __init__(self, duration: float, sr: int = 48000, seed: int = 42):
        self.duration = max(0.1, float(duration))
        self.sr = int(sr)
        self.n_samples = int(round(self.duration * self.sr))
        self.rng = np.random.default_rng(seed)
        self._voice = np.zeros(self.n_samples, dtype=np.float32)
        self._bed = np.zeros(self.n_samples, dtype=np.float32)
        self._sfx = np.zeros(self.n_samples, dtype=np.float32)
        self._has_voice = False

    # =====================================================================
    # Organic Procedural SFX Generators
    # =====================================================================
    def slap(self) -> np.ndarray:
        """Crisp paper card slap."""
        n = max(16, int(0.065 * self.sr))
        t = np.linspace(0.0, 0.065, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        s = (
            0.65 * np.diff(ns, prepend=0.0) * np.exp(-t * 68.0)
            + 0.55 * np.sin(2.0 * math.pi * 160.0 * t * np.exp(-t * 14.0)) * np.exp(-t * 55.0)
        )
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def stamp_thud(self) -> np.ndarray:
        """Heavy rubber stamp slam onto desk."""
        n = max(16, int(0.115 * self.sr))
        t = np.linspace(0.0, 0.115, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        s = (
            0.82 * np.sin(2.0 * math.pi * 108.0 * t * np.exp(-t * 18.0)) * np.exp(-t * 34.0)
            + 0.42 * ns * np.exp(-t * 78.0)
        )
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def scissor_snip(self) -> np.ndarray:
        """Metallic editorial scissor snip."""
        n = max(16, int(0.085 * self.sr))
        t = np.linspace(0.0, 0.085, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        hp = ns - np.convolve(ns, np.ones(5, dtype=np.float32) / 5.0, mode="same")
        ring = (
            np.sin(2.0 * math.pi * 3400.0 * t) * np.exp(-t * 55.0)
            + 0.50 * np.sin(2.0 * math.pi * 5100.0 * t) * np.exp(-t * 70.0)
        )
        s = 0.65 * hp * np.exp(-t * 48.0) + 0.55 * ring
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def paper_rip(self) -> np.ndarray:
        """Textured paper tear / curtain rip."""
        n = max(16, int(0.22 * self.sr))
        t = np.linspace(0.0, 0.22, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        hp = ns - np.convolve(ns, np.ones(9, dtype=np.float32) / 9.0, mode="same")
        s = hp * (np.maximum(0.0, np.sin(math.pi * t / 0.22)) ** 0.8) * (0.7 + 0.3 * np.sin(2.0 * math.pi * 38.0 * t))
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def whoosh(self, dur: float = 0.36) -> np.ndarray:
        """Soft archival map camera pan whoosh."""
        d = max(0.08, float(dur))
        n = max(16, int(d * self.sr))
        t = np.linspace(0.0, d, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        lp = np.convolve(ns, np.ones(45, dtype=np.float32) / 45.0, mode="same")
        s = lp * (np.maximum(0.0, np.sin(math.pi * t / d)) ** 1.6)
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def coin_clink(self) -> np.ndarray:
        """Warm brass/coin double-clink for money & price hits."""
        dur = 0.18
        n = max(16, int(dur * self.sr))
        t = np.linspace(0.0, dur, n, dtype=np.float32)
        p1 = (
            0.55 * np.sin(2.0 * math.pi * 2620.0 * t) * np.exp(-t * 36.0)
            + 0.35 * np.sin(2.0 * math.pi * 4180.0 * t) * np.exp(-t * 48.0)
            + 0.20 * np.sin(2.0 * math.pi * 6350.0 * t) * np.exp(-t * 62.0)
        )
        t2 = np.maximum(0.0, t - 0.042)
        gate2 = (t >= 0.042).astype(np.float32)
        p2 = gate2 * (
            0.40 * np.sin(2.0 * math.pi * 2980.0 * t2) * np.exp(-t2 * 40.0)
            + 0.25 * np.sin(2.0 * math.pi * 4720.0 * t2) * np.exp(-t2 * 56.0)
        )
        s = p1 + p2
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    def type_tick(self) -> np.ndarray:
        """Mechanical typewriter keystroke click."""
        dur = 0.028
        n = max(16, int(dur * self.sr))
        t = np.linspace(0.0, dur, n, dtype=np.float32)
        ns = self.rng.normal(0.0, 1.0, n).astype(np.float32)
        s = (
            0.70 * np.diff(ns, prepend=0.0) * np.exp(-t * 170.0)
            + 0.45 * np.sin(2.0 * math.pi * 1850.0 * t) * np.exp(-t * 140.0)
        )
        return (s / (float(np.max(np.abs(s))) + 1e-6)).astype(np.float32)

    # =====================================================================
    # Tracks & Mixing
    # =====================================================================
    def add_voice(self, wav_path: Union[str, Path], gain: float = 1.0) -> None:
        """Load voiceover audio (resampled to mono self.sr via ffmpeg if needed)."""
        vp = _safe_media_path(wav_path)
        if not vp.is_file():
            raise FileNotFoundError(f"Voice file not found: {vp}")

        raw: Optional[np.ndarray] = None
        if vp.suffix.lower() == ".wav":
            try:
                with wave.open(str(vp), "rb") as wf:
                    if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == self.sr:
                        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            except wave.Error:
                raw = None

        if raw is None:
            with tempfile.TemporaryDirectory(prefix="vox_voice_") as td:
                tmp_wav = Path(td) / "voice_mono.wav"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-y",
                        "-i",
                        str(vp),
                        "-t",
                        f"{self.duration:.3f}",
                        "-ar",
                        str(self.sr),
                        "-ac",
                        "1",
                        str(tmp_wav),
                    ],
                    check=True,
                )
                with wave.open(str(tmp_wav), "rb") as wf:
                    raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

        count = min(len(raw), self.n_samples)
        self._voice[:count] += raw[:count] * float(gain)
        self._has_voice = True

    def add_editorial_bed(self, bpm: float = 108.0, gain: float = 0.14) -> None:
        """
        Synthesize a warm, minimalist, royalty-free editorial documentary music bed in pure NumPy.

        Combines a plucked muted bass, soft felt-marimba harmonic pulse, and subtle brushed ticks.
        """
        beat_s = 60.0 / max(40.0, float(bpm))
        eighth_s = beat_s * 0.5
        bed = np.zeros(self.n_samples, dtype=np.float32)

        # Warm documentary progression (Dm -> F -> C -> Gm) in Hz
        bass_roots = [73.42, 87.31, 65.41, 98.00]
        chords = [
            (293.66, 349.23, 440.00),  # Dm
            (349.23, 440.00, 523.25),  # F
            (261.63, 329.63, 392.00),  # C
            (293.66, 349.23, 392.00),  # Gm7/add4 warm tension
        ]

        # Precompute gentle percussive brushed shaker grain
        shaker_n = max(16, int(0.038 * self.sr))
        st = np.linspace(0.0, 0.038, shaker_n, dtype=np.float32)
        sh_noise = self.rng.normal(0.0, 1.0, shaker_n).astype(np.float32)
        sh_hp = sh_noise - np.convolve(sh_noise, np.ones(7, dtype=np.float32) / 7.0, mode="same")
        shaker = (sh_hp * np.exp(-st * 95.0) * 0.16).astype(np.float32)

        n_eighths = int(math.ceil(self.duration / eighth_s))
        for step in range(n_eighths):
            t0 = step * eighth_s
            idx0 = int(round(t0 * self.sr))
            if idx0 >= self.n_samples:
                break

            bar = (step // 8) % len(bass_roots)
            pos = step % 8

            # Plucked upright bass on beats 1, 2.5, 4
            if pos in (0, 3, 6):
                f0 = bass_roots[bar]
                dur = min(beat_s * 1.15, (self.n_samples - idx0) / self.sr)
                ln = max(1, int(round(dur * self.sr)))
                tt = np.linspace(0.0, dur, ln, dtype=np.float32)
                env = np.minimum(1.0, tt / 0.012) * np.exp(-tt * 4.2)
                sig = (
                    0.72 * np.sin(2.0 * math.pi * f0 * tt)
                    + 0.24 * np.sin(2.0 * math.pi * (f0 * 2.0) * tt) * np.exp(-tt * 7.0)
                    + 0.08 * np.sin(2.0 * math.pi * (f0 * 3.0) * tt) * np.exp(-tt * 12.0)
                ) * env
                end = min(self.n_samples, idx0 + ln)
                bed[idx0:end] += sig[: end - idx0] * 0.58

            # Warm felt-marimba arpeggio pulse on steady eighths
            chord = chords[bar]
            note_f = chord[(pos + bar) % len(chord)]
            if pos in (0, 2, 4, 5, 7):
                dur_m = min(eighth_s * 1.4, (self.n_samples - idx0) / self.sr)
                ln_m = max(1, int(round(dur_m * self.sr)))
                tt = np.linspace(0.0, dur_m, ln_m, dtype=np.float32)
                env = np.minimum(1.0, tt / 0.008) * np.exp(-tt * 8.5)
                amp_m = 0.26 if pos in (0, 4) else 0.16
                sig_m = (
                    0.85 * np.sin(2.0 * math.pi * note_f * tt)
                    + 0.15 * np.sin(2.0 * math.pi * (note_f * 2.0) * tt) * np.exp(-tt * 14.0)
                ) * env
                end_m = min(self.n_samples, idx0 + ln_m)
                bed[idx0:end_m] += sig_m[: end_m - idx0] * amp_m

            # Soft brushed tick on off-beats
            if pos % 2 == 1:
                end_s = min(self.n_samples, idx0 + shaker_n)
                bed[idx0:end_s] += shaker[: end_s - idx0]

        # Subtle warm sustained pad glued underneath for seamless loudness
        t_all = np.linspace(0.0, self.duration, self.n_samples, dtype=np.float32)
        pad = 0.12 * np.sin(2.0 * math.pi * 146.83 * t_all) + 0.08 * np.sin(2.0 * math.pi * 220.0 * t_all)
        bed += pad.astype(np.float32)

        # Gentle analog-style tape saturation so plucked peaks stay warm and RMS stays consistent
        bed = np.tanh(bed * 1.65).astype(np.float32)

        # Gentle fade-in / fade-out scaled safely for short clips
        fade_in_n = min(int(self.n_samples * 0.10), int(0.25 * self.sr))
        fade_out_n = min(int(self.n_samples * 0.15), int(0.60 * self.sr))
        if fade_in_n > 1:
            bed[:fade_in_n] *= np.linspace(0.0, 1.0, fade_in_n, dtype=np.float32)
        if fade_out_n > 1:
            bed[-fade_out_n:] *= np.linspace(1.0, 0.0, fade_out_n, dtype=np.float32)

        rms = float(np.sqrt(np.mean(bed * bed))) or 1.0
        bed = bed * (0.28 / rms)
        bed = np.tanh(bed).astype(np.float32)
        pk = float(np.max(np.abs(bed))) or 1.0
        self._bed += (bed / pk) * float(gain)

    def add_sfx(self, t_sec: float, kind: str, amp: float = 1.0, **kwargs) -> None:
        """Place a named procedural SFX at t_sec seconds."""
        k = kind.lower().strip()
        generators = {
            "slap": self.slap,
            "stamp_thud": self.stamp_thud,
            "scissor_snip": self.scissor_snip,
            "paper_rip": self.paper_rip,
            "whoosh": lambda: self.whoosh(**kwargs),
            "coin_clink": self.coin_clink,
            "type_tick": self.type_tick,
        }
        if k not in generators:
            raise ValueError(f"Unknown SFX kind: {kind!r}. Available: {sorted(generators)}")
        sig = generators[k]()
        idx = int(round(float(t_sec) * self.sr))
        if 0 <= idx < self.n_samples:
            end = min(self.n_samples, idx + len(sig))
            self._sfx[idx:end] += sig[: end - idx] * float(amp)

    def mix(self) -> np.ndarray:
        """Mix voice, editorial bed, and scaled SFX into normalized float32 [-0.90, 0.90] audio."""
        if self._has_voice:
            v_peak = float(np.max(np.abs(self._voice))) or 0.5
            sfx_scale = 0.24 * v_peak
        else:
            b_peak = float(np.max(np.abs(self._bed))) or 0.35
            sfx_scale = max(0.18, 0.85 * b_peak)
        mixed = self._voice + self._bed + self._sfx * sfx_scale
        # Soft-knee transient limiter prevents brief SFX spikes from starving integrated loudness
        pk = float(np.max(np.abs(mixed)))
        if pk > 0.01:
            rms = float(np.sqrt(np.mean(mixed * mixed))) or 1e-6
            if pk / rms > 5.0:
                drive = 1.65 / pk
                mixed = np.tanh(mixed * drive) / math.tanh(1.65)
                pk = float(np.max(np.abs(mixed)))
        if pk > 0.90:
            mixed = mixed * (0.90 / pk)
        return np.clip(mixed, -1.0, 1.0).astype(np.float32)

    def export_wav(self, out_path: Union[str, Path]) -> Path:
        """Write 16-bit mono PCM WAV to out_path."""
        op = Path(out_path)
        op.parent.mkdir(parents=True, exist_ok=True)
        pcm = (self.mix() * 32767.0).astype(np.int16)
        with wave.open(str(op), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sr)
            wf.writeframes(pcm.tobytes())
        return op


def apply_loudnorm(
    in_mp4: Union[str, Path],
    out_mp4: Union[str, Path],
    target_i: float = -14.0,
    target_tp: float = -1.5,
    target_lra: float = 11.0,
) -> Path:
    """Apply broadcast 2-pass ffmpeg EBU R128 loudnorm (-14 LUFS, -1.5 dBTP) while copying video."""
    src = _safe_media_path(in_mp4)
    dst = _safe_media_path(out_mp4)
    if not src.is_file():
        raise FileNotFoundError(f"Input media not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    ti = float(target_i)
    ttp = float(target_tp)
    tlra = float(target_lra)
    if not all(math.isfinite(v) for v in (ti, ttp, tlra)):
        raise ValueError("Loudnorm targets must be finite numbers")

    p1 = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(src),
            "-af",
            f"loudnorm=I={ti}:TP={ttp}:LRA={tlra}:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    matches = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr, re.S)
    if not matches:
        raise RuntimeError(f"Failed to parse loudnorm pass-1 stats from ffmpeg:\n{p1.stderr[-600:]}")
    stats = json.loads(matches[-1])

    # Guard against silent tracks where measured_I is -inf, and validate all numeric fields before filter interpolation
    if str(stats.get("input_i", "")).lower() in ("-inf", "inf", "nan"):
        af = f"loudnorm=I={ti}:TP={ttp}:LRA={tlra}"
    else:
        in_i = float(stats["input_i"])
        in_tp = float(stats["input_tp"])
        in_lra = float(stats["input_lra"])
        in_thresh = float(stats["input_thresh"])
        in_offset = float(stats["target_offset"])
        if not all(math.isfinite(v) for v in (in_i, in_tp, in_lra, in_thresh, in_offset)):
            af = f"loudnorm=I={ti}:TP={ttp}:LRA={tlra}"
        else:
            needed_gain = ti - in_i
            peak_headroom = ttp - in_tp
            use_linear = peak_headroom >= (needed_gain - 1.0)
            mode_str = "true" if use_linear else "false"
            af = (
                f"loudnorm=I={ti}:TP={ttp}:LRA={tlra}:"
                f"measured_I={in_i:.3f}:measured_TP={in_tp:.3f}:"
                f"measured_LRA={in_lra:.3f}:measured_thresh={in_thresh:.3f}:"
                f"offset={in_offset:.3f}:linear={mode_str}"
            )

    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(src),
            "-c:v",
            "copy",
            "-af",
            af,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(dst),
        ],
        check=True,
    )
    return dst
