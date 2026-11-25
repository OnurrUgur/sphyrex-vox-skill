# sphyrex-vox-skill

**Open-source Agent Skill (Claude Code · OpenAI Codex · Google Antigravity) + deterministic Python engine (`vox_kit`) for producing Vox-style editorial paper-collage & engraved map documentaries (9:16 Shorts/Reels & 16:9 YouTube) with $0 API cost.**

[Türkçe README →](README.tr.md) · [Skill Rules (`SKILL.md`)](SKILL.md) · [Agent Instructions (`AGENTS.md`)](AGENTS.md)

> **Disclaimer:** This software is provided "as is", without warranty of any kind. You are solely responsible for verifying all facts, statistics, licensing of any third-party media you add, and compliance with platform policies. Sphyrex provides no hosted service and collects no telemetry or user data. The "Sphyrex" brand name and mascot artwork are not covered by the MIT license.

---

## Why Hybrid (75% Deterministic Code + 25% Optional AI)?

Pure AI video generators corrupt text, hallucinate country borders, and stutter when mixed into 30 FPS timelines. Manual After Effects editing takes days per minute.

`sphyrex-vox-skill` splits the job cleanly:
- **Deterministic Python Engine (`vox_kit` — 70–80%, $0 API cost):** Real Natural Earth `1:50m` engraved world maps with 3-level mipmap cameras, organic torn-paper cards, clean outside-corner masking tape (never overlapping letters), worn red rubber stamps on cream paper slips, horizontal torn black contrast curtains, animated breakdown charts, procedural halftone icons, Whisper word-synced zero-jitter subtitles (`<=17` chars single-line), procedural NumPy organic SFX, and 2-pass `-14 LUFS` EBU R128 loudness normalization.
- **Optional Zero-Text AI Hero Clips (20–30%, 24 FPS):** Drop 2–4 short (2–3 s) zero-text editorial collage clips (Google Flow / Veo / any I2V tool) into your scene using the templates in `references/FLOW-PROMPTS.md` and time-remap them to spoken words.

---

## Prerequisites

- **Python 3.9+** (`python3 --version`)
- **`ffmpeg` & `ffprobe`** installed and available in `PATH`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`
- Python packages (`Pillow`, `numpy`) — installed automatically by `pip install -e .`

---

## Step 1 · Install the Engine

```bash
git clone https://github.com/OnurrUgur/sphyrex-vox-skill.git
cd sphyrex-vox-skill
pip install -e .
```

Verify your setup in ~1 second (runs 12 unit, security & end-to-end render tests):

```bash
python3 -m unittest discover -s tests -v
```

---

## Step 2 · Connect the Skill to Your AI Agent

`sphyrex-vox-skill` follows the standard `SKILL.md` + `AGENTS.md` format and works natively in **Claude Code**, **OpenAI Codex CLI**, and **Google Antigravity**. Run the command for your tool inside the cloned `sphyrex-vox-skill` directory:

### Claude Code
```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/sphyrex-vox-skill
```

### OpenAI Codex CLI
```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)" ~/.codex/skills/sphyrex-vox-skill
```
*(Or per-project: `mkdir -p .agents/skills && ln -s /path/to/sphyrex-vox-skill .agents/skills/sphyrex-vox-skill` — Codex also reads `AGENTS.md` automatically when run inside the repo.)*

### Google Antigravity (`agy` / IDE)
```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)" ~/.agents/skills/sphyrex-vox-skill
```
*(Works globally across Antigravity CLI and IDE via `~/.agents/skills/`.)*

> **Windows (PowerShell):** Instead of `ln -s`, copy the folder directly into `%USERPROFILE%\.claude\skills\sphyrex-vox-skill`, `%USERPROFILE%\.codex\skills\sphyrex-vox-skill`, or `%USERPROFILE%\.agents\skills\sphyrex-vox-skill`.

---

## Step 3 · Run the Included 48-Second Demo or Prompt Your Agent

### Option A — Render the Ready-Made 48s Mini-Documentary (1 Command)
*"Out of a 180 TL cup of coffee, how much actually reaches the farmer?"* (9:16 vertical, 24 FPS, pure code, $0 API cost):

```bash
python3 -m vox_kit map-prep --countries BRA,COL,TUR --out examples/kahve_180tl/cache/map
python3 -m vox_kit render examples/kahve_180tl/scene.py --out examples/kahve_180tl/out/kahve-demo.mp4
python3 -m vox_kit check examples/kahve_180tl/out/kahve-demo.mp4
python3 -m vox_kit contact-sheet examples/kahve_180tl/out/kahve-demo.mp4 --out examples/kahve_180tl/out/sheets
```

For **16:9 YouTube widescreen**, add `--aspect 16:9` to the `render` command.

### Option B — Generate Your Own Topic With One Prompt
Open **Claude Code**, **Codex**, or **Antigravity** and paste:

> *"Use `sphyrex-vox-skill` to produce a 45-second 9:16 Vox-style mini-documentary about [your topic]. Verify every number from real sources first, prepare the Natural Earth map cache, render at 24 FPS, and run `vox_kit check` + `contact-sheet` before showing me the result."*

To scaffold a fresh project manually:
```bash
python3 -m vox_kit init ./my-documentary
```

---

## Architecture

```text
sphyrex-vox-skill/
├── SKILL.md                     # Agent Skill manifest: 8 hard editorial rules, palette & pipeline
├── AGENTS.md                    # Repo-level agent instructions (Codex / Antigravity / Claude)
├── vox_kit/
│   ├── palette.py               # Fixed Hybrid Vox x Engraving palette, bundled fonts, easings
│   ├── paper.py                 # Torn paper polygons, outer masking tape, black curtain, grain
│   ├── elements.py              # Stamps, receipts, step cards, bar charts, 9 procedural icons
│   ├── map_engine.py            # Natural Earth 1:50m engraved map + 3-level mipmaps + masks
│   ├── sfx.py                   # 7 procedural organic SFX + editorial bed + 2-pass -14 LUFS
│   ├── subtitles.py             # Whisper word JSON -> fixed dark strip (<=17 chars, 0 jitter)
│   ├── renderer.py              # Multiprocessing ffmpeg encoder, frame/LUFS QA & contact sheets
│   └── cli.py                   # `python3 -m vox_kit map-prep|render|check|contact-sheet|init`
├── references/
│   ├── FLOW-PROMPTS.md          # Optional zero-text 24fps AI hero clip prompts
│   └── BEAT-SHEET-SCHEMA.md     # Beat timing & word-meaning sync blueprint
├── assets/
│   ├── data/countries_50m.geojson  # Natural Earth 1:50m Public Domain world borders
│   └── fonts/                   # Anton, Sora, Cinzel (SIL OFL 1.1)
├── examples/kahve_180tl/        # Full 48s working mini-documentary demo (9:16 & 16:9)
└── tests/                       # 12 unit, security & end-to-end render tests
```

---

## Security & Privacy

- **Local execution:** Designed to run offline with zero telemetry and zero required API keys.
- **Trusted scenes only:** `python3 -m vox_kit render <scene.py>` executes the target Python scene file directly — only render `.py` scene scripts you wrote or trust.
- **Hardened paths & ffmpeg inputs:** Cache paths reject traversal (`..`) and absolute escapes; ffmpeg inputs are resolved to canonical absolute paths and loudnorm measurements are strictly validated as finite floats; all subprocess calls use explicit argument arrays without shell invocation.

## License

Code is MIT licensed (`LICENSE`). Natural Earth 1:50m data is Public Domain. Bundled fonts (Anton, Sora, Cinzel) are SIL OFL 1.1.
