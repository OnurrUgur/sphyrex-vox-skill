"""Comprehensive unit and end-to-end tests for vox_kit."""
from __future__ import annotations

import json
import math
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import vox_kit
from vox_kit import (
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
    MapCamera,
    MapProjection,
    SoundMixer,
    TimedCaption,
    VideoConfig,
    add_paper_shadow,
    apply_paper_overlay,
    apply_vox_colored_cutout,
    build_cream_board,
    build_map_cache,
    build_paper_overlay,
    captions_to_groups,
    check_video,
    clamp01,
    composite_smooth,
    draw_brass_pin,
    draw_check,
    draw_red_ribbon,
    draw_star,
    draw_subtitle_bar,
    ease_in_cubic,
    ease_out_back,
    ease_out_cubic,
    get_assets_dir,
    get_font,
    group_whisper_words,
    make_bar_chart_card,
    make_contact_sheet,
    make_horizontal_torn_curtain,
    make_masking_tape,
    make_procedural_halftone_icon,
    make_red_stamp_on_slip,
    make_search_slip,
    make_step_card,
    make_torn_receipt,
    make_torn_strip,
    paint_region,
    render_scene,
    smoothstep,
    torn_rect_polygon,
)
from vox_kit.cli import main as cli_main

PKG_ROOT = Path(__file__).resolve().parent.parent


class TestPaletteAndEasing(unittest.TestCase):
    def test_palette_constants_and_fonts(self):
        for col in (C_BOARD, C_BEIGE, C_INK, C_BLACK_PAPER, C_YELLOW, C_RED, C_RED_DARK, C_TAPE, C_BRASS, C_MUTED, C_GREEN):
            self.assertEqual(len(col), 3)
            self.assertTrue(all(0 <= c <= 255 for c in col))

        self.assertTrue((get_assets_dir() / "fonts" / "Anton-Regular.ttf").is_file())
        for key in ("anton", "sora", "sora_medium", "cinzel", "caslon", "serif_bold", "serif_italic", "typewriter", "unknown_fallback_key"):
            font = get_font(key, 32)
            bb = font.getbbox("Test 123")
            self.assertGreater(bb[2] - bb[0], 0)

    def test_easing_functions(self):
        self.assertEqual(clamp01(-0.5), 0.0)
        self.assertEqual(clamp01(0.4), 0.4)
        self.assertEqual(clamp01(2.5), 1.0)
        self.assertAlmostEqual(smoothstep(0.0), 0.0)
        self.assertAlmostEqual(smoothstep(0.5), 0.5)
        self.assertAlmostEqual(smoothstep(1.0), 1.0)
        self.assertAlmostEqual(ease_out_cubic(0.0), 0.0)
        self.assertAlmostEqual(ease_out_cubic(1.0), 1.0)
        self.assertGreater(ease_out_cubic(0.5), 0.5)
        self.assertAlmostEqual(ease_in_cubic(0.0), 0.0)
        self.assertAlmostEqual(ease_in_cubic(1.0), 1.0)
        self.assertLess(ease_in_cubic(0.5), 0.5)
        self.assertAlmostEqual(ease_out_back(0.0), 0.0)
        self.assertAlmostEqual(ease_out_back(1.0), 1.0)
        self.assertGreater(ease_out_back(0.75), 1.0)


