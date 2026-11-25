# Beat Sheet & Word-Meaning Sync Blueprint

Every `vox_kit` video is structured as a sequence of **beats** (typically **2.5 to 5.0 seconds** each) with explicit **visual metaphors** and **SFX anchors**.

## Beat Structure

| Field | Rule |
|---|---|
| `start_s` / `end_s` | Exact seconds (derived from Whisper word JSON when voiceover exists, or deliberate rhythm for music-only demos). |
| `backdrop` | One of `cream_board`, `map_camera`, `black_curtain`, or `flow_clip`. Never stay on one flat backdrop for >18 seconds without a contrast shift. |
| `focal_element` | Exactly **1 primary visual focus** per beat (a map route, a receipt stack, a comparison bar, or a dramatic stamp). |
| `text_budget` | Max **1–3 words** per card/stamp (`180 TL`, `SADECE 6 TL`, `10.500 KM`). Never paste paragraph sentences onto the canvas. |
| `sfx_cues` | Every visual entrance gets a matching sound: `slap` (card), `stamp_thud` (red rubber stamp), `paper_rip` (black curtain or torn reveal), `scissor_snip` (cut/elimination), `whoosh` (camera pan), `coin_clink` (money/price hit). |

## Word-Meaning Sync Pattern

When voiceover audio is available:
1. Run Whisper word-level JSON:
   ```bash
   whisper-cli -m ~/.cache/whisper-cpp/ggml-large-v3-turbo.bin -f voice_16k.wav -l tr -oj -ml 1 -of words
   ```
2. Measure true speech start via RMS energy (never trust Whisper `0.00s` blindly) and trim leading silence.
3. Convert key spoken anchor words to frame indices (`anchor_f = round(word_start_s * fps)`):
   - Country named → start `paint_region` highlight at `anchor_f`.
   - Price/number spoken → ramp counter + fill yellow receipt badge at `anchor_f`.
   - Problem/twist spoken → trigger `make_horizontal_torn_curtain` + `paper_rip` at `anchor_f`, then `make_red_stamp_on_slip` + `stamp_thud` 3 frames later.
4. Keep subtitle groups at `<=17 characters` per single line so the bottom dark paper strip stays 100% locked with zero vertical jitter.
