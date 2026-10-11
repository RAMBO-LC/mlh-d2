# Summary

A poster-scale wordmark interlocked with a photographic product subject on a two-colour achromatic ground, with monospaced technical metadata pinned to every edge. Scroll drives the product's own mechanic rather than decorative motion, and the page is complete and readable before any of it runs.

# Style

Cool achromatic ground with near-black ink and exactly one saturated signal accent used for emphasis and never as a fill. Display type is a heavy grotesk at poster scale with tight negative tracking; everything that is not the headline is small monospaced metadata with wide positive tracking. Depth comes from real photography and hairlines, never from shadows, gradient glows or cards.

## Spec

Apply an achromatic technical-product style. Palette: ground #EFEFEE, a dimmer stage ground #E4E4E2, ink #0D0D0F, secondary ink #43444A, muted #6E6F76, one signal accent #2F5BFF plus #7C97FF as its lift on dark grounds, hairlines rgba(13,13,15,.12). Typography: display uses 'Archivo' 700-900 with letter-spacing -0.04em to -0.055em and line-height 0.74 to 0.98; metadata and labels use 'IBM Plex Mono' 400-500 at 10-12px with letter-spacing +0.14em to +0.16em, uppercase. Easing cubic-bezier(.16,1,.3,1) at 0.85-1.25s. Border-radius 0 everywhere except pill buttons. MUST commit to exactly two colours plus one accent, and the accent may only appear as small type, a dot, a rule or a single trace, never as a fill or a large area. MUST keep a constant layer of small monospaced metadata pinned to corners and edges: it is the counterweight that makes poster type read as design rather than as a banner. DO NOT use a hero banner, a gradient glow band, a dot or line grid backdrop, a bento grid, card rows, or drop shadows on anything except the cut-out subject.

# Layout & Structure

Seven full-width sections that alternate ground colour. The hero pins a poster word to the bottom edge and crops it left and right against the frame, with the product subject low and wide across the right half so it physically overlaps the word. Body sections are two-column with a hairline-ruled data list or a to-scale technical diagram. The page must genuinely scroll: a single 100vh hero with overflow hidden is an incomplete landing, not a design.

## Navigation

Fixed bar 64px tall, background the page ground at 82% with a 14px backdrop-blur and a 1px bottom hairline. Left: brand in display 800 at 16px, tracking -0.035em, followed by a period in the signal accent. Right: five mono links at 11px, tracking 0.14em, uppercase, each with a transparent 1px bottom border that becomes the accent on hover, then a pill button.

## Hero

Full viewport minus the nav, on the dimmer ground, with overflow:clip and isolation:isolate. Left column holds a mono eyebrow, a display headline at clamp(34px,5.1vw,74px) with its final phrase in the accent, a 38ch lede, two pill buttons, then a hairline-topped block of three mono spec lines. Keep every anchored element in the LEFT column: the subject is deliberately oversized and crosses the entire right half, so anything pinned top-right collides with it. Position the subject absolutely at bottom-right, width min(58vw,940px), bleeding about 4vw past the right edge, with drop-shadow(0 26px 34px rgba(13,13,15,.20)), and sit it low enough that its lower body genuinely overlaps the word.

## Inverted proof section

Full-bleed ink ground. Two columns: left holds a display headline, a lede, one enormous figure at clamp(56px,9vw,132px) with tabular numerals and a small mono unit baseline-aligned beside it, then a mono legend. Right holds an SVG of two line traces drawn to the same scale, a faint reference that wanders and an accent-coloured one that holds nearly flat, so the comparison IS the claim rather than an illustration of it. Generate both paths in JS from summed sine terms so the amplitudes stay honest to the numbers quoted.

## Technical diagram

Two columns: a display headline with a lede and a hairline-ruled definition list (mono label in the accent, plain description, mono value right-aligned, 1px top border per row). Beside it an SVG line drawing on the page ground, drawn strictly to scale in real units, with hairline construction geometry, accent-coloured points of interest, thin leader lines out to mono labels, and one path that draws itself in when the figure enters the viewport. Compute the geometry rather than eyeballing it, and give the drawing's own line a heavier stroke than the label leaders so it does not read as one more leader.

## Spec table

Two balanced columns of hairline-ruled rows, plain label left and mono tabular value right, around twelve rows. No borders except the 1px row rules.

## Close

Display headline with a mono fine-print line, buttons pushed to the opposite edge, a hairline-topped footer strip of four mono items with the last pushed right, then the brand word repeated full-width at clamp(84px,19.5vw,300px) and translated down 0.19em so the page's bottom edge crops it, bookending the hero.

# Special Components

## Type and subject occlusion weave

The signature move: a poster-scale wordmark that the product passes through, some letters behind it and one in front.

