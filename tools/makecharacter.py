#!/usr/bin/env python3
"""Rebuild lib/new/character.glb: a CC0 skinned block character, no external assets.
The mesh faces +Z, is 1.9 meters tall, and has Idle, Walk and Run animation clips.
All generated geometry, rigging and animation are dedicated to the public domain (CC0).
"""
import json
import math
from pathlib import Path
import struct

blob = bytearray()
views, accessors = [], []


def accessor(values, width, kind='f', bounds=False):
    while len(blob) % 4:
        blob.append(0)
    start = len(blob)
    flat = [x for row in values for x in row]
    blob.extend(struct.pack('<' + kind * len(flat), *flat))
    views.append(dict(buffer=0, byteOffset=start, byteLength=len(blob) - start))
    a = dict(bufferView=len(views) - 1, componentType={'f': 5126, 'H': 5123}[kind],
             count=len(values), type={1: 'SCALAR', 3: 'VEC3', 4: 'VEC4', 16: 'MAT4'}[width])
    if bounds:
        a.update(min=[min(row[k] for row in values) for k in range(width)],
                 max=[max(row[k] for row in values) for k in range(width)])
    accessors.append(a)
    return len(accessors) - 1


positions, normals, colors, joints, weights, indices = [], [], [], [], [], []


def box(center, size, joint, color):
    # Four vertices per face keep the edges flat; all vertices are skinned.
    for axis, sign, u, v in [(0, 1, 1, 2), (0, -1, 2, 1), (1, 1, 2, 0),
                             (1, -1, 0, 2), (2, 1, 0, 1), (2, -1, 1, 0)]:
        first = len(positions)
        for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            p = list(center)
            p[axis] += sign * size[axis] / 2
            p[u] += a * size[u] / 2
            p[v] += b * size[v] / 2
            n = [0, 0, 0]
            n[axis] = sign
            positions.append(p)
            normals.append(n)
            colors.append(color)
            joints.append([joint, 0, 0, 0])
            weights.append([1, 0, 0, 0])
        indices.extend([[first + i] for i in [0, 1, 2, 0, 2, 3]])


shirt = [0.72, 0.2, 0.07, 1]
skin = [0.78, 0.52, 0.36, 1]
blue = [0.06, 0.2, 0.42, 1]
dark = [0.035, 0.03, 0.03, 1]
# Root, torso, head, left/right shoulders, left/right hips.
bind = [[0, 0, 0], [0, 1.1, 0], [0, 1.63, 0], [-0.4, 1.43, 0],
        [0.4, 1.43, 0], [-0.18, 0.85, 0], [0.18, 0.85, 0]]
box([0, 1.19, 0], [0.62, 0.63, 0.34], 1, shirt)
box([0, 1.69, 0], [0.43, 0.42, 0.4], 2, skin)
for x in [-0.11, 0.11]:
    box([x, 1.73, 0.205], [0.07, 0.065, 0.025], 2, dark)
for x, arm, leg in [(-1, 3, 5), (1, 4, 6)]:
    box([x * 0.43, 1.17, 0], [0.2, 0.57, 0.23], arm, skin)
    box([x * 0.18, 0.48, 0], [0.24, 0.73, 0.27], leg, blue)
    box([x * 0.18, 0.09, 0.07], [0.27, 0.18, 0.42], leg, dark)
attrs = {'POSITION': accessor(positions, 3, bounds=True), 'NORMAL': accessor(normals, 3),
         'COLOR_0': accessor(colors, 4), 'JOINTS_0': accessor(joints, 4, 'H'),
         'WEIGHTS_0': accessor(weights, 4)}
idx = accessor(indices, 1, 'H')
matrices = []
for x, y, z in bind:
    matrices.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
ibm = accessor(matrices, 16)
names = ['Root', 'Torso', 'Head', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg']
nodes = [dict(name=n, translation=t) for n, t in zip(names, bind)]
nodes[0]['children'] = list(range(1, 7))
nodes.append(dict(name='Character', mesh=0, skin=0))
animations = []
for name, duration, swing, bounce in [('Idle', 2.4, 0.04, 0.025), ('Walk', 1.0, 0.5, 0.035),
                                       ('Run', 0.6, 0.95, 0.08)]:
    times = accessor([[duration * i / 8] for i in range(9)], 1, bounds=True)
    samplers, channels = [], []

    def channel(node, path, values, width):
        samplers.append(dict(input=times, output=accessor(values, width), interpolation='LINEAR'))
        channels.append(dict(sampler=len(samplers) - 1, target=dict(node=node, path=path)))

    channel(0, 'translation', [[0, bounce * (1 - math.cos(i * math.pi / 2)), 0]
                                for i in range(9)], 3)
    for node, direction in [(3, 1), (4, -1), (5, -1), (6, 1)]:
        angles = [direction * swing * math.sin(i * math.pi / 4) for i in range(9)]
        channel(node, 'rotation', [[math.sin(a / 2), 0, 0, math.cos(a / 2)] for a in angles], 4)
    animations.append(dict(name=name, samplers=samplers, channels=channels))
while len(blob) % 4:
    blob.append(0)
gltf = dict(asset=dict(version='2.0', generator='Sloppy procedural character (CC0-1.0)',
                       copyright='Dedicated to the public domain under CC0-1.0'),
            scene=0, scenes=[dict(nodes=[0, 7])], nodes=nodes,
            meshes=[dict(primitives=[dict(attributes=attrs, indices=idx, material=0)])],
            materials=[dict(pbrMetallicRoughness=dict(metallicFactor=0.1, roughnessFactor=0.65))],
            skins=[dict(joints=list(range(7)), inverseBindMatrices=ibm, skeleton=0)],
            animations=animations, buffers=[dict(byteLength=len(blob))],
            bufferViews=views, accessors=accessors)
encoded = json.dumps(gltf, separators=(',', ':')).encode()
encoded += b' ' * (-len(encoded) % 4)
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(encoded) + 8 + len(blob))
out += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
out += struct.pack('<II', len(blob), 0x004E4942) + blob
path = Path(__file__).resolve().parent.parent / 'lib/new/character.glb'
path.write_bytes(out)
print(f'{path.name}: {len(out)} bytes')
