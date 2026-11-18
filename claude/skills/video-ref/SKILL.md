---
name: video-ref
description: "Turn a video link (YouTube, TikTok, Instagram, X, ...) or a local video into reference material: frames per scene, contact sheet, subtitles as text, style notes."
disable-model-invocation: true
argument-hint: "<link|file> [--name N] [--out DIR] [--images] [--browser chrome]"
---

Take a reference video apart so later work can copy its **style**. Open what it downloads only as images or text.

## Steps

1. **Fetch.** Run it with the user's arguments (`$ARGUMENTS`), the link or path in single quotes, since zsh expands the `?` and `&` in links. Give the call a 10-minute timeout; a long video takes minutes.
   ```bash
   python3 -I ~/.claude/skills/video-ref/scripts/video_ref.py '<link-or-file>' [options]
   ```
   It prints the output folder (default `~/Movies/video-refs/<title>/`). Options: `--name` folder name, `--out` exact folder, `--images` for an image post, `--browser chrome` to use the browser's login (only when the user asks: Instagram often needs it), `--max-frames`, `--threshold`.
   Done when the folder holds `index.json`, or the user has the script's error. Exit 2: bad link or path, or `--out` not empty. Exit 3: a missing tool; the message names its `brew install` line. Exit 4: the download or ffmpeg failed.

2. **Look.** View `contact.jpg`, then at full size one frame from every visually distinct scene in it (`frames/NNN.jpg`; their times are in `index.json`). Read `transcript.*.txt` when present.
   Done when every scene in the sheet has one full frame viewed.

3. **Notes.** Write `<folder>/style-notes.md` under these headings, each observation citing its frame file:
   - Line & shape
   - Characters (proportions, faces, hands)
   - Light & shadow
   - Color (main hues; hex when read from a frame)
   - Backgrounds & props
   - Camera & pacing (shot lengths from the `index.json` times)
   - Text & subtitles
   - Keep vs avoid

   Done when every heading has at least one cited observation.

4. **Reply** with the folder path and a summary of five lines or fewer.