Set the brand word at clamp(88px,20.5vw,304px), weight 900, line-height 0.74, tracking -0.055em, as a flex row with justify-content:space-between spanning 105% of the width so the frame crops the first and last letters, translated down 0.10em so the bottom edge crops the baseline. CRITICAL: render the word TWICE as two absolutely positioned layers that overlay exactly, a back layer at z-index 1 and a front layer at z-index 3, with the subject at z-index 2 between them. Each layer contains every letter and sets visibility:hidden on the ones it does not own, which keeps the flex metrics identical so the two layers register perfectly. Put most letters in the back layer and exactly ONE overlapping letter in the front layer. DO NOT try this with per-letter z-index inside a single element: the word needs a transform for the baseline crop and again for the scroll parallax, a transform creates a stacking context on its own, z-index:auto does not save you, and the letters' z-index is then trapped at the word's level so every overlapping letter falls behind the subject and the effect silently does not exist.

## Hero subject artwork

How to produce the cut-out product photograph the occlusion depends on. A rectangular photo or a CSS shape collapses the whole style.

Generate the subject as a photoreal studio product shot against a FLAT SATURATED CHROMA-GREEN backdrop, not white. Ask for the product to stay strictly neutral in colour, lit by soft directional light from the upper left with a smooth tonal gradient across its surfaces and one crisp specular line along its longest edge, placed in the right half of the frame with generous empty space to its left, and state that nothing else appears anywhere in the frame. Describe lighting as a RESULT ('soft directional light falls from the upper left'), never as equipment ('lit by a softbox'), because naming the gear makes the model draw the gear into the picture. Then key it: alpha = 1 - smoothstep(0.10, 0.30, (G - max(R,B)) / G). Normalise greenness by brightness rather than using a raw channel difference, or shadowed backdrop lands mid-matte and survives as a ragged grey band hugging the object. Despill by clamping G down to max(R,B) wherever it leads. Keep only the largest connected blob, since generators often leave a detached ghost of a part floating in the empty half of the frame. Trim to the alpha bounding box before use, or CSS positions the empty frame instead of the object and the type and subject silently never overlap. A white sweep is NOT a substitute: a bright part of the product can be genuinely as bright as the backdrop it touches, and no threshold separates two regions that share a value. For a large reflective part such as a disc, chroma keying also fails because it bounces green across its own face, so take its alpha from fitted geometry and use the key only to find its bounding box. Set both width and height attributes to the FINAL file's real pixels and add height:auto in CSS, since a stale height attribute silently stretches a circle into an ellipse.

## Pinned counter-travel stage

A sticky stage where the product's moving part turns with the scroll while a giant word slides the opposite way behind it.

A section 320vh tall containing a position:sticky, 100svh stage. Centre the product's rotating part at width min(56vw,600px) at z-index 2. Behind it at z-index 1 put a single-line marquee of the section's two-word title repeated three times at clamp(78px,17vw,250px), weight 900, opacity 0.14, white-space:nowrap. Map progress through the section to BOTH a rotation on the part and an opposing horizontal translation on the marquee so they counter-travel. Pin the section label bottom-left and a live mono readout bottom-right, and drive the readout from the same progress value so the number is telling the truth about the rotation.

## Runtime field-swap picker

A variant picker that repaints the entire section field rather than swatching a small preview.

A section whose background-color and color transition over 0.7s. A row of pill buttons each carrying data attributes for a ground, an ink and the values it reveals; clicking one repaints the whole section field and rewrites a three-cell definition panel below it. The panel's dividers MUST be borders coloured with color-mix(in srgb, currentColor 24%, transparent), never a coloured grid showing through 1px gaps: the gap technique needs the cells to paint the section ground, which is being swapped at runtime, so background:inherit resolves to the grid's own ink and the panel fills in solid over its own text. For the same reason nothing in this section may hold a fixed ink colour, so tint currentColor instead of naming a grey, or the body copy drops to about 1.8:1 on the dark options.

## Scroll choreography

Motion as an opt-in enhancement layered over a page that is already complete without it.

Add a 'js' class to the document element ONLY after checking that prefers-reduced-motion is not 'reduce', and scope every reveal rule to that class, so the reduced-motion render and the no-JS render are simply the finished page. Reveal on scroll with one IntersectionObserver (rootMargin '0px 0px -12% 0px', threshold 0.08) that adds an 'in' class and unobserves. Anything already on screen at load, such as the hero word and subject, must reveal on requestAnimationFrame instead and must NOT be observed: on a short viewport it can sit inside the negative bottom margin, never intersect, and stay invisible permanently, which loses the hero's whole signature move on phones. Drive scroll effects from a single passive, rAF-throttled scroll listener. In the hero, translate the word up slightly and the subject down slightly as you leave so they part. Express static emphasis by tinting the colour, never by setting element opacity, so opacity stays a reliable signal of whether a node has revealed. DO NOT animate anything that is not the product's own behaviour.

## Evidence rules

What the page is allowed to claim.

The only claims on the page are the product's own measured specifications. DO NOT invent testimonials, press logos, customer counts, star ratings or awards, and do not add a logo wall. Where the design makes a checkable promise, such as a diagram drawn to scale or a figure tied to a trace, compute it and verify it in the DOM rather than eyeballing it.