class TestPaper(unittest.TestCase):
    def test_paper_primitives(self):
        tex, dusts = build_paper_overlay(320, 180, seed=7)
        self.assertEqual(tex.shape, (180, 320))
        self.assertEqual(len(dusts), 3)
        self.assertTrue(float(tex.min()) >= 0.5 and float(tex.max()) <= 1.0)

        board = build_cream_board(320, 180)
        self.assertEqual(board.size, (320, 180))
        self.assertEqual(board.mode, "RGB")

        poly = torn_rect_polygon(10, 10, 110, 60, amp=4.0, step=10.0, seed=3)
        self.assertGreaterEqual(len(poly), 16)

        tape = make_masking_tape(length=80, width=24, angle=-30.0, seed=9)
        self.assertEqual(tape.mode, "RGBA")
        self.assertGreater(tape.width, 60)

        body = Image.new("RGBA", (60, 40), (*C_BEIGE, 255))
        shadowed = add_paper_shadow(body, pad=12)
        self.assertEqual(shadowed.size, (84, 64))

        curtain_9_16 = make_horizontal_torn_curtain(540, 960, split_y=520)
        self.assertEqual(curtain_9_16.size, (540, 960))
        self.assertEqual(curtain_9_16.getpixel((270, 100))[3], 0)
        self.assertEqual(curtain_9_16.getpixel((270, 900))[3], 255)

        curtain_16_9 = make_horizontal_torn_curtain(960, 540, split_y=300)
        self.assertEqual(curtain_16_9.size, (960, 540))

        out_arr = apply_paper_overlay(board, tex, dusts, frame_idx=5)
        self.assertEqual(out_arr.shape, (180, 320, 3))
        self.assertEqual(out_arr.dtype, np.uint8)


class TestElementsAndIcons(unittest.TestCase):
    def test_editorial_elements(self):
        canvas = Image.new("RGBA", (960, 540), (*C_BOARD, 255))
        d = ImageDraw.Draw(canvas)
        draw_star(d, 100, 100, 30, 14, (*C_YELLOW, 255), (*C_INK, 255))
        draw_check(d, 180, 100, radius=20)
        draw_brass_pin(d, 260, 100, scale=1.0)
        draw_red_ribbon(d, [(100, 200), (250, 160), (400, 220)], reveal=0.8, width=8)

        for icon in ("", "apple", "play", "puzzle", "doc", "check", "coffee", "pin", "warning"):
            strip = make_torn_strip("180 TL KAHVE", red_underline=0.8, icon=icon, seed=12)
            self.assertEqual(strip.mode, "RGBA")
            self.assertGreater(strip.width, 120)

        stamp_slip = make_red_stamp_on_slip("SADECE 6 TL", with_slip=True)
        stamp_bare = make_red_stamp_on_slip("SADECE 6 TL", with_slip=False)
        self.assertGreater(stamp_slip.width, stamp_bare.width)

        receipt = make_torn_receipt("#01", "Brezilya Cekirdek", "6 TL", lit_p=0.75, width=760, height=110)
        self.assertEqual(receipt.mode, "RGBA")

        step = make_step_card("01", "HASAT", "Ciftci payi %3", highlight=True, width=760, height=140)
        self.assertEqual(step.mode, "RGBA")

        slip = make_search_slip("kahve maliyeti", f=20, start_f=5, width=720, height=110)
        self.assertEqual(slip.mode, "RGBA")

        chart = make_bar_chart_card(
            "180 TL KAHVE DAGILIMI",
            [
                ("Ciftci", "6 TL", 0.04, C_RED),
                ("Lojistik", "18 TL", 0.14, C_INK),
                ("Kafe & Kira", "156 TL", 0.86, C_YELLOW),
            ],
            progress=0.85,
            width=820,
            height=520,
        )
        self.assertEqual(chart.mode, "RGBA")

        # Composite including negative/edge coordinates (must not crash!)
        composite_smooth(canvas, strip, cx=10, cy=10, f=5, start_f=0, end_f=30, fps=24, rot=-2.0, float_amp=3.0)
        composite_smooth(canvas, stamp_slip, cx=480, cy=270, f=10, start_f=8, end_f=30, fps=24, stamp_pop=True)

    def test_all_procedural_halftone_icons(self):
        kinds = [
            "coffee_cup",
            "coffee_bean",
            "cargo_ship",
            "paper_cup",
            "coin_stack",
            "receipt_roll",
            "magnifying_glass",
            "scissors",
            "code_terminal",
        ]
        for idx, kind in enumerate(kinds):
            im = make_procedural_halftone_icon(kind, size=180, accent=C_YELLOW if idx % 2 == 0 else C_RED, seed=idx + 5)
            self.assertEqual(im.mode, "RGBA")
            self.assertGreater(im.width, 100)
            self.assertGreater(im.height, 100)
            alpha = np.array(im.split()[3])
            self.assertGreater(int((alpha > 200).sum()), 2000, f"Icon {kind} appears empty")

        with self.assertRaises(ValueError):
            make_procedural_halftone_icon("nonexistent_kind")


