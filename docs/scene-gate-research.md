# Scene gate: sources and skills checked

Research for `claude/common/rules/scene.md`, done 2026-11-27. Two questions: which pages teach a natural or painted look in a real-time Three.js scene, and whether a public agent skill already does what the gate asks. "Opened" means the page or file was fetched and searched for the terms named; the rest comes from a `researcher` agent's report and is marked so.

## Technique pages

| Page | Covers | Status |
|---|---|---|
| https://douges.dev/blog/threejs-trees-1 | Foliage as quads that face the camera, moved into place in the vertex shader by their UVs | opened: "foliage", "quad", "billboard", "normal", "alpha" all present |
| https://blog.maximeheckel.com/posts/on-crafting-painterly-shaders/ | A painterly post-process built on the Kuwahara filter, its anisotropic form and the structure tensor | opened: "Kuwahara" 224 times, "anisotropic" 89 |
| https://react-postprocessing.docs.pmnd.rs/effects/kuwahara | The same filter as a ready effect, with `radius` and `sectorCount` | opened |
| https://blog.maximeheckel.com/posts/real-time-cloudscapes-with-volumetric-raymarching/ | Clouds as raymarched volumes: noise for density, Beer's law for light | opened |
| https://github.com/Steve245270533/three-stylized | A meadow with instanced grass, runtime wind and wildflowers | README opened |
| https://threejs-journey.com/lessons/webgpu-tsl/stylized-nature-scene | Terrain, grass and water in WebGPU/TSL | researcher only; it reached the terrain part |
| Codrops: "How to make the fluffiest grass with Three.js" (2025-02-04) and "Susurrus: crafting a cozy watercolor world" (2026-04-24) | Grass shading; a watercolour scene | not read: both answered 403 to the agent and to `curl` |

The gate's last line links the trees page, the painterly shader page and the clouds page. Its fourth link, for a photoreal target, is `threejs-ops`' render pipeline, below.

## Skills

| Skill | What it tells the agent | Takes the owner's reference | Compares render with reference | Status |
|---|---|---|---|---|
| `threejs-aaa-graphics-builder`, in https://github.com/majidmanzarpour/threejs-game-skills (MIT) | Forms first, then materials, light, effects ("Glow does not make primitives look AAA"). Scores screenshots on a 10-category card before and after, and inspects motion in play | no: it sets its own art direction | no: against its own card | SKILL.md, README and LICENSE opened |
| `threejs-game-director`, same repo | Routes a game build across nine sibling skills; the image, 3D and audio ones call outside generators that need API keys | no | no | SKILL.md opened |
| `threejs-ops`, in https://github.com/0xDarkMatter/claude-mods (MIT) | Game-scale Three.js: glTF pipeline, instancing, and a photoreal look from code alone (HDR chain, PCSS shadows, volumetric fog, SSAO, tonemap and grade, baked procedural PBR) | no | no | SKILL.md, `references/render-pipeline.md` headings and LICENSE opened |
| https://github.com/wolffe/three.js-skills (MIT) | 29 WebGPU/TSL skills: materials, geometry, environments, lighting | no | no | README headings and LICENSE opened |
| `algorithmic-art`, in https://github.com/anthropics/skills | A written "philosophy", then a seeded p5.js piece | no | no | SKILL.md fetched (14 mentions of p5); read by the researcher |
| https://github.com/full-stack-skills/threejs-skills (Apache 2.0) | 18 skills of Three.js knowledge and workflows | no | no | README opened |
| https://github.com/ahujasid/blender-mcp (MIT) | A bridge that lets the agent run Python in a live Blender. Its `look` tool shows the agent the viewport, a camera view, a multi-view sheet or an animation strip | no | no: the agent views its own render | README opened |

## What this means for the gate

- No skill found starts from the owner's reference image or puts a render beside it. The gate keeps those two steps itself.
- `threejs-aaa-graphics-builder` is the closest. Its order (forms, materials, light, effects) is step 3 of the gate, and its scorecard is a second opinion the look review could use. It aims at a game's "premium" look, and its generator skills make images with an API key, which a project that bans generated art cannot use.
- `threejs-ops` is the one to read for a photoreal target built from code alone.
- Neither is installed. The gate names no skill it would need, so `bin/check` (Names) stays green without them.

## Not verified

- Last-commit dates of the skill repos.
- The two Codrops pages and the Three.js Journey lesson beyond its terrain part.
- Whether any of the skills improves a picture: none was run.
