---
paths:
  - "**/{remotion,manim,motion-canvas,animation,animations,video,videos,scenes}/**"
  - "**/{render,timeline,scene,scenes,storyboard,composition}.{ts,tsx,js,jsx,mjs,py}"
  - "**/*.{scene,anim}.{ts,tsx,js,py}"
  - "**/{lesson,video,render,remotion,manim}.config.{json,ts,js,mjs,toml,yaml,yml}"
---
# Video gate
Invoke `ui-ux-pro-max` FIRST for type scale, colour contrast and motion timing; Remotion project → `remotion-best-practices` FIRST instead.

1. **Reading time**: the storyboard lists, per scene, the words on screen and the seconds the scene is fully visible after fade-in and fade-out. Words × 0.3 s fits inside that time, counting on-screen text and subtitle together while both are visible; otherwise lengthen the scene or split the text. Count words with a script over the exact strings that render.
2. **No blank frames**: scan every frame of the render (`ffmpeg -vf signalstats`, flag frames where YMIN == YMAX). Scene boundaries count: fade-in starts above opacity 0, or scenes overlap.
3. **Transitions viewed**: besides hold frames, pull the first frame of every scene and one frame from the middle of every fade-in and fade-out, and view them beside the contact sheet. In the mid-crossfade frame, text of the two scenes must not overlap: the old scene is below 20 % opacity before the new one passes 50 %, or the two sit in different places.
4. **Repeatable render**: render twice from the same commit and compare every frame (`ffmpeg -i out.mp4 -f framemd5 -`). Any difference → remove the nondeterminism (Remotion: `concurrency: 1`) before acceptance.
5. **Motion review**: before the review step closes, invoke `review-animations` with `args` naming the timeline and easing files. Fix what it flags or list it as P2.
6. **Safe area**: every glyph, diacritics included, and every caption box stays inside a 5 % margin; check the bounding box of non-background pixels on rendered frames.
