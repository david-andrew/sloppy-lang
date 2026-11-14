# API stability

This declaration covers **source names and observable contracts**, including named arguments,
defaults, units, absence, errors, mutation and handle ownership. A contract listed as stable
will not break without a **major version** and migration notes in the changelog. This promise
applies to the stable subset even while the overall language is pre-1.0. Additive APIs and
bug fixes that restore a documented contract may ship in minor/patch releases.

It does not promise binary layouts or ABI, permanent serialized/wire formats, identical pixels
across GPUs, deterministic thread scheduling, or a security certification. The [API reference](API.md)
is a discovery index: inclusion alone does not declare an API stable. Underscore-prefixed
implementation names, storage fields, renderer queues and the private layout bridge are outside
the supported boundary. Use documented operations instead of manipulating their storage.

## Stable now

The following contracts include the decisions implemented in consistency batches 1 and 2.

- **Language values and calls.** Assignment copies ordinary values; arrays/maps/sets/strings
  have copy-on-write semantics, and `mut` parameters modify the caller. UFCS targets the first
  argument. Named/default arguments, closures, optional flattening, `if let`, `??`, explicit
  unwrap/expect, error structs/unions and `?` propagation retain their documented meanings.
  Copying a resource/shared handle copies its identity, not its resource: Channel, Task,
  TaskGroup, Atomic and CookieJar copies share state and can mutate it without `mut`.
  Native file/socket/GPU aliases share ownership and must follow their close/free rules.
- **Core collections.** Array storage operations (`len`, `push`, `pop`, `insert`, `remove_at`,
  `extend`, `clear`, `truncate`, `resize`, `reserve`, `cap`), `map`, `filter`, `retain`, `reduce`,
  `any`, `all`, `count`, `sum`, stable sorting and keyed `sort`/`sorted`/`min`/`max` use their
  documented contracts. Strict empty/index operations panic; safe lookups provide absence.
  `lower_bound`/`upper_bound` return insertion positions. Maps/sets preserve insertion order,
  membership is `contains`/`in`, removal returns bool, and equality/hash remain consistent.
  Ordinary map `get` is stable, and array `index_of` returns an optional index like strings.
- **Text and parsing.** Raw byte length/index/slices and byte search offsets coexist with
  code-point `chars`, `char_count`, `first`, `last`, padding and `trim(chars)`. Whitespace trim
  and whitespace `split()` retain their documented ASCII rules. Use `join(parts, sep)`.
  String `index_of`/`last_index_of`, predicate `find_index`, and `first_overlap` return optional
  indexes; invalid starts give none (start equal to byte length is allowed). `reverse` mutates
  arrays and `reversed` returns a value. `regex` returns Regex or RegexError; `ints` returns
  an array or ParseError. Prompted input returns none at EOF/cancellation.
- **Numbers and geometry.** Scalar math, f32 vector arithmetic, dot/cross, normalization,
  geometric length/distance, matrices, 0–1 colors, full-size Rect x/y/w/h and zero-based
  half-open ranges keep their documented conventions. Float-to-int conversion truncates and
  saturates as documented. Angles use radians, except every `camera3d.fov_degrees` uses degrees.
  Random intervals are half-open; reversed bounds panic and equal bounds return the bound. Seeded Rng and the global generator remain distinct; shuffle mutates.
- **Data and dates.** Typed text/JSON structure rules, error positions, JSON UTF-8 policy and
  strict typed parsing are stable. Dynamic JSON `get(key)`/`get(index)` chain safely through
  none; `as_float` reads floating/integer variants, while `as_int` truncates finite fractions
  and rejects values outside int range. `as_list`/`keys` return [] for noncontainers.
  Date stores whole seconds with its explicit offset; local/UTC interpretation, calendar and
  weekday bases, date_add/date_diff, and flooring of fractional timestamps are documented
  contracts. `date_text` is display text unless a zoned format is supplied;
  `http.parse_http_date` reads GMT HTTP dates. Storage-format longevity is a separate promise.
- **Files and connections.** Checked reads return their value or FileError; streaming line
  reads distinguish EOF from failure and byte failures do not report partial success.
  Bool/optional file operations retain `file_error()` for failure details. Writers put the
  destination first, including `save_png(path, image)` and `save_wav(path, sound)`.
  TCP/TLS connect results own their NetError details; connect/handshake deadlines are separate
  from send/receive deadlines. This does not freeze TLS implementation/security policy.
