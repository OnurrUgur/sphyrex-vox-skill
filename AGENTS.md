# AGENTS.md — sphyrex-vox-skill

This repository is an open-source **Agent Skill + deterministic Python video engine (`vox_kit`)** compatible with **Claude Code**, **OpenAI Codex CLI**, and **Google Antigravity**.

## Instructions for Coding Agents

1. **Always read `SKILL.md` first** before writing or editing any video scene. It contains the 8 non-negotiable editorial design rules, fixed color palette, FPS lock, and QA pipeline.
2. **Never fabricate statistics, prices, or geography.** Verify every number before putting it in a scene script, and use the bundled Natural Earth `1:50m` GeoJSON (`assets/data/countries_50m.geojson`) via `vox_kit.map_engine`.
3. **Never ask an image/video AI model to render text or numbers.** Keep 70–80% of the timeline deterministic in `vox_kit` (maps, torn paper, outside-corner masking tape, worn red stamps on cream slips, charts, subtitles, organic SFX, `-14 LUFS`). If optional 24 FPS AI hero clips are used, follow `references/FLOW-PROMPTS.md` (strictly zero text).
4. **No empty transition frames or cartoon-icon split screens.** Keep the engraved map or concrete visual evidence active on every frame.
5. **Mandatory verification before finishing any render:**
   ```bash
   python3 -m vox_kit check <output.mp4>
   python3 -m vox_kit contact-sheet <output.mp4> --out <sheets_dir>
   python3 -m unittest discover -s tests -v
   ```
   Inspect every generated contact sheet image for overlapping text, clipped cards, missing glyphs, or sparse frames before delivering.
