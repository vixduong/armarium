---
paths:
  - "**/*.{tsx,jsx,vue,svelte,css,scss,html}"
---
# Frontend gate
Invoke `ui-ux-pro-max` FIRST. Chart, dashboard, or stat tile → also `dataviz`. New site or page built from scratch → also `hallmark` (on an existing design only when the user names it).

1. **Reuse** — the project's design tokens and components come before a new colour, spacing value, or component.
2. **Explore** — new screen or an open "make it look good" → show 2–3 directions, build the chosen one. Least-code rules size the build, not the exploration.
3. **Tests** — logic (state, data transforms, validation, permissions) keeps full TDD. Pure presentation (CSS, layout, copy) is verified by eye: step 4.
4. **Look before done** — render it; screenshot at 375, 768, and desktop width, in light and dark if the app has both. Check empty, loading, error, and long-content states.
5. **Accessibility** — keyboard reach with visible focus, labels on inputs and icon buttons, text contrast ≥ 4.5:1, no meaning carried by colour alone.
6. **Motion** — the diff adds or changes animation (CSS transition or keyframes, a `requestAnimationFrame` loop, a canvas, WebGL or Three.js scene) → before the review step closes, invoke `review-animations` with `args` naming those files. Fix what it flags or list it as P2.
7. **Dashboard/report** — every number states unit, period, and source; each chart answers one question, named in its title.