class TestMapEngine(unittest.TestCase):
    def test_default_projection_covers_brazil_colombia_turkey_usa(self):
        proj = MapProjection()
        for lon, lat in [(-47.9, -15.8), (-74.1, 4.7), (35.0, 39.0), (-98.0, 39.5)]:
            mx, my = proj.ll_to_map(lon, lat)
            self.assertTrue(0 <= mx <= proj.map_w, f"lon {lon} out of range")
            self.assertTrue(0 <= my <= proj.map_h, f"lat {lat} out of range")
            rlon, rlat = proj.map_to_ll(mx, my)
            self.assertAlmostEqual(rlon, lon, places=4)
            self.assertAlmostEqual(rlat, lat, places=4)

    def test_mini_geojson_cache_and_camera(self):
        mini_geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ADM0_A3": "BRA", "ISO_A3": "BRA", "NAME": "Brazil"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-60, -25], [-40, -25], [-38, -5], [-55, -2], [-60, -25]]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"ADM0_A3": "TUR", "ISO_A3": "TUR", "NAME": "Turkey"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[26, 36], [45, 36], [45, 42], [26, 42], [26, 36]]],
                    },
                },
            ],
        }
        with tempfile.TemporaryDirectory(prefix="vox_map_test_") as td:
            gpath = Path(td) / "mini.geojson"
            gpath.write_text(json.dumps(mini_geo), encoding="utf-8")
            cache_dir = Path(td) / "cache"
            proj = MapProjection(map_w=720)
            meta = build_map_cache(gpath, cache_dir, countries=("BRA", "TUR"), projection=proj)

            self.assertEqual(meta["countries"], ["BRA", "TUR"])
            for fn in ("mip0.png", "mip1.png", "mip2.png", "meta.json", "mask_BRA.png", "mask_TUR.png"):
                self.assertTrue((cache_dir / fn).is_file(), f"Missing {fn}")

            cam = MapCamera(cache_dir)
            # 9:16 portrait view with highlight
            v_port = cam.render_view(-48.0, -14.0, zoom=1.2, w=270, h=480, highlights={"BRA": (1.0, C_YELLOW)})
            self.assertEqual(v_port.size, (270, 480))
            # 16:9 landscape view with highlight
            v_land = cam.render_view(35.0, 39.0, zoom=1.5, w=480, h=270, highlights={"TUR": (0.8, C_RED)})
            self.assertEqual(v_land.size, (480, 270))

            # Geodesic arc + screen projection
            arc = cam.geodesic_arc_points(-47.9, -15.8, 29.0, 41.0, n=32, lift=0.18)
            self.assertEqual(len(arc), 32)
            self.assertAlmostEqual(arc[0][0], -47.9, places=2)
            self.assertAlmostEqual(arc[-1][0], 29.0, places=2)

            cx, cy, x0, y0, x1, y1, ez = cam.compute_viewport(0.0, 15.0, 0.8, 480, 270)
            sx, sy = cam.project(35.0, 39.0, cx, cy, ez, 480, 270)
            self.assertTrue(math.isfinite(sx) and math.isfinite(sy))

            arr = np.array(v_land, dtype=np.uint8)
            paint_region(arr, cam.masks["TUR"], x0, y0, x1, y1, reveal_p=0.5, color=C_YELLOW)


