The `pbr_*` scenes use original procedural data, dedicated to CC0/public domain.
`python3 tests/render/pbr_assets.py` regenerates the small glTF fixtures with embedded PNGs.
No external assets are downloaded. The glTF intentionally selects just one mesh in its
scene; tests select its other meshes by changing the node's mesh index before loading.

- `pbr_grid`: metallic 0, 0.5, 1 (top to bottom), roughness 0.08 to 1 (left to right).
- `pbr_normal`: generated versus authored tangent frames, nonuniform scale and UV set 1.
- `pbr_skin`: a normal-mapped glTF mesh at rest and animated, including skinned tangents.
- `pbr_cutout`: alpha masks from both sides and their cutout shadows; packed metallic/
  roughness, AO, colored emissive, and alpha blending.

Initial references were rendered with native GLES on redfox, using a surfaceless EGL
context (no display), and downsampled fourfold with tools/pngutil.py, just as rendertest
stores references. These scenes are static: the first and sixtieth frames are identical.
Keep their geometry within the frame for Apple's software OpenGL rasterizer.