- **Basic games and audio.** Window/input polling and held/pressed/released distinctions,
  screen/design/pixel coordinates, basic shapes/text positioning, camera2d and screen/world
  conversion are stable with documented platform capability differences. Static sprite
  placement keeps its documented sibling defaults: sprite is top-left, region/frame draws
  are centered; origin offsets placement before rotation and is not a fixed pivot.
  Camera3d's field of view remains degrees. Sound units, voice controls, scheduling, crossfade,
  volume/pan and shared playback-option order are settled: Sound defaults to one play and
  Music to looping. Byte asset loaders return typed errors, including embedded inputs;
  detected streaming music corruption ends playback and `music_error(voice)` takes its error.
  Model decoding's checked result is settled; advanced model/render representation is not.
  Ordinary and instanced classic meshes share specular 0.3 by default.
- **Simple UI and physics conventions.** `ui_` column menus and `hud_` explicit boxes retain
  their distinct leading placement/label arguments. Menu sliders use step/low/high; HUD
  sliders use low/high/step. Single-line fields default to 64 code points. Identity remains
  `id` for HUD and `key` for experimental layout. Physics keeps world-first/body-second,
  generation-checked handles, full box sizes, layer/mask semantics, seconds/radians, 2D pixels
  (mass = density × area / 100) versus 3D meters. Both dimensions call a hinge `hinge`;
  2D motor `limit` is force for sliders and torque for angular motors. Ray/casts exclude
  sensors and overlap queries include them. Solver internals/tuning are excluded.
- **Basic task handles.** Spawn, shared Task results, untimed `Task.wait()` returning its
  result and timed `wait_for(seconds)` returning a completion flag are settled. Channel and
  Atomic handle-copy semantics are settled; cancellation/fairness promises are excluded below.

## Stable after the remaining decisions

These specific areas are **not frozen yet**. Their existing behavior stays documented until a
coordinated change; a deferred proposal is not permission to silently change it.

- **Animation (G7):** settle inclusive numeric frame endpoints, checked animation-name failure,
  and 2D/3D completion policy. Batch 2 aligned `looping` spelling only; it did not change
  endpoint or absent-name behavior.
- **Other graphics choices (G4/G5/G9):** decide whether to freeze vec4 sprite source rectangles
  versus Rect, render_target's default linear filtering versus `smooth_textures`, and Image
  get's transparent-border sentinel versus a checked get/explicit sample operation. Existing
  defaults and sampling behavior were retained. Those exact edge contracts remain provisional.
- **Channel cancellation (T2):** untimed void send can leave an accepted value queued after
  cancellation, or return without enqueueing when already cancelled and no slot/receiver is
  available. Timed/try sends return bool for local acceptance, never remote processing;
  cancellation does not retract accepted values. Tests cover these behaviors. No item-loss bug
  was found requiring a semantic change. The void-send cancellation API remains experimental
  until its acceptance-reporting decision is frozen.

Batches 1/2 resolved the supported documentation boundary, overload descriptions, trim/search/
reversal and parsing/EOF contracts, file reads, checked color/JSON conversions, checked asset
loads, camera units and sprite-anchor documentation, instancing defaults, playback order,
widget limits/documented orders, hinge/motor naming, random bounds, JSON/date names, TCP error
ownership, file-writing order, netplay bind failures and HTTP/listener ordering, timed Task
waiting, and shared-handle/scheduler documentation. No compatibility shims were added.

## Experimental areas

- Responsive `layout`: prior-description hit testing, first appearance, key retention,
  focus/edit lifecycle and widget coverage.
- Shader/compiler/backend details, LitParams/Pixel2D/effect layouts, custom draw hooks,
  GPU buffers/arrays/compute/subgroup behavior and backend-specific guarantees.
- Advanced 3D PBR/environment/model/morph/skin data and renderer queues. The high-level checked
  loading contract does not freeze every model format feature or internal structure.
- 3D physics solver/contact/controller tuning and continuous-collision promises; all World
  implementation storage in both dimensions.
- Netplay wire formats, reconciliation layouts, transport/relay/WebRTC/TURN internals and
  cross-version interoperability. Bind results and explicit unit spellings can stabilize
  independently of those internals.
- Task cancellation/fairness, arbitrary parallel-callback library use and thread-safety policy
  beyond documented shared primitives. Unix run_program yields; Windows run_program blocks
  tasks. General file/C operations do not become asynchronous merely by running in a task.
- Cryptography/TLS internals, HTTP security-policy helpers and sqlite platform/binding details
  unless separately audited and deliberately declared supported.

See [language conventions](LANGUAGE.md), [graphics conventions](GRAPHICS.md), and the
[changelog](../CHANGELOG.md) for the precise current contracts and migration instructions.