class TestSFXAndSubtitles(unittest.TestCase):
    def test_sound_mixer_and_editorial_bed(self):
        mixer = SoundMixer(duration=2.0, sr=48000, seed=123)
        mixer.add_editorial_bed(bpm=108, gain=0.18)
        for idx, kind in enumerate(["slap", "stamp_thud", "scissor_snip", "paper_rip", "whoosh", "coin_clink", "type_tick"]):
            mixer.add_sfx(0.1 + idx * 0.22, kind, amp=0.9)

        with tempfile.TemporaryDirectory(prefix="vox_sfx_test_") as td:
            out_wav = Path(td) / "mix.wav"
            mixer.export_wav(out_wav)
            self.assertTrue(out_wav.is_file())
            with wave.open(str(out_wav), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getframerate(), 48000)
                self.assertEqual(wf.getnframes(), 96000)
                pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                self.assertGreater(int(np.max(np.abs(pcm))), 2000)

            # Also verify add_voice reads WAV cleanly
            mixer2 = SoundMixer(duration=1.0, sr=48000, seed=5)
            mixer2.add_voice(out_wav, gain=0.8)
            self.assertGreater(float(np.max(np.abs(mixer2.mix()))), 0.05)

    def test_subtitles_whisper_and_timed_captions(self):
        words = [
            (0.0, 0.3, "180"),
            (0.3, 0.6, "TL'lik"),
            (0.6, 1.0, "kahveden"),
            (1.0, 1.4, "ciftciye"),
            (1.4, 1.8, "ne"),
            (1.8, 2.2, "kaliyor?"),
        ]
        groups = group_whisper_words(words, max_chars=17, max_gap=0.45, duration=2.5)
        self.assertGreaterEqual(len(groups), 2)
        for _, _, kk in groups:
            line = " ".join(w[2] for w in kk)
            self.assertLessEqual(len(line.replace("?", "")), 20)

        cap_groups = captions_to_groups(
            [TimedCaption(0.0, 1.5, "Brezilya'dan Istanbul'a yolculuk.")],
            max_chars=17,
            duration=2.0,
        )
        self.assertGreaterEqual(len(cap_groups), 1)

        # Draw on both 9:16 and 16:9 frames
        for (w, h) in ((540, 960), (960, 540)):
            fr = build_cream_board(w, h).convert("RGBA")
            before = np.array(fr)
            draw_subtitle_bar(fr, 0.4, groups, w, h)
            after = np.array(fr)
            self.assertGreater(int(np.abs(after.astype(int) - before.astype(int)).sum()), 10000)


