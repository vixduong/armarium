---
paths:
  - "**/{scene,world,shaders,webgl,three}/**"
  - "**/*.{glsl,vert,frag,wgsl}"
---
# Scene gate
A picture drawn by code: a 3D or WebGL scene, an illustration, a shader or generative background. The look is the deliverable: steps 1–5 are its acceptance check and come before the scene's systems (clock, weather, controls, interaction), which then take the Code flow. There is no toolchain skill.
The user gives a reference video, link or web page → suggest `/video-ref <link>` (frames, contact sheet, style notes; `--page` for a web page: what moves and what the scene is made of).

1. **Reference pack** — before the first line of code: the reference images or frames saved in the repo's design reference folder (none → `docs/reference/<name>/`), and one sentence naming the target look: painted, low-poly or photoreal, one of them. No reference → ask the user for one; they have none → render 2–3 looks of the largest element and build the one they pick. Questions barred or headless → pick one of those looks yourself and record the choice and its reason beside the pack's paths; its still is the reference for steps 4 and 5. Done when the plan names the pack's paths and that sentence.
2. **Medium** — before building, name the cheapest medium that reaches the target look: a pre-rendered video loop · painted layers with parallax and shader overlays · an authored vector animation (Rive, Lottie) · 3D with authored models and textures · 3D from code alone. The brief rules out the medium its look needs (no textures, yet "natural") → tell the user before the first line.
3. **Hero still** — one fixed view at one time of day: forms first, then materials, then light, then effects. Render it and view the screenshot before any system exists.
4. **Look loop** — view the hero still and the reference in one call. Judge every element the brief names (tree, figures, sky, ground, light) on silhouette, proportion, colour, edge and shadow; rebuild the worst one; render again. Least-code rules size the systems; the reference sizes the geometry, shader and palette detail. A technique you have not built before → search the web for it first.
5. **Look review** — before the systems start, and again before the review step closes: a `reviewer` call with a look-only prompt ← the pack's paths + the screenshot paths. It returns each difference from the reference as P1 (breaks the target look) or P2. Fix every P1; the closing call returned a P1 → one re-check of those P1s only, and a P1 it still finds stays ✗ in Exit; P2 → list in the final reply.
6. **Motion** — for every element that moves (wind, walk, water, weather) view a strip of 5 frames 0.2 s apart; motion that is linear, rigid or in step across elements is a finding. `review-animations` covers the page's controls; the scene's motion is judged here.
7. **Budget last** — measure frame time on the target device after the look review passes; cut detail from the reviewer's P2 items first.

Starting points for step 4: foliage cards https://douges.dev/blog/threejs-trees-1 · painterly pass https://blog.maximeheckel.com/posts/on-crafting-painterly-shaders/ · clouds https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/ · a photoreal look from code alone https://github.com/0xDarkMatter/claude-mods/blob/main/skills/threejs-ops/references/render-pipeline.md
