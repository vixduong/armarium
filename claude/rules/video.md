---
paths:
  - "**/{remotion,manim,motion-canvas,animation,animations,video,videos,scenes}/**"
  - "**/{render,timeline,scene,scenes,storyboard,composition}.{ts,tsx,js,jsx,mjs,py}"
  - "**/*.{scene,anim}.{ts,tsx,js,py}"
  - "**/{lesson,video,render,remotion,manim}.config.{json,ts,js,mjs,toml,yaml,yml}"
---
# Video gate
Invoke the toolchain skill FIRST: Remotion project or batch renders from data → `remotion-best-practices` + `lean-build` + `tdd` · film in a named Lemo-Opuscar style → `lemo-opuscar:lemo-opuscar` · other video by code → `hyperframes:hyperframes`. Design skills are optional (`ui-ux-pro-max` for an open look-and-feel question).
The user gives a reference video or link → suggest `/video-ref <link>` (frames per scene, contact sheet, subtitles).

## Toolchain skills
- **Load per project.** A toolchain skill missing from the skill list → in the video repo run `claude plugin enable hyperframes@hyperframes --scope project` (or `lemo-opuscar@lemolab`); for Remotion add `"skillOverrides": {"remotion-best-practices": "on"}` to `.claude/settings.json`. The user then runs `/reload-plugins`.
- **HyperFrames and Lemo-Opuscar own the build loop**: it replaces Code flow steps 4 (plan mode) and 6 (TDD). The gate below stays the acceptance check; reuse what their loop already made as its evidence. Remotion keeps the whole Code flow.
- **HyperFrames**: `npx hyperframes check --json` audits layout and contrast, and its `sweep_static` flags 3 s+ with no change (blank frames still need item 2). `snapshot --at`/`--range` and `measure frames --range` give item 3's frames; `measure cuts` finds the cuts a scene score misses. Its rules keep key text in the 80 % title-safe box, inside item 6's margin. Renders seek a paused timeline, so item 4 should pass first time.
- **Lemo-Opuscar**: `~/lemo-opuscar/DIRECTOR.md` §11 checks black and NaN frames, −14 LUFS loudness and subtitle sync; its review loop (`~/lemo-opuscar/TECHNIQUE.md` §8) makes contact sheets and 0.2 s strips for item 3. Gate findings join its one fix round.
- Neither counts reading time: item 1 is yours.

1. **Reading time**: the storyboard lists, per scene, the words on screen and the seconds the scene is fully visible after fade-in and fade-out. Words × 0.3 s fits inside that time, counting on-screen text and subtitle together while both are visible; otherwise lengthen the scene or split the text. Count words with a script over the exact strings that render.
2. **No blank frames**: scan every frame of the render (`ffmpeg -vf signalstats`, flag frames where YMIN == YMAX). Scene boundaries count: fade-in starts above opacity 0, or scenes overlap.
3. **Transitions viewed**: besides hold frames, pull the first frame of every scene and one frame from the middle of every fade-in and fade-out, and view them beside the contact sheet. In the mid-crossfade frame, text of the two scenes must not overlap: the old scene is below 20 % opacity before the new one passes 50 %, or the two sit in different places.
4. **Repeatable render**: render twice from the same commit and compare every frame (`ffmpeg -i out.mp4 -f framemd5 -`). Any difference → remove the nondeterminism (Remotion: `concurrency: 1`) before acceptance.
5. **Motion review**: before the review step closes, invoke `review-animations` with `args` naming the timeline and easing files. Fix what it flags or list it as P2.
6. **Safe area**: every glyph, diacritics included, and every caption box stays inside a 5 % margin; check the bounding box of non-background pixels on rendered frames.