class TestEndToEndRenderAndCLI(unittest.TestCase):
    def test_end_to_end_render_check_contact_sheet_and_cli(self):
        cfg = VideoConfig(width=320, height=180, fps=24, duration=1.5, workers=1, crf=20, preset="ultrafast")
        state = {}

        def init_fn(args):
            state["board"] = build_cream_board(args["w"], args["h"])
            state["tex"], state["dusts"] = build_paper_overlay(args["w"], args["h"], seed=7)
            state["strip"] = make_torn_strip("VOX TEST", font_size=28, pad_x=24, pad_y=10, seed=1)
            state["subs"] = captions_to_groups([(0.1, 1.4, "Test editorial bar.")], duration=1.5)

        def frame_fn(f: int) -> bytes:
            w, h = cfg.width, cfg.height
            fr = state["board"].convert("RGBA")
            composite_smooth(fr, state["strip"], w * 0.5, h * 0.42, f, 0, cfg.total_frames + 4, fps=cfg.fps, rot=-1.0)
            draw_subtitle_bar(fr, f / cfg.fps, state["subs"], w, h)
            return apply_paper_overlay(fr, state["tex"], state["dusts"], f).tobytes()

        with tempfile.TemporaryDirectory(prefix="vox_e2e_") as td:
            tdp = Path(td)
            wav_path = tdp / "mix.wav"
            mixer = SoundMixer(duration=cfg.duration, seed=9)
            mixer.add_editorial_bed(bpm=112, gain=0.25)
            mixer.add_sfx(0.2, "slap", amp=0.9)
            mixer.add_sfx(0.8, "stamp_thud", amp=1.0)
            mixer.export_wav(wav_path)

            out_mp4 = tdp / "test_out.mp4"
            render_scene(
                cfg,
                init_fn,
                {"w": cfg.width, "h": cfg.height},
                frame_fn,
                wav_path,
                out_mp4,
                normalize=True,
            )
            self.assertTrue(out_mp4.is_file())
            self.assertGreater(out_mp4.stat().st_size, 5000)

            report = check_video(out_mp4)
            self.assertTrue(report["ok"], f"QA failed: {report}")
            self.assertEqual(report["fps"], 24.0)
            self.assertEqual(report["width"], 320)
            self.assertEqual(report["height"], 180)
            self.assertEqual(report["broken_frames"], [])
            self.assertTrue(report["lufs_ok"])
            self.assertTrue(-16.0 <= report["lufs"] <= -12.0)

            sheets = make_contact_sheet(out_mp4, tdp / "sheets", fps=2.0, grid="3x1", tile_width=160)
            self.assertGreaterEqual(len(sheets), 1)
            self.assertTrue(sheets[0].is_file())

            # Test CLI subcommands: check, contact-sheet, init
            self.assertEqual(cli_main(["check", str(out_mp4), "--json"]), 0)
            self.assertEqual(cli_main(["contact-sheet", str(out_mp4), "--out", str(tdp / "cli_sheets"), "--grid", "2x1"]), 0)
            init_dir = tdp / "starter_proj"
            self.assertEqual(cli_main(["init", str(init_dir)]), 0)
            self.assertTrue((init_dir / "scene.py").is_file())

    def test_no_personal_paths_or_shell_true(self):
        scan_exts = {".py", ".md", ".toml"}
        for path in PKG_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in scan_exts:
                continue
            if "__pycache__" in path.parts or "out" in path.parts or "cache" in path.parts:
                continue
            src = path.read_text(encoding="utf-8")
            rel = path.relative_to(PKG_ROOT)
            if path.name != "test_vox_kit.py":
                self.assertNotIn("/Users/", src, f"Personal macOS path found in {rel}")
                self.assertNotIn("shell=True", src, f"shell=True found in {rel}")
                self.assertNotIn("os.system(", src, f"os.system found in {rel}")
                self.assertNotIn("eval(", src, f"eval() found in {rel}")
                self.assertNotIn("exec(", src, f"exec() found in {rel}")

    def test_security_hardening_guards(self):
        # 1. MapCamera blocks path traversal in meta.json
        with tempfile.TemporaryDirectory(prefix="vox_sec_") as td:
            tdp = Path(td)
            (tdp / "meta.json").write_text(
                json.dumps(
                    {
                        "projection": {"lon_min": -10, "lon_max": 10, "lat_min": -10, "lat_max": 10, "map_w": 256},
                        "countries": ["BRA"],
                        "mips": ["../escape.png"],
                        "masks": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                MapCamera(tdp)

            # 2. CLI render rejects non-.py script and init rejects '..' traversal
            bad_script = tdp / "not_python.txt"
            bad_script.write_text("print('hi')", encoding="utf-8")
            self.assertNotEqual(cli_main(["render", str(bad_script), "--out", str(tdp / "o.mp4")]), 0)
            self.assertNotEqual(cli_main(["init", "../outside_dir"]), 0)

            # 3. make_contact_sheet rejects zero/malformed grid and non-positive/NaN fps
            with self.assertRaises(ValueError):
                make_contact_sheet(tdp / "x.mp4", tdp / "s", grid="0x2")
            with self.assertRaises(ValueError):
                make_contact_sheet(tdp / "x.mp4", tdp / "s", fps=0.0)
            with self.assertRaises(ValueError):
                make_contact_sheet(tdp / "x.mp4", tdp / "s", fps=float("nan"))

        # 4. VideoConfig rejects invalid x264 preset or odd dimensions
        with self.assertRaises(ValueError):
            VideoConfig(width=321, height=180)
        with self.assertRaises(ValueError):
            VideoConfig(width=320, height=180, preset="invalid_preset")

        # 5. MapProjection rejects inverted bbox or out-of-range width
        with self.assertRaises(ValueError):
            MapProjection(lon_min=50.0, lon_max=10.0)
        with self.assertRaises(ValueError):
            MapProjection(map_w=32)


if __name__ == "__main__":
    unittest.main()
