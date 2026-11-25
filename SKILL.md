---
name: sphyrex-vox-skill
description: Produce Vox-style editorial paper-collage & engraved map documentaries (9:16 Shorts/Reels or 16:9 YouTube) from a script or topic using a deterministic Python rendering kit (Natural Earth maps, torn paper, outside-corner masking tape, worn red stamps, word-synced subtitles, procedural organic SFX, -14 LUFS loudnorm) plus optional 24fps zero-text AI hero clips. Compatible with Claude Code, OpenAI Codex CLI, and Google Antigravity.
license: MIT
metadata:
  author: Sphyrex
  homepage: https://xsphyrex.com/en/guides/vox-documentary-skill
  version: "0.1.0"
---

# Sphyrex Vox Skill (Hybrid Vox × Engraving v6)

*Works natively as a skill in **Claude Code** (`~/.claude/skills/`), **OpenAI Codex CLI** (`~/.codex/skills/`), and **Google Antigravity** (`~/.agents/skills/`).*

You are producing a **Vox-style editorial collage documentary** using the `vox_kit` Python engine.
Your job is to keep **70–80% of the video deterministic in code** (maps, typography, numbers, torn receipts, red stamps, charts, subtitles, SFX) so text and geography are **100% accurate**, and optionally slot **20–30% zero-text AI hero clips** (24 FPS) for physical tactile moments.

## Hard Rules (Never Violate)

1. **Zero Hallucinated Text or Numbers:** Every statistic, price, date, and country border must come from verified sources and Natural Earth GeoJSON (`1:50m`). Never ask an image/video AI model to render text, letters, or numbers.
2. **FPS Lock:**
   - If the timeline includes AI video clips (e.g., Google Flow / Veo at 24 FPS), lock the entire render to **24 FPS** (mixing 24 FPS clips into 30 FPS causes stutter).
   - Pure-code renders may use **24 FPS** (editorial film feel, default) or **30 FPS**.
3. **0-Second Visual Hook:**
   - Frame `0` must already show the core tension or shocking contrast (never a blank fade-in, never a static logo/avatar).
   - Trigger the first physical motion (stamp slam, ribbon cut, paper rip, counter jump) within the first **0.3 seconds**.
4. **Torn Paper + Clean Outside-Corner Tape:**
   - Never use plain sharp rectangles for editorial cards. Use `make_torn_strip`, `make_torn_receipt`, `make_step_card`, or `torn_rect_polygon`.
   - Masking tape (`make_masking_tape`) goes **only on outer corners** and must **never overlap letters**.
5. **High-Contrast Red Stamp Rule:**
   - Never stamp bare red ink directly on busy map coastlines. Always set `with_slip=True` (`make_red_stamp_on_slip`) so the stamp lands on a torn cream paper slip.
   - Restrict vermilion red (`#D02E2A`) to 4 semantic roles: rubber stamps, map ribbons/pins, hand-drawn underlines/circles, and danger/`0` callouts.
6. **Whole Map + Horizontal Torn Black Curtain:**
   - Break visual monotony with 1–2 high-contrast dark beats using `make_horizontal_torn_curtain` (`#141417`) rising **horizontally from the bottom** while shifting the map upward so the featured country remains **100% uncut**.
7. **1–3 Words per Visual Element + No Empty Transition Frames + Rock-Steady Subtitles:**
   - Let voiceover carry full sentences; put **1–3 words + a physical icon/number** on screen.
   - **Never leave sparse/empty transition frames or drop into overly simplified split screens with flat vector icons** (e.g., a lone text strip on a black void, or cutting away from a map to two cartoon icons on black): keep the engraved map running continuously underneath while real evidence, screenshots, data charts, or locked preview cards animate on top.
   - Multi-step lists ("3 steps") must remain readable on screen for **at least 2.5–3 seconds**.
   - Subtitles sit in a fixed dark paper bar (`#1A191D`, `#EBBA2C` border), guaranteed single line (`<=17 chars`), active word highlighted in mustard yellow, **0 px vertical jitter**.
