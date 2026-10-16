# Make a 3D shooter

This tutorial builds **Little Breakwater**, a small version of
[Breakwater](../examples/breakwater/breakwater.jo): a first-person shooter on a deck at sea, where
drones come in waves and you hold them off with a rifle and a shotgun. It is the third tutorial,
after [a platformer](TUTORIAL.md) and [an arcade game](TUTORIAL_REBOUND.md), and the first in 3D:
a camera that is your eyes, walls you bump into, shots that are rays, and things flying at you.
Everything is built from boxes and spheres the program makes itself, so each step is a whole
program that runs; on the website, "Run it in the playground" opens it in your browser, and with
Sloppy installed `sloppy breakwater.jo` runs it in a window.

## 1. A deck at sea, seen through your eyes

```gdscript
# step 1: a deck at sea, seen through your eyes
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

pos = vec3(0, 0, 12)                    # the player's feet
yaw = 0.0
pitch = 0.0

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

update = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    pos += (right * move.x - ahead * move.y) * SPEED * dt

cube = cube_mesh(1.0)

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    text("click, then the mouse looks around and W A S D walk", vec2(30, 30), 24)

window("Little Breakwater", 1280, 720)
```

3D positions are `vec3`s, in meters: x to the right, y up, and z toward you, so walking "into the
screen" is going along -z. `camera3d(eye, target, fov)` puts the camera at one point looking at
another, with a field of view in degrees; everything drawn after it is seen through it.

The world is one mesh, drawn many times. `cube_mesh(1.0)` is a 1 m cube centered on the origin, and
a transform places each copy: `translation(center) * scaling(size)` stretches it to a box's size,
then moves it to its place (read the product from right to left: scale first, then move). The sea
is the same cube, 400 m wide and far below; the deck is 40 by 30 m with its top at y = 0; a `Box`
is cover, given by its lowest and highest corners.

Where you look is two angles: `yaw` turns you left and right, `pitch` up and down. `look_dir`
turns them into a direction: at yaw 0 it is -z, and a bigger yaw turns left. Clicking calls
`mouse_lock()`, which hides the pointer and keeps it in the window; after that, `mouse_delta()` is
how far the mouse moved this frame, and moving it turns the view. (In a browser, Escape gives the
mouse back; click again to look.)

`input_axis()` is W A S D (or the arrows, or a gamepad's stick) as a 2D vector with y pointing down
the screen, so W is y = -1. Walking turns it the way you face: forward is `look_dir(yaw, 0.0)`
along the ground, and right is the same a quarter turn clockwise.

## 2. Cover that stops you, and jumping onto it

```gdscript
# step 2: cover that stops you, and jumping onto it
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

update = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)

cube = cube_mesh(1.0)

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    text("Space jumps", vec2(30, 30), 24)

window("Little Breakwater", 1280, 720)
```

You are a circle on the ground, `RADIUS` wide, with feet at `pos`. `collide` takes where you would
move and pushes you out of every box you overlap: the nearest point of a box's footprint (`q`, the
position clamped into the box's x and z) is less than `RADIUS` away, so you move away from it until
it is exactly `RADIUS` away. You slide along walls instead of stopping dead, because only the part
of the move that goes into the wall is taken away. Boxes whose top is below your feet are left out:
you are standing on them. This tutorial writes its own simple collision so you can see how it
works; a bigger game can use `import physics3d`, with rigid bodies, `w.raycast`, and
`w.character(...)` and `w.walk(...)` for a walking capsule.

Gravity is an acceleration: it changes the velocity, by `GRAVITY * dt` a frame, and the velocity
changes the position, by `vel * dt`. Half the frame's change to the velocity comes before the move
and half after, so the move uses the velocity halfway through the frame: then a jump goes exactly
as high whatever the frame rate. `ground_under` is what you would stand on: the deck at 0, or the
top of a box you are over. Reaching it, you stop falling and are `grounded`; only then does Space
jump. Up and down are settled first, then the move across, so a box you have just landed on is
under you, not in your way. The low boxes are
1.1 m tall and a jump reaches about 1.2 m: try climbing onto one.

## 3. A rifle

```gdscript
# step 3: a rifle
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const MAG = 30                          # rounds in a magazine
const GAP = 0.1                         # seconds between shots
const SPREAD = 0.012                    # how far a shot strays (radians)
const RELOAD = 1.5                      # seconds

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

ammo = MAG
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the rifle's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

tracers: Tracer[]
sparks: Spark[]

fire = ():
    ammo -= 1
    wait = GAP
    kick = 0.06
    o = eye()
    d = scatter(aim(), SPREAD)
    far = ray_world(o, d, 100)
    stop = o + d * far
    # (the streak starts at the rifle's muzzle: ahead, right and down of the eye)
    tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
    if far < 100.0:
        loop i in [0..3): sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the rifle: fires while the button is held; R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo = MAG
    else if key_pressed(.r) and ammo < MAG or ammo == 0: reloading = RELOAD
    if mouse_down(.left) and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo > 0: fire()

update = (dt: f64):
    step_player(dt)
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)

cube = cube_mesh(1.0)
rifle = Mesh()

# the rifle, from boxes (its barrel along -z)
make_meshes = ():
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    rifle = custom_mesh(r)

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)
    # the rifle in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(rifle, hold, cast_shadow = false, in_front = true)
    # the reticle, and the rounds left
    circle(vec2(640, 360), 3, rgba(1, 1, 1, 0.8))
    text("RIFLE  {ammo} / {MAG}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)

make_meshes()
window("Little Breakwater", 1280, 720)
```

A rifle bullet is too fast to see, so a shot is a ray: a line from your eye along where you look,
and whatever it meets first is hit, at once. `ray_box` finds where a ray enters a box. Along each
axis the box is a slab between two planes, and the ray is inside it from one distance to another;
the ray is in the box where it is inside all three slabs at once, from the largest of the three
starts (`t0`) to the smallest of the ends (`t1`). If those cross, it misses. `d[i]` is the i-th part
of a vector, so one loop does x, y and z. `ray_world` is the nearest of the deck and every box.

`scatter` turns the aim a little at random (up to `SPREAD` radians), so shots spread. A `Tracer` is
the shot's streak for a twentieth of a second: `beam` stretches the cube from the muzzle to where
the shot landed, turned to point along it: `facing(d)` is the turn that points a model's front (-z)
along `d`. Sparks are the cube again, small, flying and falling.

The rifle is drawn in front of you, wherever you look. `look_at` is the camera's view (the world as
the camera sees it), and its inverse takes points the other way, from in front of the camera into
the world. So `view * translation(...)` puts the rifle 0.2 m right, 0.19 m down and half a meter
ahead of your eye, and `in_front = true` draws it over everything, so it never goes into a wall.
`kick` pushes it back with each shot and eases it forward again.

The rifle fires while the button is held, every `GAP` seconds, until the magazine is empty;
reloading takes `RELOAD` seconds, and starts by itself when you run out.

## 4. Drones to shoot

