#!/usr/bin/env python3
"""Tiny original glTF fixtures for PBR. Generated data is dedicated to CC0/public domain.
Run from any directory; no network, external assets or Python dependencies.
"""
import base64
import copy
import json
import math
from pathlib import Path
import struct
import zlib

OUT = Path(__file__).resolve().parent

def uri(data, mime):
    return f'data:{mime};base64,' + base64.b64encode(data).decode()

def png(w, h, pixel):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    data = b''.join(b'\0' + bytes(c for x in range(w) for c in pixel(x, y)) for y in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(data)) + chunk(b'IEND', b'')

buf = bytearray()
views, accessors = [], []
def accessor(values, n, kind=5126):
    while len(buf) % 4: buf.append(0)
    raw = struct.pack('<' + ('f' if kind == 5126 else 'H') * len(values), *values)
    views.append(dict(buffer=0, byteOffset=len(buf), byteLength=len(raw)))
    buf.extend(raw)
    accessors.append(dict(bufferView=len(views)-1, componentType=kind, count=len(values)//n, type={1:'SCALAR', 2:'VEC2', 3:'VEC3', 4:'VEC4'}[n]))
    return len(accessors)-1

attrs = dict(POSITION=accessor([-1,-1,0, 1,-1,0, 1,1,0, -1,1,0], 3),
             NORMAL=accessor([0,0,1]*4, 3),
             TEXCOORD_0=accessor([0,1, 1,1, 1,0, 0,0], 2),
             TEXCOORD_1=accessor([0,2, 2,2, 2,0, 0,0], 2))
accessors[attrs['POSITION']].update(min=[-1,-1,0], max=[1,1,0])
indices = accessor([0,1,2, 0,2,3], 1, 5123)
# Deliberate -Y tangent basis: glTF image rows go from top to bottom.
tangent = accessor([1,0,0,-1]*4, 4)
def normal(x, y):
    nx = 0.48 * math.sin(2*math.pi*x/16)
    ny = 0.48 * math.sin(2*math.pi*y/16)
    nz = math.sqrt(1-nx*nx-ny*ny)
    return tuple(round(127.5*(v+1)) for v in (nx,ny,nz)) + (255,)
images = [png(16,16,normal),
          png(8,8,lambda x,y: (170,215,110,255 if (x//2+y//2)%2 == 0 else 0)),
          png(8,8,lambda x,y: (255,32+x*28,y*36,255)),
          png(8,8,lambda x,y: (70+x*22,70+x*22,70+x*22,255)),
          png(8,8,lambda x,y: (25,60,200,255))]
materials = [dict(pbrMetallicRoughness=dict(baseColorFactor=[0.55,0.34,0.12,1],metallicFactor=0.35,roughnessFactor=0.42), normalTexture=dict(index=0,scale=0.7)),
             dict(pbrMetallicRoughness=dict(baseColorTexture=dict(index=1),metallicFactor=0,roughnessFactor=0.9),alphaMode='MASK',alphaCutoff=0.6,doubleSided=True),
             dict(pbrMetallicRoughness=dict(baseColorFactor=[0.7,0.5,0.2,1],metallicRoughnessTexture=dict(index=2)),normalTexture=dict(index=0,scale=0.5,texCoord=1),occlusionTexture=dict(index=3,strength=0.7),emissiveTexture=dict(index=4),emissiveFactor=[0.1,0.3,0.8]),
             dict(pbrMetallicRoughness=dict(baseColorFactor=[0.1,0.4,0.8,0.45],metallicFactor=0,roughnessFactor=0.5),alphaMode='BLEND',doubleSided=True)]
meshes = [dict(primitives=[dict(attributes=dict(attrs, **({'TANGENT':tangent} if i==2 else {})),indices=indices,material=i)]) for i in range(4)]
joints = accessor([0,0,0,0]*4, 4, 5123)
weights = accessor([1,0,0,0]*4, 4)
times = accessor([0,1], 1)
accessors[times].update(min=[0], max=[1])
rotations = accessor([0,0,0,1, 0,math.sin(math.pi/6),0,math.cos(math.pi/6)], 4)
# Two morphs: tilt/stretch upward, and widen. Explicit tangent deltas leave W untouched.
base_positions = [-1,-1,0, 1,-1,0, 1,1,0, -1,1,0]
delta1 = []
for x,y,z in zip(base_positions[0::3], base_positions[1::3], base_positions[2::3]):
    delta1.extend([0, (1.2*math.cos(math.pi/6)-1)*y + 0.5, 1.2*math.sin(math.pi/6)*y])
delta2 = [v for x in base_positions[0::3] for v in [0.35*x,0,0]]
def position_delta(values):
    values = [struct.unpack('<f',struct.pack('<f',v))[0] for v in values]
    a = accessor(values,3)
    accessors[a].update(min=[min(values[k::3]) for k in range(3)], max=[max(values[k::3]) for k in range(3)])
    return a
mp1 = position_delta(delta1)
mp2 = position_delta(delta2)
mn = accessor([0,-math.sin(math.pi/6),math.cos(math.pi/6)-1]*4,3)
mt = accessor([0,0,0]*4,3)
mw = accessor([0,0, 1,0.5],1)
mc = accessor([0,0, 0,0, 2,0, 0,0, 1,0.5, 0,0],1)
ctimes = accessor([0,2],1)
accessors[ctimes].update(min=[0],max=[2])
morph_rotations = accessor([0,0,0,1, 0,math.sin(math.pi/9),0,math.cos(math.pi/9)],4)
def raw_view(raw):
    while len(buf)%4: buf.append(0)
    view=len(views)
    views.append(dict(buffer=0,byteOffset=len(buf),byteLength=len(raw)))
    buf.extend(raw)
    return view
sparse_indices = raw_view(bytes([2,3]))
sparse_values = raw_view(struct.pack('<6f',*delta1[6:]))
mp_sparse = len(accessors)
accessors.append(dict(componentType=5126,count=4,type='VEC3',min=[0,0,0],max=[0,delta1[7],delta1[8]],sparse=dict(count=2,indices=dict(bufferView=sparse_indices,componentType=5121),values=dict(bufferView=sparse_values))))
doc = dict(asset=dict(version='2.0',copyright='CC0: original procedural test data'),
           scene=0,scenes=[dict(nodes=[0])],nodes=[dict(mesh=0)],meshes=meshes,materials=materials,
           buffers=[dict(byteLength=len(buf),uri=uri(buf,'application/octet-stream'))],bufferViews=views,accessors=accessors,
           textures=[dict(source=i,sampler=0) for i in range(len(images))],samplers=[dict(magFilter=9729)],
           images=[dict(uri=uri(im,'image/png')) for im in images])
(OUT/'pbr_materials.gltf').write_text(json.dumps(doc,separators=(',',':'))+'\n')

skin = copy.deepcopy(doc)
skin['nodes'] = [dict(mesh=0, skin=0), dict(name='Turn')]
skin['scenes'] = [dict(nodes=[0,1])]
skin['skins'] = [dict(joints=[1])]
skin['meshes'] = [dict(primitives=[dict(attributes=dict(attrs, TANGENT=tangent, JOINTS_0=joints, WEIGHTS_0=weights), indices=indices, material=0)])]
skin['animations'] = [dict(name='Turn',samplers=[dict(input=times, output=rotations)],channels=[dict(sampler=0,target=dict(node=1,path='rotation'))])]
(OUT/'pbr_skin.gltf').write_text(json.dumps(skin,separators=(',',':'))+'\n')

morph = copy.deepcopy(doc)
morph['nodes'] = [dict(name='Morph',mesh=0)]
morph['meshes'] = [dict(weights=[0.25,0],primitives=[dict(attributes=dict(attrs,TANGENT=tangent),indices=indices,material=0,targets=[dict(POSITION=mp1,NORMAL=mn,TANGENT=mt),dict(POSITION=mp2)])])]
morph['animations'] = [dict(name=name,samplers=[dict(input=times,output=output,interpolation=how)],channels=[dict(sampler=0,target=dict(node=0,path='weights'))]) for name,output,how in [('Morph',mw,'LINEAR'),('Step',mw,'STEP'),('Cubic',mc,'CUBICSPLINE')]]
morph['animations'].append(dict(name='CubicSlow',samplers=[dict(input=ctimes,output=mc,interpolation='CUBICSPLINE')],channels=[dict(sampler=0,target=dict(node=0,path='weights'))]))
(OUT/'pbr_morph.gltf').write_text(json.dumps(morph,separators=(',',':'))+'\n')
flat = copy.deepcopy(morph)
flat['meshes'][0]['primitives'][0]['attributes'].pop('NORMAL')
flat['meshes'][0]['primitives'][0]['attributes'].pop('TANGENT')
flat['meshes'][0]['primitives'][0]['targets'][0] = dict(POSITION=mp1)
(OUT/'pbr_morph_flat.gltf').write_text(json.dumps(flat,separators=(',',':'))+'\n')
ms = copy.deepcopy(morph)
ms['nodes'] = [dict(name='Morph',mesh=0,skin=0),dict(name='Turn')]
ms['scenes'] = [dict(nodes=[0,1])]
ms['skins'] = [dict(joints=[1])]
ms['meshes'][0]['primitives'][0]['attributes'].update(JOINTS_0=joints,WEIGHTS_0=weights)
ms['animations'][0]['samplers'].append(dict(input=times,output=morph_rotations))
ms['animations'][0]['channels'].append(dict(sampler=1,target=dict(node=1,path='rotation')))
(OUT/'pbr_morph_skin.gltf').write_text(json.dumps(ms,separators=(',',':'))+'\n')

sparse = copy.deepcopy(flat)
sparse['meshes'][0]['primitives'][0]['targets'][0] = dict(POSITION=mp_sparse)
(OUT/'pbr_morph_sparse.gltf').write_text(json.dumps(sparse,separators=(',',':'))+'\n')