8. **Word-Meaning Millisecond Sync + Audio Quality Gate:**
   - Bind every visual entrance, ribbon draw, stamp slam, and SFX (`slap`, `stamp_thud`, `paper_rip`, `scissor_snip`, `whoosh`, `coin_clink`) to the exact word timestamp (or beat timestamp in music-only demos).
   - Always finish with 2-pass `loudnorm` (`I=-14, TP=-1.5`) and run `python3 -m vox_kit check <video.mp4>` + `python3 -m vox_kit contact-sheet <video.mp4> --out <dir>`. Inspect every contact sheet before delivering.

## Fixed Color Palette (`vox_kit.palette`)

| Role | Name | Hex | RGB |
|---|---|---|---|
| Map / board background | Warm Parchment | `#EFEAE0` | `(239, 234, 224)` |
| Torn card / slip | Cream Paper | `#F4EFE5` | `(244, 239, 229)` |
| Primary ink / subtitle bar | Deep Ink | `#1A191D` | `(26, 25, 29)` |
| Contrast curtain | Torn Black Paper | `#141417` | `(20, 20, 23)` |
| Warm highlight | Mustard Yellow | `#EBBA2C` | `(235, 186, 44)` |
| Stamp / ribbon / danger | Stamp Red | `#D02E2A` | `(208, 46, 42)` |
| Approval / checkmark | Patina Green | `#2F8F6B` | `(47, 143, 107)` |
| Masking tape / brass pin | Tape & Brass | `#E8DDC0` / `#D4A848` | `(232, 221, 192)` / `(212, 168, 72)` |

No neon green, no purple-blue gradients, no glassmorphism, no flash frames.

## Step-by-Step Production Pipeline

1. **Research & Fact-Check:** Verify all numbers, units, and countries. Write a concise fact table first.
2. **Beat Sheet (Average 2.5–4.5 s per beat):** Follow `references/BEAT-SHEET-SCHEMA.md`. Pair every spoken/visual beat with one primary visual metaphor and exact SFX cue.
3. **Prepare Map Cache (if geography is used):**
   ```bash
   python3 -m vox_kit map-prep --countries BRA,COL,TUR --out ./cache/map
   ```
   Generates engraved Natural Earth `1:50m` mipmaps (`mip0..mip2.png`) + per-country highlight masks (`mask_BRA.png`, etc.).
4. **Optional AI Hero Clips (2–4 clips, 2–3 s each, 24 FPS):**
   Use the zero-text prompts in `references/FLOW-PROMPTS.md`. Extract frames (`ffmpeg -i clip.mp4 -vf fps=24 frames/f_%04d.jpg`) and time-remap them in your scene function so motion matches spoken words.
5. **Write & Render Scene Script:**
   Copy `examples/kahve_180tl/scene.py` as a template. Choose `aspect="9:16"` (`1080×1920`) or `aspect="16:9"` (`1920×1080`). Render with:
   ```bash
   python3 -m vox_kit render examples/kahve_180tl/scene.py --out ./out/demo.mp4
   ```
6. **Automated QA + Visual Inspection:**
   ```bash
   python3 -m vox_kit check ./out/demo.mp4
   python3 -m vox_kit contact-sheet ./out/demo.mp4 --out ./out/sheets
   ```
   Fix any broken frame, overlapping text, illegible list, or LUFS warning (`-16..-12 LUFS`), re-render, and re-check.

## Files in This Skill

- `SKILL.md` — Core rules and workflow (this file).
- `vox_kit/` — Reusable Python rendering engine (maps, paper collage, cutouts, charts, SFX, subtitles, multiprocessing encoder, QA CLI).
- `references/FLOW-PROMPTS.md` — Zero-text halftone collage & 24 FPS I2V prompt templates.
- `references/BEAT-SHEET-SCHEMA.md` — Beat timing and word-sync blueprint.
- `examples/kahve_180tl/` — Full working 48-second mini-documentary ("180 TL'lik Kahveden Çiftçiye Ne Kalıyor?").