```gdscript
# step 4: drones to shoot
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const MAG = 30                          # rounds in a magazine
const GAP = 0.1                         # seconds between shots
const SPREAD = 0.012                    # how far a shot strays (radians)
const RELOAD = 1.5                      # seconds
const DAMAGE = 12.0                     # a shot's
const DRONE_R = 0.5                     # a drone's size (the radius shots hit)

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
flat = (v: vec3) -> vec3: vec3(v.x, 0, v.z)
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

# how far along d a ray from o goes into a sphere (-1: it misses)
ray_sphere = (o: vec3, d: vec3, c: vec3, r: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    if q <= 0.0: return 0                               # (o is inside it)
    if b * b - q < 0.0: return -1
    t = -b - sqrt(b * b - q)
    if t < 0.0: return -1
    t

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

ammo = MAG
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the rifle's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

struct Drone:
    pos: vec3                           # (its middle)
    vel: vec3
    health: f64
    strafe: f32 = 1                     # which way it circles the player
    flash: f64 = 0.0                    # just hit

tracers: Tracer[]
sparks: Spark[]
drones: Drone[]
score = 0

burst = (at: vec3, n: int):
    loop i in [0..n): sparks.push(Spark(at, scatter(vec3(0, 1, 0), 2.0) * random(3.0, 9.0), random(0.3, 0.7)))

fire = ():
    ammo -= 1
    wait = GAP
    kick = 0.06
    o = eye()
    d = scatter(aim(), SPREAD)
    # (the nearest of what it meets: cover, the deck, or a drone)
    far = ray_world(o, d, 100)
    who = -1
    loop i in 0.. and dr in drones:
        t = ray_sphere(o, d, dr.pos, DRONE_R)
        if t >= 0.0 and t < far:
            far = t
            who = i
    stop = o + d * far
    # (the streak starts at the rifle's muzzle: ahead, right and down of the eye)
    tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
    if who >= 0:
        drones[who].health -= DAMAGE
        drones[who].flash = 0.1
        drones[who].vel += d * 1.5
    else if far < 100.0:
        loop i in [0..3): sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))

step_drones = (dt: f64):
    # (all down: four more, from the far side)
    if drones.len() == 0:
        loop i in [0..4): drones.push(Drone(vec3(random(-HALF_X + 2.0, HALF_X - 2.0), 3, -HALF_Z + 1.0), vec3(0, 0, 0), 30, strafe = random_int(0, 2) * 2 - 1))
    loop mut d in drones:
        # (shot down: it bursts, and does nothing more)
        if d.health <= 0.0:
            burst(d.pos, 24)
            score += 100
            continue
        to = flat(eye() - d.pos)
        dist = length(to)
        dir = to * (1.0 / max(dist, 0.01))
        side = vec3(-dir.z, 0, dir.x)
        # keep 7 to 14 m away, circling, bobbing at 1.5 to 3 m
        want = side * d.strafe * 2.0
        if dist > 14.0: want += dir * 4.0
        if dist < 7.0: want -= dir * 4.0
        want.y = 2.2 + sin(elapsed() * 1.3 + d.strafe) * 0.7 - d.pos.y
        d.vel += (want - d.vel) * min(1.0, 2.0 * dt)
        p = collide(d.pos + d.vel * dt - vec3(0, DRONE_R, 0), DRONE_R)
        d.pos = p + vec3(0, DRONE_R, 0)
        if random() < dt * 0.3: d.strafe = -d.strafe
        d.flash -= dt
    drones = drones.filter((d): d.health > 0.0)

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the rifle: fires while the button is held; R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo = MAG
    else if key_pressed(.r) and ammo < MAG or ammo == 0: reloading = RELOAD
    if mouse_down(.left) and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo > 0: fire()

update = (dt: f64):
    step_player(dt)
    step_drones(dt)
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)

cube = cube_mesh(1.0)
rifle = Mesh()
drone_mesh = Mesh()
eye_mesh = sphere_mesh(0.14, 12, 8)

# a drone: a ball with a band and two fins; the rifle, from boxes (its barrel along -z)
make_meshes = ():
    v: Vertex3D[]
    add_sphere(v, vec3(0, 0, 0), DRONE_R, rgb(0.8, 0.8, 0.82), 16, 10)
    add_cylinder(v, vec3(0, -0.08, 0), 0.53, 0.16, rgb(0.9, 0.45, 0.1), 20)
    add_box(v, vec3(0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    add_box(v, vec3(-0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    drone_mesh = custom_mesh(v)
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    rifle = custom_mesh(r)

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    # drones, facing the player, their eyes glowing; white for a moment when hit
    loop d in drones:
        to_me = normalize(flat(eye() - d.pos))
        tint = vec4(1, 1, 1, 1)
        if d.flash > 0.0: tint = vec4(2, 2, 2, 1)
        draw_mesh(drone_mesh, translation(d.pos) * facing(to_me), tint)
        draw_mesh(eye_mesh, translation(d.pos + to_me * (DRONE_R - 0.06)), rgb(1, 0.15, 0.1), emissive = 0.6)
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)
    # the rifle in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(rifle, hold, cast_shadow = false, in_front = true)
    # the reticle, and the rounds left
    circle(vec2(640, 360), 3, rgba(1, 1, 1, 0.8))
    text("RIFLE  {ammo} / {MAG}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)
    text("{score}", vec2(40, 30), 28)

make_meshes()
window("Little Breakwater", 1280, 720)
```

A drone is a ball you can hit, so it needs one more ray test: `ray_sphere`. The point of a ray
nearest the sphere's center is `-b` along it (`b` is how far the center is behind the start, along
the ray); the ray meets the sphere if that point is closer to the center than the radius, and enters
it a little before. A ray that starts inside the sphere (your eye inside a drone) hits it at 0. A shot checks every drone and keeps the nearest hit, but only if it is nearer
than the cover the ray would hit: drones behind a box are safe.

Drones steer by wanting a velocity and easing toward it. `want` circles you (`side` is a quarter
turn from the way to you, and `strafe` picks which way), comes closer from far away and backs off
when you are near, and bobs up and down. `d.vel += (want - d.vel) * min(1.0, 2.0 * dt)` closes
part of the gap each frame, so they drift into turns instead of snapping. They bump into cover
with the same `collide` as you, and now and then change which way they circle.

Each drone is a mesh built once from shapes: `add_sphere`, `add_cylinder` and `add_box` add each
shape's triangles to an array, and `custom_mesh` makes one mesh of them all. Its eye is a separate
small sphere, so it can glow by itself: `emissive` is how much a surface gives off light instead of
taking it from the sun.

## 5. They fire back

```gdscript
# step 5: they fire back
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const MAG = 30                          # rounds in a magazine
const GAP = 0.1                         # seconds between shots
const SPREAD = 0.012                    # how far a shot strays (radians)
const RELOAD = 1.5                      # seconds
const DAMAGE = 12.0                     # a shot's
const DRONE_R = 0.5                     # a drone's size (the radius shots hit)
const SHIELD = 60.0
const HEALTH = 60.0
const RECHARGE_WAIT = 3.0               # seconds out of fire before the shield comes back

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
flat = (v: vec3) -> vec3: vec3(v.x, 0, v.z)
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer, a bolt)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

# how far along d a ray from o goes into a sphere (-1: it misses)
ray_sphere = (o: vec3, d: vec3, c: vec3, r: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    if q <= 0.0: return 0                               # (o is inside it)
    if b * b - q < 0.0: return -1
    t = -b - sqrt(b * b - q)
    if t < 0.0: return -1
    t

clear_line = (a: vec3, b: vec3) -> bool: ray_world(a, normalize(b - a), length(b - a)) >= length(b - a) - 0.01
# is p inside cover?
in_cover = (p: vec3) -> bool:
    loop b in boxes:
        if p.x >= b.lo.x and p.x <= b.hi.x and p.y <= b.hi.y and p.z >= b.lo.z and p.z <= b.hi.z: return true
    false

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0
shield = SHIELD
health = HEALTH
calm = 0.0                              # seconds since a hit

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

ammo = MAG
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the rifle's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

struct Drone:
    pos: vec3                           # (its middle)
    vel: vec3
    health: f64
    cool: f64                           # seconds until it fires
    windup: f64 = 0.0                   # about to fire (its eye glows)
    strafe: f32 = 1                     # which way it circles the player
    flash: f64 = 0.0                    # just hit

struct Bolt:
    pos: vec3
    vel: vec3
    life: f64

tracers: Tracer[]
sparks: Spark[]
drones: Drone[]
bolts: Bolt[]
score = 0

new_run = ():
    pos = vec3(0, 0, 12)
    vel = vec3(0, 0, 0)
    yaw = 0
    pitch = 0
    shield = SHIELD
    health = HEALTH
    ammo = MAG
    reloading = 0
    drones = []
    bolts = []
    score = 0

# the shield takes hits first; then health; with none left, start again
hurt = (dmg: f64):
    calm = 0
    left = dmg - shield
    shield = max(0.0, shield - dmg)
    if left > 0.0: health -= left
    if health <= 0.0: new_run()

burst = (at: vec3, n: int):
    loop i in [0..n): sparks.push(Spark(at, scatter(vec3(0, 1, 0), 2.0) * random(3.0, 9.0), random(0.3, 0.7)))

fire = ():
    ammo -= 1
    wait = GAP
    kick = 0.06
    o = eye()
    d = scatter(aim(), SPREAD)
    # (the nearest of what it meets: cover, the deck, or a drone)
    far = ray_world(o, d, 100)
    who = -1
    loop i in 0.. and dr in drones:
        t = ray_sphere(o, d, dr.pos, DRONE_R)
        if t >= 0.0 and t < far:
            far = t
            who = i
    stop = o + d * far
    # (the streak starts at the rifle's muzzle: ahead, right and down of the eye)
    tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
    if who >= 0:
        drones[who].health -= DAMAGE
        drones[who].flash = 0.1
        drones[who].vel += d * 1.5
    else if far < 100.0:
        loop i in [0..3): sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))

step_drones = (dt: f64):
    # (all down: four more, from the far side)
    if drones.len() == 0:
        loop i in [0..4): drones.push(Drone(vec3(random(-HALF_X + 2.0, HALF_X - 2.0), 3, -HALF_Z + 1.0), vec3(0, 0, 0), 30, random(1.0, 3.0), strafe = random_int(0, 2) * 2 - 1))
    loop mut d in drones:
        # (shot down: it bursts, and does nothing more)
        if d.health <= 0.0:
            burst(d.pos, 24)
            score += 100
            continue
        to = flat(eye() - d.pos)
        dist = length(to)
        dir = to * (1.0 / max(dist, 0.01))
        side = vec3(-dir.z, 0, dir.x)
        # keep 7 to 14 m away, circling, bobbing at 1.5 to 3 m
        want = side * d.strafe * 2.0
        if dist > 14.0: want += dir * 4.0
        if dist < 7.0: want -= dir * 4.0
        want.y = 2.2 + sin(elapsed() * 1.3 + d.strafe) * 0.7 - d.pos.y
        d.vel += (want - d.vel) * min(1.0, 2.0 * dt)
        p = collide(d.pos + d.vel * dt - vec3(0, DRONE_R, 0), DRONE_R)
        d.pos = p + vec3(0, DRONE_R, 0)
        if random() < dt * 0.3: d.strafe = -d.strafe
        d.flash -= dt
        # firing: a glowing eye for 0.6 s, then a bolt at the player's chest
        if d.windup > 0.0:
            d.windup -= dt
            if d.windup <= 0.0:
                at = eye() - vec3(0, 0.3, 0)
                bolts.push(Bolt(d.pos, scatter(normalize(at - d.pos), 0.03) * 16.0, 4.0))
                d.cool = random(2.0, 3.5)
        else:
            d.cool -= dt
            if d.cool <= 0.0 and clear_line(d.pos, eye()): d.windup = 0.6
    drones = drones.filter((d): d.health > 0.0)
    # bolts: stopped by cover; the player is hit within half a meter of the body (they move
    # in steps of at most 20 cm, so a slow frame cannot carry one through a wall, or you)
    taken = 0.0
    loop mut b in bolts:
        b.life -= dt
        n = int(ceil(length(b.vel) * dt / 0.2))
        loop k in [0..n):
            b.pos += b.vel * (dt / n)
            if in_cover(b.pos) or b.pos.y <= 0.0:
                b.life = 0
                break
            q = vec3(pos.x, clamp(b.pos.y, pos.y + 0.3, eye().y), pos.z)
            if length(b.pos - q) < 0.5:
                b.life = 0
                taken += 10.0
                break
    bolts = bolts.filter((b): b.life > 0.0)
    # (after the loop: a hit that ends the run starts a new one, bolts and all)
    if taken > 0.0: hurt(taken)

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the shield comes back out of fire
    calm += dt
    if calm > RECHARGE_WAIT: shield = min(SHIELD, shield + 30.0 * dt)
    # the rifle: fires while the button is held; R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo = MAG
    else if key_pressed(.r) and ammo < MAG or ammo == 0: reloading = RELOAD
    if mouse_down(.left) and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo > 0: fire()

update = (dt: f64):
    step_player(dt)
    step_drones(dt)
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)

cube = cube_mesh(1.0)
rifle = Mesh()
drone_mesh = Mesh()
eye_mesh = sphere_mesh(0.14, 12, 8)

# a drone: a ball with a band and two fins; the rifle, from boxes (its barrel along -z)
make_meshes = ():
    v: Vertex3D[]
    add_sphere(v, vec3(0, 0, 0), DRONE_R, rgb(0.8, 0.8, 0.82), 16, 10)
    add_cylinder(v, vec3(0, -0.08, 0), 0.53, 0.16, rgb(0.9, 0.45, 0.1), 20)
    add_box(v, vec3(0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    add_box(v, vec3(-0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    drone_mesh = custom_mesh(v)
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    rifle = custom_mesh(r)

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    # drones, facing the player, their eyes glowing; white for a moment when hit
    loop d in drones:
        to_me = normalize(flat(eye() - d.pos))
        tint = vec4(1, 1, 1, 1)
        if d.flash > 0.0: tint = vec4(2, 2, 2, 1)
        draw_mesh(drone_mesh, translation(d.pos) * facing(to_me), tint)
        glow = 0.6
        if d.windup > 0.0: glow = 0.6 + (0.6 - d.windup) * 5.0
        draw_mesh(eye_mesh, translation(d.pos + to_me * (DRONE_R - 0.06)), rgb(1, 0.15, 0.1), emissive = glow)
    loop b in bolts: draw_mesh(cube, beam(b.pos - normalize(b.vel) * 0.6, b.pos, 0.08), rgb(1.0, 0.45, 0.15), emissive = 2.0, cast_shadow = false)
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)
    # the rifle in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(rifle, hold, cast_shadow = false, in_front = true)
    # the reticle, and the rounds left
    circle(vec2(640, 360), 3, rgba(1, 1, 1, 0.8))
    text("RIFLE  {ammo} / {MAG}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)
    text("{score}", vec2(40, 30), 28)
    # the shield and health; the screen reddens for a moment when hit
    rect(40, 650, 300, 10, rgba(0, 0, 0, 0.4))
    rect(40, 650, 300.0 * shield / SHIELD, 10, rgb(0.4, 0.85, 1))
    rect(40, 666, 300, 6, rgba(0, 0, 0, 0.4))
    rect(40, 666, 300.0 * health / HEALTH, 6, rgb(1, 0.4, 0.35))
    if calm < 0.25: rect(0, 0, 1280, 720, rgba(1, 0, 0, 0.25 - calm))

make_meshes()
window("Little Breakwater", 1280, 720)
```

