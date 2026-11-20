# Depth, draw state and render targets (2026-11-20)

Aegean Skies asked for five things it does by hand today: shader-written depth with a reversed
range, a sampleable depth target, draw state in the public API, a `noinline` for shader helpers,
and a second fragment output. The decisions, and the API they lead to. Every part works on all
five renderers (Vulkan, Metal, OpenGL, WebGL, software); a render test checks each.

## 1. Draw state: public, one setter each (yes)

The raw `glDepthMask`/`glBlendFunc`/... wrappers already reach Vulkan and the software renderer,
but game code should not need GL constants. Setters in the style of `blend()`, applying to
custom `draw`/`draw_instanced` calls (and 2D batches, flushed first) until changed:

```jo
enum Blend: alpha, add, multiply, premultiplied, screen, none   # screen: 1, 1 - src color; none: opaque
enum DepthTest: off, nearer, nearer_or_equal, farther, farther_or_equal, equal, always
enum Cull: none, back, front

blend(.none)
depth_test(.nearer_or_equal)
depth_write(false)
cull(.none)
color_write(false)                # a depth-only pass
```

`DepthTest` names the meaning, not the GL function: under reversed depth (section 3) `.nearer`
is GREATER, so game code does not change with the depth range. Each frame starts from the
documented defaults; the library's own passes (draw_mesh, shadows, sky, post) set what they
need and give the game's selection back.

## 2. Depth targets that can be sampled (yes)

`render_target(w, h, smooth = true, depth_texture = false)`: with `depth_texture = true` the
target's depth is a texture (`rt.depth_texture`), sampled like any other (`sample(t, uv).x`, 0..1).
A pass may not sample the depth (or color) of the target it is drawing into: the draw panics
with a message saying so, on every renderer (WebGL forbids it; elsewhere it is undefined).
`copy_depth(from, to)` copies one target's depth into another's of the same size (a blit on
GL/WebGL, an image copy on Vulkan and Metal, a copy in software), for a pass that tests against
the scene's depth while sampling it. The library's own scene target (post effects on) offers its
depth the same way, so a later pass reads the 3D scene's depth.

## 3. Shader-written depth and reversed depth (yes)

- `set_depth(d)` in a fragment shader writes the fragment's depth (0..1) instead of the
  interpolated one (GLSL `gl_FragDepth`, SPIR-V `FragDepth` + `DepthReplacing`, Metal
  `[[depth(any)]]`, software: the value written and tested). It turns off early depth rejection
  on GPUs for that shader. The fragment input's position field already gives the window
  position, depth and 1/w (`tests/render/fragcoord.jo`).
- Reversed depth, opt-in: float depth, cleared to 0, an infinite far plane, `.nearer` = GREATER.
  The clip z goes to the depth unit without the GL-to-Vulkan remap (no `(z + w) / 2`
  cancellation at a million metres). Vulkan, Metal and the software renderer have it; OpenGL
  and WebGL where clip control exists (`EXT_clip_control`, GL 4.5); elsewhere the call says it
  is not available and the game uses `set_depth` (logarithmic depth) or ordinary depth.

## 4. `noinline` for shader functions (no)

GPU compilers inline every call; GLSL has no way to ask otherwise, and SPIR-V's `DontInline` is a
hint drivers ignore. Sloppy's shader backends never inline or duplicate a function themselves,
so a keyword would do nothing on the phones where link time matters. The tool that works is the
one Aegean found: one call site in a loop over a small array of inputs. docs/GRAPHICS.md says so.

## 5. More than one fragment output (yes, general up to 4)

Rather than one auxiliary output: a fragment shader may return a struct of 1 to 4 `vec4` fields,
written to a render target made with as many color textures (`render_target(w, h, colors = 2)`,
textures `rt.colors[i]`; `rt.texture` is `rt.colors[0]`). Four is what WebGL2 guarantees. A
one-output shader drawn into a multi-color target leaves the other colors unchanged. The
software renderer writes each image. Built after sections 1 to 3.
