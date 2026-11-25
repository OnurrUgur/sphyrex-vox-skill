# Zero-Text AI Hero Clip Prompt Templates (Optional 20–30% Layer)

`sphyrex-vox-skill` works **100% offline with $0 API cost** in pure-code mode.
When you want 2–4 cinematic physical collage inserts (2–3 seconds each) on top of the code engine, generate a **zero-text start frame** first, then animate **one single physical micro-motion** at **24 FPS**.

## 1. Start Frame Prompt (9:16 Vertical — Halftone Editorial Collage)

```text
Premium VOX-style hand-cut editorial paper collage, 9:16 vertical, warm vintage cream paper background (#EFEAE0) with subtle archival newsprint grain, centered black-and-white halftone newsprint cutout of [SUBJECT / OBJECT] with rough scissor-cut paper edge and thick mustard-yellow (#EBBA2C) outline, translucent beige masking tape on outer corners, soft drop shadow, single matte vermilion red (#D02E2A) ink accent, generous clean negative space top and bottom for overlays. Strictly zero text, no words, no letters, no numbers, no logos.
```

For **16:9 YouTube**, swap `9:16 vertical` → `16:9 widescreen` and keep clean negative space on the left or right third for code overlays.

## 2. Image-to-Video Prompt (Single Micro-Motion · 24 FPS)

```text
Fixed overhead flat-lay camera, crisp 24fps stop-motion editorial paper collage motion. [ONE SINGLE PHYSICAL ACTION, e.g., a cutout hand enters smoothly from the right holding a red grease pencil and draws one bold X across the blank monitor card, then exits cleanly]. Warm cream paper stays completely static, zero camera shake, strictly zero text, no letters or numbers appearing.
```

## 3. Extracting & Time-Remapping Frames in `vox_kit`

1. Export or download the 24 FPS clip (`clip.mp4`).
2. Extract frames:
   ```bash
   mkdir -p ./clips/clip1_frames
   ffmpeg -v error -i clip.mp4 -vf "fps=24,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" ./clips/clip1_frames/f_%04d.jpg
   ```
3. Build a 2-fps contact index (`ffmpeg -i clip.mp4 -vf "fps=4,scale=270:480,tile=8x4" idx.jpg`) to note the exact frame numbers where the action begins (`ACTION_START`) and finishes (`ACTION_END`).
4. In your `scene.py`, map timeline frames (`f`) smoothly so:
   - Before the key spoken word → stay on calm frames (`1..ACTION_START`).
   - During the key spoken phrase → advance `ACTION_START..ACTION_END`.
   - After impact → hold `ACTION_END` while `vox_kit` slams the red stamp and torn receipt on top.

## 4. Isolated Cutout Object Prompt (1:1 Pure White → Transparent PNG)

```text
Isolated single object centered on a pure flat solid white (#FFFFFF) background with wide empty white margin all around. Drawn in crisp black-and-white Renaissance copperplate engraving cross-hatching style with clean thick dark ink outer contour, subtle risograph ink grain, ready to be cut out as a Pop-Art motion graphic sprite. Strictly monochrome ink. No shadows on background, no background texture, no frame, no grid, no text or letters, no photorealism, no 3D glossy render.
```