The drones' shots are not rays but bolts you can see coming and step away from: each has a velocity
and moves every frame, and is gone when it flies into cover (`in_cover`) or the deck.
You are hit by a bolt within half a meter of your body, the line from just above your feet to your
eyes. A bolt moves in steps of at most 20 cm: in one slow frame it could otherwise jump from one
side of a wall (or of you) to the other without ever being inside.

Before a drone fires, its eye glows for 0.6 seconds: a warning you can act on, the most useful
thing an enemy can do for the player. It only winds up if it can see you: `clear_line` asks whether
a ray from the drone reaches your eyes before any cover.

Hits take the shield first and health after it. The shield comes back after `RECHARGE_WAIT`
seconds out of fire, so the game is about stepping behind cover between fights; health does not
come back. The bars and the red flash are 2D, drawn after the 3D world, over it.

## 6. A shotgun

```gdscript
# step 6: a shotgun
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const DRONE_R = 0.5                     # a drone's size (the radius shots hit)
const SHIELD = 60.0
const HEALTH = 60.0
const RECHARGE_WAIT = 3.0               # seconds out of fire before the shield comes back

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
flat = (v: vec3) -> vec3: vec3(v.x, 0, v.z)
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer, a bolt)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

# how far along d a ray from o goes into a sphere (-1: it misses)
ray_sphere = (o: vec3, d: vec3, c: vec3, r: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    if q <= 0.0: return 0                               # (o is inside it)
    if b * b - q < 0.0: return -1
    t = -b - sqrt(b * b - q)
    if t < 0.0: return -1
    t

clear_line = (a: vec3, b: vec3) -> bool: ray_world(a, normalize(b - a), length(b - a)) >= length(b - a) - 0.01
# is p inside cover?
in_cover = (p: vec3) -> bool:
    loop b in boxes:
        if p.x >= b.lo.x and p.x <= b.hi.x and p.y <= b.hi.y and p.z >= b.lo.z and p.z <= b.hi.z: return true
    false

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0
shield = SHIELD
health = HEALTH
calm = 0.0                              # seconds since a hit

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

# the weapons: what each does
struct Gun:
    name: str
    mag: int                            # rounds in a magazine
    gap: f64                            # seconds between shots
    auto: bool                          # fires while the button is held
    pellets: int                        # rays a shot (a shotgun's are many)
    spread: f64                         # how far they stray (radians)
    damage: f64                         # a pellet's
    reload: f64                         # seconds

guns = [Gun("RIFLE", 30, 0.1, true, 1, 0.012, 12, 1.5), Gun("SHOTGUN", 6, 0.7, false, 14, 0.1, 9, 2.0)]
held = 0                                # the one in hand
ammo = [loop g in guns: g.mag]          # each one's rounds
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the weapon's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

struct Drone:
    pos: vec3                           # (its middle)
    vel: vec3
    health: f64
    cool: f64                           # seconds until it fires
    windup: f64 = 0.0                   # about to fire (its eye glows)
    strafe: f32 = 1                     # which way it circles the player
    flash: f64 = 0.0                    # just hit

struct Bolt:
    pos: vec3
    vel: vec3
    life: f64

tracers: Tracer[]
sparks: Spark[]
drones: Drone[]
bolts: Bolt[]
score = 0

new_run = ():
    pos = vec3(0, 0, 12)
    vel = vec3(0, 0, 0)
    yaw = 0
    pitch = 0
    shield = SHIELD
    health = HEALTH
    ammo = [loop g in guns: g.mag]
    held = 0
    reloading = 0
    drones = []
    bolts = []
    score = 0

# the shield takes hits first; then health; with none left, start again
hurt = (dmg: f64):
    calm = 0
    left = dmg - shield
    shield = max(0.0, shield - dmg)
    if left > 0.0: health -= left
    if health <= 0.0: new_run()

burst = (at: vec3, n: int):
    loop i in [0..n): sparks.push(Spark(at, scatter(vec3(0, 1, 0), 2.0) * random(3.0, 9.0), random(0.3, 0.7)))

fire = ():
    g = guns[held]
    ammo[held] -= 1
    wait = g.gap
    kick = 0.06
    o = eye()
    loop k in [0..g.pellets):
        d = scatter(aim(), g.spread)
        # (the nearest of what it meets: cover, the deck, or a drone)
        far = ray_world(o, d, 100)
        who = -1
        loop i in 0.. and dr in drones:
            t = ray_sphere(o, d, dr.pos, DRONE_R)
            if t >= 0.0 and t < far:
                far = t
                who = i
        stop = o + d * far
        # (the streak starts at the muzzle: ahead, right and down of the eye)
        tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
        if who >= 0:
            drones[who].health -= g.damage
            drones[who].flash = 0.1
            drones[who].vel += d * 1.5
        else if far < 100.0: sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))

step_drones = (dt: f64):
    # (all down: four more, from the far side)
    if drones.len() == 0:
        loop i in [0..4): drones.push(Drone(vec3(random(-HALF_X + 2.0, HALF_X - 2.0), 3, -HALF_Z + 1.0), vec3(0, 0, 0), 30, random(1.0, 3.0), strafe = random_int(0, 2) * 2 - 1))
    loop mut d in drones:
        # (shot down: it bursts, and does nothing more)
        if d.health <= 0.0:
            burst(d.pos, 24)
            score += 100
            continue
        to = flat(eye() - d.pos)
        dist = length(to)
        dir = to * (1.0 / max(dist, 0.01))
        side = vec3(-dir.z, 0, dir.x)
        # keep 7 to 14 m away, circling, bobbing at 1.5 to 3 m
        want = side * d.strafe * 2.0
        if dist > 14.0: want += dir * 4.0
        if dist < 7.0: want -= dir * 4.0
        want.y = 2.2 + sin(elapsed() * 1.3 + d.strafe) * 0.7 - d.pos.y
        d.vel += (want - d.vel) * min(1.0, 2.0 * dt)
        p = collide(d.pos + d.vel * dt - vec3(0, DRONE_R, 0), DRONE_R)
        d.pos = p + vec3(0, DRONE_R, 0)
        if random() < dt * 0.3: d.strafe = -d.strafe
        d.flash -= dt
        # firing: a glowing eye for 0.6 s, then a bolt at the player's chest
        if d.windup > 0.0:
            d.windup -= dt
            if d.windup <= 0.0:
                at = eye() - vec3(0, 0.3, 0)
                bolts.push(Bolt(d.pos, scatter(normalize(at - d.pos), 0.03) * 16.0, 4.0))
                d.cool = random(2.0, 3.5)
        else:
            d.cool -= dt
            if d.cool <= 0.0 and clear_line(d.pos, eye()): d.windup = 0.6
    drones = drones.filter((d): d.health > 0.0)
    # bolts: stopped by cover; the player is hit within half a meter of the body (they move
    # in steps of at most 20 cm, so a slow frame cannot carry one through a wall, or you)
    taken = 0.0
    loop mut b in bolts:
        b.life -= dt
        n = int(ceil(length(b.vel) * dt / 0.2))
        loop k in [0..n):
            b.pos += b.vel * (dt / n)
            if in_cover(b.pos) or b.pos.y <= 0.0:
                b.life = 0
                break
            q = vec3(pos.x, clamp(b.pos.y, pos.y + 0.3, eye().y), pos.z)
            if length(b.pos - q) < 0.5:
                b.life = 0
                taken += 10.0
                break
    bolts = bolts.filter((b): b.life > 0.0)
    # (after the loop: a hit that ends the run starts a new one, bolts and all)
    if taken > 0.0: hurt(taken)

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the shield comes back out of fire
    calm += dt
    if calm > RECHARGE_WAIT: shield = min(SHIELD, shield + 30.0 * dt)
    # weapons: 1 and 2 choose (Q, the next); R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    swap = -1
    if key_pressed(.n1): swap = 0
    if key_pressed(.n2): swap = 1
    if key_pressed(.q): swap = (held + 1) % guns.len()
    if swap >= 0 and swap != held:
        held = swap
        reloading = 0
        wait = 0.3
    g = guns[held]
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo[held] = g.mag
    else if key_pressed(.r) and ammo[held] < g.mag or ammo[held] == 0: reloading = g.reload
    # (the rifle fires while the button is held, the shotgun once a click)
    trigger = mouse_pressed(.left)
    if g.auto: trigger = mouse_down(.left)
    if trigger and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo[held] > 0: fire()

update = (dt: f64):
    step_player(dt)
    step_drones(dt)
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)

cube = cube_mesh(1.0)
gun_meshes: Mesh[]
drone_mesh = Mesh()
eye_mesh = sphere_mesh(0.14, 12, 8)

# a drone: a ball with a band and two fins; the weapons, from boxes (their barrels along -z)
make_meshes = ():
    v: Vertex3D[]
    add_sphere(v, vec3(0, 0, 0), DRONE_R, rgb(0.8, 0.8, 0.82), 16, 10)
    add_cylinder(v, vec3(0, -0.08, 0), 0.53, 0.16, rgb(0.9, 0.45, 0.1), 20)
    add_box(v, vec3(0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    add_box(v, vec3(-0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    drone_mesh = custom_mesh(v)
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    s: Vertex3D[]
    add_box(s, vec3(0, 0.01, -0.22), vec3(0.05, 0.05, 0.42), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.045, -0.24), vec3(0.06, 0.045, 0.16), rgb(0.55, 0.32, 0.15))
    add_box(s, vec3(0, 0, 0.04), vec3(0.065, 0.09, 0.14), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.03, 0.18), vec3(0.05, 0.08, 0.16), rgb(0.55, 0.32, 0.15))
    gun_meshes = [custom_mesh(r), custom_mesh(s)]

draw = ():
    clear(BLACK)
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    camera3d(eye(), eye() + aim(), 70.0)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    # drones, facing the player, their eyes glowing; white for a moment when hit
    loop d in drones:
        to_me = normalize(flat(eye() - d.pos))
        tint = vec4(1, 1, 1, 1)
        if d.flash > 0.0: tint = vec4(2, 2, 2, 1)
        draw_mesh(drone_mesh, translation(d.pos) * facing(to_me), tint)
        glow = 0.6
        if d.windup > 0.0: glow = 0.6 + (0.6 - d.windup) * 5.0
        draw_mesh(eye_mesh, translation(d.pos + to_me * (DRONE_R - 0.06)), rgb(1, 0.15, 0.1), emissive = glow)
    loop b in bolts: draw_mesh(cube, beam(b.pos - normalize(b.vel) * 0.6, b.pos, 0.08), rgb(1.0, 0.45, 0.15), emissive = 2.0, cast_shadow = false)
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)
    # the weapon in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(gun_meshes[held], hold, cast_shadow = false, in_front = true)
    # the reticle (for the shotgun, a ring as wide as its spread), and the rounds left
    if held == 0: circle(vec2(640, 360), 3, rgba(1, 1, 1, 0.8))
    else: ring(vec2(640, 360), 50, 2, rgba(1, 1, 1, 0.8))
    text("{guns[held].name}  {ammo[held]} / {guns[held].mag}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)
    text("{score}", vec2(40, 30), 28)
    # the shield and health; the screen reddens for a moment when hit
    rect(40, 650, 300, 10, rgba(0, 0, 0, 0.4))
    rect(40, 650, 300.0 * shield / SHIELD, 10, rgb(0.4, 0.85, 1))
    rect(40, 666, 300, 6, rgba(0, 0, 0, 0.4))
    rect(40, 666, 300.0 * health / HEALTH, 6, rgb(1, 0.4, 0.35))
    if calm < 0.25: rect(0, 0, 1280, 720, rgba(1, 0, 0, 0.25 - calm))

make_meshes()
window("Little Breakwater", 1280, 720)
```

The weapons are now data: a `Gun` says what each does, and the code reads it. A shotgun is a
`Gun` like the rifle with different numbers: it fires 14 pellets a shot, each a ray, spread over a
wide cone; it fires once a click instead of while held, and has six shells. Everything else, from
reloading to the streaks, is the same code. A third weapon is one more line in `guns`, one more
mesh, and a number key to choose it (Q already goes through all of them).

1 and 2 pick a weapon, and Q goes to the next. Each keeps its own rounds (`ammo` is an array with one number
per weapon, made from `guns`: `[loop g in guns: g.mag]` is each one's magazine), and swapping cancels a reload.

## 7. Waves, a title and a best score

```gdscript
# step 7: waves, a title and a best score
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const DRONE_R = 0.5                     # a drone's size (the radius shots hit)
const SHIELD = 60.0
const HEALTH = 60.0
const RECHARGE_WAIT = 3.0               # seconds out of fire before the shield comes back

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
flat = (v: vec3) -> vec3: vec3(v.x, 0, v.z)
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer, a bolt)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

# how far along d a ray from o goes into a sphere (-1: it misses)
ray_sphere = (o: vec3, d: vec3, c: vec3, r: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    if q <= 0.0: return 0                               # (o is inside it)
    if b * b - q < 0.0: return -1
    t = -b - sqrt(b * b - q)
    if t < 0.0: return -1
    t

clear_line = (a: vec3, b: vec3) -> bool: ray_world(a, normalize(b - a), length(b - a)) >= length(b - a) - 0.01
# is p inside cover?
in_cover = (p: vec3) -> bool:
    loop b in boxes:
        if p.x >= b.lo.x and p.x <= b.hi.x and p.y <= b.hi.y and p.z >= b.lo.z and p.z <= b.hi.z: return true
    false

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0
shield = SHIELD
health = HEALTH
calm = 0.0                              # seconds since a hit

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

# the weapons: what each does
struct Gun:
    name: str
    mag: int                            # rounds in a magazine
    gap: f64                            # seconds between shots
    auto: bool                          # fires while the button is held
    pellets: int                        # rays a shot (a shotgun's are many)
    spread: f64                         # how far they stray (radians)
    damage: f64                         # a pellet's
    reload: f64                         # seconds

guns = [Gun("RIFLE", 30, 0.1, true, 1, 0.012, 12, 1.5), Gun("SHOTGUN", 6, 0.7, false, 14, 0.1, 9, 2.0)]
held = 0                                # the one in hand
ammo = [loop g in guns: g.mag]          # each one's rounds
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the weapon's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

struct Drone:
    pos: vec3                           # (its middle)
    vel: vec3
    health: f64
    cool: f64                           # seconds until it fires
    windup: f64 = 0.0                   # about to fire (its eye glows)
    strafe: f32 = 1                     # which way it circles the player
    flash: f64 = 0.0                    # just hit

struct Bolt:
    pos: vec3
    vel: vec3
    life: f64

tracers: Tracer[]
sparks: Spark[]
drones: Drone[]
bolts: Bolt[]

# a run: waves of drones, between a title and its end
enum Screen: title, play, over
screen = Screen.title
wave = 0
to_spawn = 0                            # drones still to come this wave
spawn_wait = 0.0
score = 0
best = to_int(load_data("best") ?? "0") ?? 0

new_run = ():
    pos = vec3(0, 0, 12)
    vel = vec3(0, 0, 0)
    yaw = 0
    pitch = 0
    shield = SHIELD
    health = HEALTH
    ammo = [loop g in guns: g.mag]
    held = 0
    reloading = 0
    drones = []
    bolts = []
    wave = 0
    to_spawn = 0
    score = 0

# the shield takes hits first; then health; with none left, the run is over
hurt = (dmg: f64):
    calm = 0
    left = dmg - shield
    shield = max(0.0, shield - dmg)
    if left > 0.0: health -= left
    if health <= 0.0:
        screen = .over
        mouse_lock(false)
        if score > best:
            best = score
            save_data("best", "{best}")

burst = (at: vec3, n: int):
    loop i in [0..n): sparks.push(Spark(at, scatter(vec3(0, 1, 0), 2.0) * random(3.0, 9.0), random(0.3, 0.7)))

fire = ():
    g = guns[held]
    ammo[held] -= 1
    wait = g.gap
    kick = 0.06
    o = eye()
    loop k in [0..g.pellets):
        d = scatter(aim(), g.spread)
        # (the nearest of what it meets: cover, the deck, or a drone)
        far = ray_world(o, d, 100)
        who = -1
        loop i in 0.. and dr in drones:
            t = ray_sphere(o, d, dr.pos, DRONE_R)
            if t >= 0.0 and t < far:
                far = t
                who = i
        stop = o + d * far
        # (the streak starts at the muzzle: ahead, right and down of the eye)
        tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
        if who >= 0:
            drones[who].health -= g.damage
            drones[who].flash = 0.1
            drones[who].vel += d * 1.5
        else if far < 100.0: sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))

step_drones = (dt: f64):
    # a wave: its drones arrive one by one at the far side, more and tougher each wave; the
    # next wave once all are down
    if to_spawn == 0 and drones.len() == 0:
        wave += 1
        to_spawn = 2 + wave * 2
        spawn_wait = 2.5
    spawn_wait -= dt
    if to_spawn > 0 and spawn_wait <= 0.0:
        drones.push(Drone(vec3(random(-HALF_X + 2.0, HALF_X - 2.0), 3, -HALF_Z + 1.0), vec3(0, 0, 0), 30.0 + wave * 5.0, random(1.0, 3.0), strafe = random_int(0, 2) * 2 - 1))
        to_spawn -= 1
        spawn_wait = 1.2
    loop mut d in drones:
        # (shot down: it bursts, and does nothing more)
        if d.health <= 0.0:
            burst(d.pos, 24)
            score += 100
            continue
        to = flat(eye() - d.pos)
        dist = length(to)
        dir = to * (1.0 / max(dist, 0.01))
        side = vec3(-dir.z, 0, dir.x)
        # keep 7 to 14 m away, circling, bobbing at 1.5 to 3 m
        want = side * d.strafe * 2.0
        if dist > 14.0: want += dir * 4.0
        if dist < 7.0: want -= dir * 4.0
        want.y = 2.2 + sin(elapsed() * 1.3 + d.strafe) * 0.7 - d.pos.y
        d.vel += (want - d.vel) * min(1.0, 2.0 * dt)
        p = collide(d.pos + d.vel * dt - vec3(0, DRONE_R, 0), DRONE_R)
        d.pos = p + vec3(0, DRONE_R, 0)
        if random() < dt * 0.3: d.strafe = -d.strafe
        d.flash -= dt
        # firing: a glowing eye for 0.6 s, then a bolt at the player's chest
        if d.windup > 0.0:
            d.windup -= dt
            if d.windup <= 0.0:
                at = eye() - vec3(0, 0.3, 0)
                bolts.push(Bolt(d.pos, scatter(normalize(at - d.pos), 0.03) * 16.0, 4.0))
                d.cool = max(0.8, random(2.0, 3.5) - wave * 0.15)
        else:
            d.cool -= dt
            if d.cool <= 0.0 and clear_line(d.pos, eye()): d.windup = 0.6
    drones = drones.filter((d): d.health > 0.0)
    # bolts: stopped by cover; the player is hit within half a meter of the body (they move
    # in steps of at most 20 cm, so a slow frame cannot carry one through a wall, or you)
    taken = 0.0
    loop mut b in bolts:
        b.life -= dt
        n = int(ceil(length(b.vel) * dt / 0.2))
        loop k in [0..n):
            b.pos += b.vel * (dt / n)
            if in_cover(b.pos) or b.pos.y <= 0.0:
                b.life = 0
                break
            q = vec3(pos.x, clamp(b.pos.y, pos.y + 0.3, eye().y), pos.z)
            if length(b.pos - q) < 0.5:
                b.life = 0
                taken += 10.0
                break
    bolts = bolts.filter((b): b.life > 0.0)
    # (after the loop: a hit that ends the run starts a new one, bolts and all)
    if taken > 0.0: hurt(taken)

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the shield comes back out of fire
    calm += dt
    if calm > RECHARGE_WAIT: shield = min(SHIELD, shield + 30.0 * dt)
    # weapons: 1 and 2 choose (Q, the next); R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    swap = -1
    if key_pressed(.n1): swap = 0
    if key_pressed(.n2): swap = 1
    if key_pressed(.q): swap = (held + 1) % guns.len()
    if swap >= 0 and swap != held:
        held = swap
        reloading = 0
        wait = 0.3
    g = guns[held]
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo[held] = g.mag
    else if key_pressed(.r) and ammo[held] < g.mag or ammo[held] == 0: reloading = g.reload
    # (the rifle fires while the button is held, the shotgun once a click)
    trigger = mouse_pressed(.left)
    if g.auto: trigger = mouse_down(.left)
    if trigger and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo[held] > 0: fire()

update = (dt: f64):
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)
    # (on the title or after a run, a click starts one)
    if screen == .play:
        step_player(dt)
        if screen == .play: step_drones(dt)
    else if mouse_pressed(.left):
        new_run()
        screen = .play
        mouse_lock()

cube = cube_mesh(1.0)
gun_meshes: Mesh[]
drone_mesh = Mesh()
eye_mesh = sphere_mesh(0.14, 12, 8)

# a drone: a ball with a band and two fins; the weapons, from boxes (their barrels along -z)
make_meshes = ():
    v: Vertex3D[]
    add_sphere(v, vec3(0, 0, 0), DRONE_R, rgb(0.8, 0.8, 0.82), 16, 10)
    add_cylinder(v, vec3(0, -0.08, 0), 0.53, 0.16, rgb(0.9, 0.45, 0.1), 20)
    add_box(v, vec3(0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    add_box(v, vec3(-0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    drone_mesh = custom_mesh(v)
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    s: Vertex3D[]
    add_box(s, vec3(0, 0.01, -0.22), vec3(0.05, 0.05, 0.42), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.045, -0.24), vec3(0.06, 0.045, 0.16), rgb(0.55, 0.32, 0.15))
    add_box(s, vec3(0, 0, 0.04), vec3(0.065, 0.09, 0.14), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.03, 0.18), vec3(0.05, 0.08, 0.16), rgb(0.55, 0.32, 0.15))
    gun_meshes = [custom_mesh(r), custom_mesh(s)]

draw_world = ():
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45))
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    # drones, facing the player, their eyes glowing; white for a moment when hit
    loop d in drones:
        to_me = normalize(flat(eye() - d.pos))
        tint = vec4(1, 1, 1, 1)
        if d.flash > 0.0: tint = vec4(2, 2, 2, 1)
        draw_mesh(drone_mesh, translation(d.pos) * facing(to_me), tint)
        glow = 0.6
        if d.windup > 0.0: glow = 0.6 + (0.6 - d.windup) * 5.0
        draw_mesh(eye_mesh, translation(d.pos + to_me * (DRONE_R - 0.06)), rgb(1, 0.15, 0.1), emissive = glow)
    loop b in bolts: draw_mesh(cube, beam(b.pos - normalize(b.vel) * 0.6, b.pos, 0.08), rgb(1.0, 0.45, 0.15), emissive = 2.0, cast_shadow = false)
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)

draw = ():
    clear(BLACK)
    if screen == .title:
        # (circling the deck)
        t = elapsed() * 0.1
        camera3d(vec3(sin(t) * 26.0, 12, cos(t) * 20.0), vec3(0, 0, 0), 60.0)
    else: camera3d(eye(), eye() + aim(), 70.0)
    draw_world()
    if screen == .title:
        text_centered("LITTLE BREAKWATER", vec2(640, 300), 64)
        text_centered("click to play", vec2(640, 380), 28, rgba(1, 1, 1, 0.7))
        text_centered("best {best}", vec2(640, 420), 22, rgba(1, 1, 1, 0.5))
        return
    # the weapon in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(gun_meshes[held], hold, cast_shadow = false, in_front = true)
    # the reticle (for the shotgun, a ring as wide as its spread), and the rounds left
    if held == 0: circle(vec2(640, 360), 3, rgba(1, 1, 1, 0.8))
    else: ring(vec2(640, 360), 50, 2, rgba(1, 1, 1, 0.8))
    text("{guns[held].name}  {ammo[held]} / {guns[held].mag}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)
    text("WAVE {wave}   {score}", vec2(40, 30), 28)
    # the shield and health; the screen reddens for a moment when hit
    rect(40, 650, 300, 10, rgba(0, 0, 0, 0.4))
    rect(40, 650, 300.0 * shield / SHIELD, 10, rgb(0.4, 0.85, 1))
    rect(40, 666, 300, 6, rgba(0, 0, 0, 0.4))
    rect(40, 666, 300.0 * health / HEALTH, 6, rgb(1, 0.4, 0.35))
    if calm < 0.25: rect(0, 0, 1280, 720, rgba(1, 0, 0, 0.25 - calm))
    if screen == .over:
        rect(0, 0, 1280, 720, rgba(0, 0, 0, 0.5))
        text_centered("{score}", vec2(640, 300), 72)
        text_centered("wave {wave}   best {best}", vec2(640, 370), 26)
        text_centered("click to play again", vec2(640, 420), 24, rgba(1, 1, 1, 0.7))

make_meshes()
window("Little Breakwater", 1280, 720)
```

A run now has a beginning and an end. `screen` says which part of the game it is (`Screen` is an
enum: a type with these three values), and `update` and `draw` do different things on each. Behind
the title, the camera circles the deck: the same world, drawn from another place.

Drones come in waves: wave n brings 2 + 2n drones, one at a time from the far side, each a little
tougher and quicker to fire than the last wave's. The next wave starts once all are down.

When your health runs out, the run is over: `mouse_lock(false)` gives the mouse back, and if the
score is a new best, `save_data("best", ...)` keeps it. `load_data` reads it back when the game
starts, as text or none: `to_int(load_data("best") ?? "0") ?? 0` is the number kept, or 0 the first
time. (In a browser it is kept in the page's storage.)

## 8. Sound, light and glow

```gdscript
# step 8: sound, light and glow
const EYE = 1.6                         # eye height (meters)
const SPEED = 6.0                       # walking speed (m/s)
const LOOK = 0.0025                     # radians turned per pixel the mouse moves
const GRAVITY = 18.0                    # m/s²
const JUMP = 6.5                        # m/s up (about 1.2 m high: onto low cover)
const RADIUS = 0.4                      # the player's, bumping into cover
const HALF_X = 20.0                     # the deck: 40 by 30 m
const HALF_Z = 15.0
const DRONE_R = 0.5                     # a drone's size (the radius shots hit)
const SHIELD = 60.0
const HEALTH = 60.0
const RECHARGE_WAIT = 3.0               # seconds out of fire before the shield comes back

# the way a yaw and pitch look (yaw 0: along -z; turning left is a bigger yaw)
look_dir = (yaw: f64, pitch: f64) -> vec3: vec3(-sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
flat = (v: vec3) -> vec3: vec3(v.x, 0, v.z)
# a random direction within `spread` radians of d
scatter = (d: vec3, spread: f64) -> vec3:
    side = cross(d, vec3(0, 1, 0))
    if length(side) < 0.01: side = vec3(1, 0, 0)     # (d is straight up or down)
    side = normalize(side)
    up = cross(side, d)
    a = random(0.0, TAU)
    r = spread * sqrt(random())
    normalize(d + side * cos(a) * r + up * sin(a) * r)
# a box stretched from a to b, w wide (a tracer, a bolt)
beam = (a: vec3, b: vec3, w: f32) -> mat4:
    d = b - a
    translation((a + b) * 0.5) * facing(d) * scaling(vec3(w, w, length(d)))

struct Box:
    lo: vec3                            # its lowest corner
    hi: vec3                            # and its highest

boxes = [Box(vec3(-9, 0, -2), vec3(-6, 1.1, -1)), Box(vec3(6, 0, 1), vec3(9, 1.1, 2)),
         Box(vec3(-8, 0, -8), vec3(-4, 2.5, -6)), Box(vec3(4, 0, 6), vec3(8, 2.5, 8)),
         Box(vec3(-15, 0, 4), vec3(-13, 2.5, 9)), Box(vec3(13, 0, -9), vec3(15, 2.5, -4)),
         Box(vec3(-1.5, 0, -0.5), vec3(1.5, 1.1, 0.5))]

# p moved out of the boxes it stands beside (not the ones it is above), and kept on the deck
collide = (p0: vec3, r: f32) -> vec3:
    p = p0
    loop b in boxes:
        if p.y >= b.hi.y - 0.05: continue
        # (the nearest point of the box's footprint)
        q = vec3(clamp(p.x, b.lo.x, b.hi.x), 0, clamp(p.z, b.lo.z, b.hi.z))
        d = vec3(p.x - q.x, 0, p.z - q.z)
        l = length(d)
        if l >= r: continue
        if l > 0.0001: p += d * ((r - l) / l)
        else:
            # (inside it: out through the nearest side)
            left = p.x - b.lo.x
            right = b.hi.x - p.x
            near = p.z - b.lo.z
            far = b.hi.z - p.z
            m = min(min(left, right), min(near, far))
            if m == left: p.x = b.lo.x - r
            else if m == right: p.x = b.hi.x + r
            else if m == near: p.z = b.lo.z - r
            else: p.z = b.hi.z + r
    p.x = clamp(p.x, -HALF_X + r, HALF_X - r)
    p.z = clamp(p.z, -HALF_Z + r, HALF_Z - r)
    p

# what is under p: the deck, or the top of a box it is over
ground_under = (p: vec3) -> f32:
    g = 0.0
    loop b in boxes:
        over = p.x >= b.lo.x and p.x <= b.hi.x and p.z >= b.lo.z and p.z <= b.hi.z
        if over and p.y >= b.hi.y - 0.3: g = max(g, b.hi.y)
    g

# how far along d (a unit vector) a ray from o goes into box b (-1: it misses)
ray_box = (o: vec3, d: vec3, b: Box) -> f32:
    t0 = 0.0
    t1 = 1000.0
    loop i in [0..3):
        if abs(d[i]) < 0.00001:
            if o[i] < b.lo[i] or o[i] > b.hi[i]: return -1
        else:
            a = (b.lo[i] - o[i]) / d[i]
            c = (b.hi[i] - o[i]) / d[i]
            t0 = max(t0, min(a, c))
            t1 = min(t1, max(a, c))
    if t0 > t1: return -1
    t0

# how far a ray goes before the deck or cover stops it (up to far)
ray_world = (o: vec3, d: vec3, far: f32) -> f32:
    t = far
    if d.y < 0.0: t = min(t, -o.y / d.y)
    loop b in boxes:
        h = ray_box(o, d, b)
        if h >= 0.0: t = min(t, h)
    t

# how far along d a ray from o goes into a sphere (-1: it misses)
ray_sphere = (o: vec3, d: vec3, c: vec3, r: f32) -> f32:
    oc = o - c
    b = dot(oc, d)
    q = dot(oc, oc) - r * r
    if q <= 0.0: return 0                               # (o is inside it)
    if b * b - q < 0.0: return -1
    t = -b - sqrt(b * b - q)
    if t < 0.0: return -1
    t

clear_line = (a: vec3, b: vec3) -> bool: ray_world(a, normalize(b - a), length(b - a)) >= length(b - a) - 0.01
# is p inside cover?
in_cover = (p: vec3) -> bool:
    loop b in boxes:
        if p.x >= b.lo.x and p.x <= b.hi.x and p.y <= b.hi.y and p.z >= b.lo.z and p.z <= b.hi.z: return true
    false

pos = vec3(0, 0, 12)                    # the player's feet
vel = vec3(0, 0, 0)
grounded = true
yaw = 0.0
pitch = 0.0
shield = SHIELD
health = HEALTH
calm = 0.0                              # seconds since a hit

eye = () -> vec3: pos + vec3(0, EYE, 0)
aim = () -> vec3: look_dir(yaw, pitch)

# the weapons: what each does
struct Gun:
    name: str
    mag: int                            # rounds in a magazine
    gap: f64                            # seconds between shots
    auto: bool                          # fires while the button is held
    pellets: int                        # rays a shot (a shotgun's are many)
    spread: f64                         # how far they stray (radians)
    damage: f64                         # a pellet's
    reload: f64                         # seconds

guns = [Gun("RIFLE", 30, 0.1, true, 1, 0.012, 12, 1.5), Gun("SHOTGUN", 6, 0.7, false, 14, 0.1, 9, 2.0)]
held = 0                                # the one in hand
ammo = [loop g in guns: g.mag]          # each one's rounds
wait = 0.0                              # until the next shot
reloading = 0.0                         # seconds left
kick = 0.0                              # the weapon's recoil, easing back

# a shot's streak, for a moment; and sparks where shots land
struct Tracer:
    a: vec3
    b: vec3
    life: f64

struct Spark:
    pos: vec3
    vel: vec3
    life: f64

struct Drone:
    pos: vec3                           # (its middle)
    vel: vec3
    health: f64
    cool: f64                           # seconds until it fires
    windup: f64 = 0.0                   # about to fire (its eye glows)
    strafe: f32 = 1                     # which way it circles the player
    flash: f64 = 0.0                    # just hit

struct Bolt:
    pos: vec3
    vel: vec3
    life: f64

tracers: Tracer[]
sparks: Spark[]
drones: Drone[]
bolts: Bolt[]

# a run: waves of drones, between a title and its end
enum Screen: title, play, over
screen = Screen.title
wave = 0
to_spawn = 0                            # drones still to come this wave
spawn_wait = 0.0
score = 0
best = to_int(load_data("best") ?? "0") ?? 0
hit_mark = 0.0                          # (the reticle turns red on a hit)

# sounds, made by the synthesizer
snd_rifle = mix([tone(160.0, 0.1, .noise, 0.5, 0.001, 0.09, 0.4), tone(95.0, 0.08, .square, 0.2, 0.001, 0.07, 0.6)])
snd_shotgun = mix([tone(110.0, 0.4, .noise, 0.8, 0.001, 0.35, 0.35), tone(55.0, 0.3, .square, 0.3, 0.001, 0.25, 0.5)])
snd_reload = tone(500.0, 0.08, .square, 0.15, 0.001, 0.06)
snd_bolt = mix([tone(700.0, 0.2, .square, 0.12, 0.002, 0.17, 0.45), tone(300.0, 0.15, .sine, 0.2, 0.002, 0.12, 0.5)])
snd_hit = tone(1300.0, 0.05, .square, 0.1, 0.001, 0.04)
snd_boom = mix([tone(90.0, 0.5, .noise, 0.6, 0.002, 0.45, 0.4), tone(60.0, 0.4, .sine, 0.4, 0.002, 0.35, 0.5)])
snd_hurt = tone(200.0, 0.2, .saw, 0.3, 0.002, 0.18, 0.6)

new_run = ():
    pos = vec3(0, 0, 12)
    vel = vec3(0, 0, 0)
    yaw = 0
    pitch = 0
    shield = SHIELD
    health = HEALTH
    ammo = [loop g in guns: g.mag]
    held = 0
    reloading = 0
    drones = []
    bolts = []
    wave = 0
    to_spawn = 0
    score = 0

# the shield takes hits first; then health; with none left, the run is over
hurt = (dmg: f64):
    calm = 0
    play(snd_hurt, 0.5)
    left = dmg - shield
    shield = max(0.0, shield - dmg)
    if left > 0.0: health -= left
    if health <= 0.0:
        screen = .over
        mouse_lock(false)
        if score > best:
            best = score
            save_data("best", "{best}")

burst = (at: vec3, n: int):
    loop i in [0..n): sparks.push(Spark(at, scatter(vec3(0, 1, 0), 2.0) * random(3.0, 9.0), random(0.3, 0.7)))

fire = ():
    g = guns[held]
    ammo[held] -= 1
    wait = g.gap
    kick = 0.06
    o = eye()
    struck = false
    loop k in [0..g.pellets):
        d = scatter(aim(), g.spread)
        # (the nearest of what it meets: cover, the deck, or a drone)
        far = ray_world(o, d, 100)
        who = -1
        loop i in 0.. and dr in drones:
            t = ray_sphere(o, d, dr.pos, DRONE_R)
            if t >= 0.0 and t < far:
                far = t
                who = i
        stop = o + d * far
        # (the streak starts at the muzzle: ahead, right and down of the eye)
        tracers.push(Tracer(o + aim() * 0.8 + look_dir(yaw - PI / 2.0, 0.0) * 0.2 - vec3(0, 0.2, 0), stop, 0.05))
        if who >= 0:
            drones[who].health -= g.damage
            drones[who].flash = 0.1
            drones[who].vel += d * 1.5
            struck = true
        else if far < 100.0: sparks.push(Spark(stop, scatter(vec3(0, 1, 0), 1.0) * 3.0, 0.3))
    if struck:
        hit_mark = 0.15
        play(snd_hit, 0.4)
    if held == 0: play(snd_rifle, 0.5, pitch = random(0.95, 1.05))
    else: play(snd_shotgun, 0.7)

step_drones = (dt: f64):
    # a wave: its drones arrive one by one at the far side, more and tougher each wave; the
    # next wave once all are down
    if to_spawn == 0 and drones.len() == 0:
        wave += 1
        to_spawn = 2 + wave * 2
        spawn_wait = 2.5
    spawn_wait -= dt
    if to_spawn > 0 and spawn_wait <= 0.0:
        drones.push(Drone(vec3(random(-HALF_X + 2.0, HALF_X - 2.0), 3, -HALF_Z + 1.0), vec3(0, 0, 0), 30.0 + wave * 5.0, random(1.0, 3.0), strafe = random_int(0, 2) * 2 - 1))
        to_spawn -= 1
        spawn_wait = 1.2
    loop mut d in drones:
        # (shot down: it bursts, and does nothing more)
        if d.health <= 0.0:
            burst(d.pos, 24)
            play(snd_boom, 0.6)
            score += 100
            continue
        to = flat(eye() - d.pos)
        dist = length(to)
        dir = to * (1.0 / max(dist, 0.01))
        side = vec3(-dir.z, 0, dir.x)
        # keep 7 to 14 m away, circling, bobbing at 1.5 to 3 m
        want = side * d.strafe * 2.0
        if dist > 14.0: want += dir * 4.0
        if dist < 7.0: want -= dir * 4.0
        want.y = 2.2 + sin(elapsed() * 1.3 + d.strafe) * 0.7 - d.pos.y
        d.vel += (want - d.vel) * min(1.0, 2.0 * dt)
        p = collide(d.pos + d.vel * dt - vec3(0, DRONE_R, 0), DRONE_R)
        d.pos = p + vec3(0, DRONE_R, 0)
        if random() < dt * 0.3: d.strafe = -d.strafe
        d.flash -= dt
        # firing: a glowing eye for 0.6 s, then a bolt at the player's chest
        if d.windup > 0.0:
            d.windup -= dt
            if d.windup <= 0.0:
                at = eye() - vec3(0, 0.3, 0)
                bolts.push(Bolt(d.pos, scatter(normalize(at - d.pos), 0.03) * 16.0, 4.0))
                play(snd_bolt, 0.3)
                d.cool = max(0.8, random(2.0, 3.5) - wave * 0.15)
        else:
            d.cool -= dt
            if d.cool <= 0.0 and clear_line(d.pos, eye()): d.windup = 0.6
    drones = drones.filter((d): d.health > 0.0)
    # bolts: stopped by cover; the player is hit within half a meter of the body (they move
    # in steps of at most 20 cm, so a slow frame cannot carry one through a wall, or you)
    taken = 0.0
    loop mut b in bolts:
        b.life -= dt
        n = int(ceil(length(b.vel) * dt / 0.2))
        loop k in [0..n):
            b.pos += b.vel * (dt / n)
            if in_cover(b.pos) or b.pos.y <= 0.0:
                b.life = 0
                break
            q = vec3(pos.x, clamp(b.pos.y, pos.y + 0.3, eye().y), pos.z)
            if length(b.pos - q) < 0.5:
                b.life = 0
                taken += 10.0
                break
    bolts = bolts.filter((b): b.life > 0.0)
    # (after the loop: a hit that ends the run starts a new one, bolts and all)
    if taken > 0.0: hurt(taken)

step_player = (dt: f64):
    # a click hands the mouse to the game: then moving it turns the view
    if mouse_pressed(.left) and not is_mouse_locked(): mouse_lock()
    if is_mouse_locked():
        m = mouse_delta()
        yaw -= m.x * LOOK
        pitch = clamp(pitch - m.y * LOOK, -1.4, 1.4)
    # walking: the keys, turned the way the player faces
    ahead = look_dir(yaw, 0.0)
    right = look_dir(yaw - PI / 2.0, 0.0)
    move = input_axis()
    wish = right * move.x - ahead * move.y
    vel.x = wish.x * SPEED
    vel.z = wish.z * SPEED
    # falling (half the frame's gravity before the move, half after), and jumping from the ground
    if grounded and key_pressed(.space): vel.y = JUMP
    vel.y -= GRAVITY * dt / 2.0
    pos.y += vel.y * dt
    vel.y -= GRAVITY * dt / 2.0
    floor_y = ground_under(pos)
    grounded = pos.y <= floor_y
    if grounded:
        pos.y = floor_y
        vel.y = 0
    # then across, round the cover
    pos = collide(pos + vec3(vel.x, 0, vel.z) * dt, RADIUS)
    # the shield comes back out of fire
    calm += dt
    if calm > RECHARGE_WAIT: shield = min(SHIELD, shield + 30.0 * dt)
    # weapons: 1 and 2 choose (Q, the next); R reloads (and so does an empty magazine)
    wait -= dt
    kick = max(0.0, kick - dt * 0.4)
    hit_mark -= dt
    swap = -1
    if key_pressed(.n1): swap = 0
    if key_pressed(.n2): swap = 1
    if key_pressed(.q): swap = (held + 1) % guns.len()
    if swap >= 0 and swap != held:
        held = swap
        reloading = 0
        wait = 0.3
    g = guns[held]
    if reloading > 0.0:
        reloading -= dt
        if reloading <= 0.0: ammo[held] = g.mag
    else if key_pressed(.r) and ammo[held] < g.mag or ammo[held] == 0:
        reloading = g.reload
        play(snd_reload, 0.4)
    # (the rifle fires while the button is held, the shotgun once a click)
    trigger = mouse_pressed(.left)
    if g.auto: trigger = mouse_down(.left)
    if trigger and is_mouse_locked() and wait <= 0.0 and reloading <= 0.0 and ammo[held] > 0: fire()

update = (dt: f64):
    loop mut t in tracers: t.life -= dt
    tracers = tracers.filter((t): t.life > 0.0)
    loop mut s in sparks:
        s.vel.y -= GRAVITY * dt
        s.pos += s.vel * dt
        s.life -= dt
    sparks = sparks.filter((s): s.life > 0.0)
    # (on the title or after a run, a click starts one)
    if screen == .play:
        step_player(dt)
        if screen == .play: step_drones(dt)
    else if mouse_pressed(.left):
        new_run()
        screen = .play
        mouse_lock()

cube = cube_mesh(1.0)
gun_meshes: Mesh[]
drone_mesh = Mesh()
eye_mesh = sphere_mesh(0.14, 12, 8)

# a drone: a ball with a band and two fins; the weapons, from boxes (their barrels along -z)
make_meshes = ():
    v: Vertex3D[]
    add_sphere(v, vec3(0, 0, 0), DRONE_R, rgb(0.8, 0.8, 0.82), 16, 10)
    add_cylinder(v, vec3(0, -0.08, 0), 0.53, 0.16, rgb(0.9, 0.45, 0.1), 20)
    add_box(v, vec3(0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    add_box(v, vec3(-0.6, 0, 0.1), vec3(0.25, 0.08, 0.5), rgb(0.25, 0.27, 0.3))
    drone_mesh = custom_mesh(v)
    r: Vertex3D[]
    add_box(r, vec3(0, 0, 0), vec3(0.07, 0.09, 0.3), rgb(0.85, 0.85, 0.82))
    add_box(r, vec3(0, 0.01, -0.28), vec3(0.03, 0.03, 0.28), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.1, -0.06), vec3(0.04, 0.13, 0.07), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, -0.02, 0.22), vec3(0.05, 0.08, 0.16), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0, 0.06, -0.02), vec3(0.02, 0.03, 0.14), rgb(0.15, 0.15, 0.17))
    add_box(r, vec3(0.036, 0.0, -0.04), vec3(0.005, 0.02, 0.2), rgb(1.0, 0.5, 0.1))
    s: Vertex3D[]
    add_box(s, vec3(0, 0.01, -0.22), vec3(0.05, 0.05, 0.42), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.045, -0.24), vec3(0.06, 0.045, 0.16), rgb(0.55, 0.32, 0.15))
    add_box(s, vec3(0, 0, 0.04), vec3(0.065, 0.09, 0.14), rgb(0.3, 0.32, 0.36))
    add_box(s, vec3(0, -0.03, 0.18), vec3(0.05, 0.08, 0.16), rgb(0.55, 0.32, 0.15))
    gun_meshes = [custom_mesh(r), custom_mesh(s)]

draw_world = ():
    sky(vec3(0.16, 0.42, 0.82), vec3(0.72, 0.86, 0.95), vec3(0.5, 0.48, 0.44))
    sun(vec3(0.6, 0.45, 0.4), vec3(1.25, 1.05, 0.82))
    fog(vec3(0.72, 0.84, 0.92), 0.004, 0.02)
    shadows(true, 0.6, 30.0)
    post_effects(0.5, 0.75, 0.3)
    # the sea, the deck, its rails, the cover on it
    draw_mesh(cube, translation(vec3(0, -3, 0)) * scaling(vec3(400, 1, 400)), rgb(0.1, 0.3, 0.45), cast_shadow = false)
    draw_mesh(cube, translation(vec3(0, -1.5, 0)) * scaling(vec3(HALF_X * 2.0, 3, HALF_Z * 2.0)), rgb(0.33, 0.38, 0.46))
    loop s in [-1.0, 1.0]:
        draw_mesh(cube, translation(vec3(0, 0.5, s * HALF_Z)) * scaling(vec3(HALF_X * 2.0, 0.08, 0.08)), rgb(0.2, 0.25, 0.3))
        draw_mesh(cube, translation(vec3(s * HALF_X, 0.5, 0)) * scaling(vec3(0.08, 0.08, HALF_Z * 2.0)), rgb(0.2, 0.25, 0.3))
    loop b in boxes: draw_mesh(cube, translation((b.lo + b.hi) * 0.5) * scaling(b.hi - b.lo), rgb(0.85, 0.82, 0.75))
    # drones, facing the player, their eyes glowing (lighting what is near as they wind up);
    # white for a moment when hit
    loop d in drones:
        to_me = normalize(flat(eye() - d.pos))
        tint = vec4(1, 1, 1, 1)
        if d.flash > 0.0: tint = vec4(2, 2, 2, 1)
        draw_mesh(drone_mesh, translation(d.pos) * facing(to_me), tint)
        glow = 0.6
        if d.windup > 0.0: glow = 0.6 + (0.6 - d.windup) * 5.0
        e = d.pos + to_me * (DRONE_R - 0.06)
        draw_mesh(eye_mesh, translation(e), rgb(1, 0.15, 0.1), emissive = glow)
        if d.windup > 0.0: point_light(e, vec3(1, 0.3, 0.2), 3.0, glow * 0.5)
    loop b in bolts:
        draw_mesh(cube, beam(b.pos - normalize(b.vel) * 0.6, b.pos, 0.08), rgb(1.0, 0.45, 0.15), emissive = 2.0, cast_shadow = false)
        point_light(b.pos, vec3(1, 0.4, 0.15), 3.0)
    loop t in tracers: draw_mesh(cube, beam(t.a, t.b, 0.015), rgb(1.0, 0.9, 0.6), emissive = 2.0, cast_shadow = false)
    loop s in sparks: draw_mesh(cube, translation(s.pos) * scaling(vec3(0.07, 0.07, 0.07)), rgb(1.0, 0.7, 0.3), emissive = 2.0, cast_shadow = false)

draw = ():
    clear(BLACK)
    if screen == .title:
        # (circling the deck)
        t = elapsed() * 0.1
        camera3d(vec3(sin(t) * 26.0, 12, cos(t) * 20.0), vec3(0, 0, 0), 60.0)
    else: camera3d(eye(), eye() + aim(), 70.0)
    draw_world()
    if screen == .title:
        text_centered("LITTLE BREAKWATER", vec2(640, 300), 64)
        text_centered("click to play", vec2(640, 380), 28, rgba(1, 1, 1, 0.7))
        text_centered("best {best}", vec2(640, 420), 22, rgba(1, 1, 1, 0.5))
        return
    # the weapon in hand, in front of everything (kicked back by each shot, lowered to reload)
    view = inverse(look_at(eye(), eye() + aim(), vec3(0, 1, 0)))
    dip = 0.0
    if reloading > 0.0: dip = 0.15
    hold = view * translation(vec3(0.2, -0.19 - dip, -0.5 + kick)) * rotation_y(0.05) * rotation_x(kick * 3.0)
    draw_mesh(gun_meshes[held], hold, cast_shadow = false, in_front = true)
    # (a flash at the muzzle as it fires)
    if wait > guns[held].gap - 0.04: point_light(transform_point(hold, vec3(0, 0, -0.5)), vec3(1, 0.8, 0.5), 4.0, 1.5)
    # the reticle (for the shotgun, a ring as wide as its spread; red on a hit), the rounds left
    rc = rgba(1, 1, 1, 0.8)
    if hit_mark > 0.0: rc = rgb(1, 0.4, 0.3)
    if held == 0: circle(vec2(640, 360), 3, rc)
    else: ring(vec2(640, 360), 50, 2, rc)
    text("{guns[held].name}  {ammo[held]} / {guns[held].mag}", vec2(1000, 30), 28)
    if reloading > 0.0: text_centered("RELOADING", vec2(640, 420), 20)
    text("WAVE {wave}   {score}", vec2(40, 30), 28)
    # the shield and health; the screen reddens for a moment when hit
    rect(40, 650, 300, 10, rgba(0, 0, 0, 0.4))
    rect(40, 650, 300.0 * shield / SHIELD, 10, rgb(0.4, 0.85, 1))
    rect(40, 666, 300, 6, rgba(0, 0, 0, 0.4))
    rect(40, 666, 300.0 * health / HEALTH, 6, rgb(1, 0.4, 0.35))
    if calm < 0.25: rect(0, 0, 1280, 720, rgba(1, 0, 0, 0.25 - calm))
    if screen == .over:
        rect(0, 0, 1280, 720, rgba(0, 0, 0, 0.5))
        text_centered("{score}", vec2(640, 300), 72)
        text_centered("wave {wave}   best {best}", vec2(640, 370), 26)
        text_centered("click to play again", vec2(640, 420), 24, rgba(1, 1, 1, 0.7))

make_meshes()
play(melody_loop("A2 . E3 . A2 . G2 . F2 . C3 . G2 . E2 .", 110.0, .triangle, 0.12), looping = true)
window("Little Breakwater", 1280, 720)
```

Every sound is made by the program: `tone` is a note of one waveform (noise for gunshots, square
for clicks, sine for a hum), with an attack and a release, and `mix` plays several at once. The
music is `melody_loop`: note names played over and over without a seam.

`point_light` lights what is near it for one frame: bolts light the deck they fly over, a drone's
eye lights up as it winds up, and the weapon flashes as it fires. `post_effects` adds bloom, so
what is bright (the emissive tracers, sparks and eyes) glows past its edges. `shadows` turns on the
sun's shadows, and `fog` fades what is far into the horizon.

## 9. From here to Breakwater

[Breakwater](../examples/breakwater/breakwater.jo) is this game, grown. It has:

- **Models made in other programs**: its robots and weapons are glTF models (`load_model`), the
  robots animated: `pose_at(model, find_animation(model, "Walk"), time)` is how they stand at a
  moment of their walk, `blend_poses` fades from standing to walking to running, `turn_node` turns
  a robot's gun toward you, and `node_transform` says where a hand is, to put a weapon in it.
- **Robots that find their way** round the cover, over a grid of where they can walk
  (lib/game/paths.jo: `path_grid`, `path_step`), with cover to hide behind, and ramps.
- **Three kinds of robot** (skitters that rush, shielded wardens, lobbers that arc shells over
  cover), five weapons on racks and in the robots' hands, grenades and melee.
- **Controls the player can change** (`action`, and a Controls screen from `ui_controls()`),
  keyboard-only play, and gamepads.
- An autopilot that plays it, which is how its difficulty was tested.

The collision and rays here are written by hand, so you can see how they work. A bigger game can
use `import physics3d`: rigid bodies, `w.raycast` for shots, and `w.character(...)` and
`w.walk(...)` for a walking capsule.

Play it at [sloppy-lang.org/breakwater](https://sloppy-lang.org/breakwater/), or change it in
[the playground](https://sloppy-lang.org/playground/#example=breakwater). To share your own game,
`sloppy build game.jo --target wasm` makes one web page, and `--target windows` a Windows program:
see [sharing](TUTORIAL.md#9-sharing-it) in the first tutorial.
