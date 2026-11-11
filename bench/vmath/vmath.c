// Equivalent f32 kernels. Compile with cc -O2 -ffp-contract=off ... -lm.
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { N = 1024, R = 256 };
typedef struct {
  float x, y, z, w;
} V4;
typedef struct {
  float x, y, z;
} V3;
typedef struct {
  V4 c[4];
} M4;
#define NI __attribute__((noinline, noipa))
static V4 add4(V4 a, V4 b) {
  return (V4){a.x + b.x, a.y + b.y, a.z + b.z, a.w + b.w};
}
static V4 sub4(V4 a, V4 b) {
  return (V4){a.x - b.x, a.y - b.y, a.z - b.z, a.w - b.w};
}
static V4 mul4(V4 a, V4 b) {
  return (V4){a.x * b.x, a.y * b.y, a.z * b.z, a.w * b.w};
}
static V4 scale4(V4 a, float k) { return mul4(a, (V4){k, k, k, k}); }
static float dot4(V4 a, V4 b) {
  return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w;
}
static V4 mv4(M4 m, V4 v) {
  return add4(
      add4(add4(scale4(m.c[0], v.x), scale4(m.c[1], v.y)), scale4(m.c[2], v.z)),
      scale4(m.c[3], v.w));
}
NI void add(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++)
    o[i] = add4(a[i], b[i]);
}
NI void mul(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++)
    o[i] = mul4(a[i], b[i]);
}
NI void dot(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++) {
    float d = dot4(a[i], b[i]);
    o[i] = (V4){d, d, d, d};
  }
}
NI void lerp(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++)
    o[i] = add4(a[i], scale4(sub4(b[i], a[i]), 0.375f));
}
NI void norm4(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++) {
    V4 v = a[i];
    float l = sqrtf(dot4(v, v));
    o[i] = l == 0 ? v : (V4){v.x / l, v.y / l, v.z / l, v.w / l};
  }
}
NI void mv(V4 *a, V4 *b, V4 *o, M4 m) {
  for (int i = 0; i < N; i++)
    o[i] = mv4(m, a[i]);
}
NI void mm(M4 *a, M4 *b, M4 *o) {
  for (int i = 0; i < N; i++)
    for (int c = 0; c < 4; c++)
      o[i].c[c] = mv4(a[i], b[i].c[c]);
}
NI void cross(V3 *a, V3 *b, V3 *o, M4 m) {
  for (int i = 0; i < N; i++) {
    V3 v = a[i], w = b[i];
    o[i] = (V3){v.y * w.z - v.z * w.y, v.z * w.x - v.x * w.z,
                v.x * w.y - v.y * w.x};
  }
}
NI void norm3(V3 *a, V3 *b, V3 *o, M4 m) {
  for (int i = 0; i < N; i++) {
    V3 v = a[i];
    float l = sqrtf(v.x * v.x + v.y * v.y + v.z * v.z);
    o[i] = l == 0 ? v : (V3){v.x / l, v.y / l, v.z / l};
  }
}
NI void particle(V4 *p, V4 *v, V4 *a) {
  for (int i = 0; i < N; i++) {
    v[i] = add4(v[i], scale4(a[i], 0.0001f));
    p[i] = add4(p[i], scale4(v[i], 0.0001f));
  }
}
typedef struct {
  V3 pos, normal, color;
} Vertex;
typedef struct {
  M4 mvp, model;
} Params;
typedef struct {
  V4 pos;
  V3 normal, color;
} Varying;
NI Varying cube_vs(Vertex v, Params u) {
  V4 n = mv4(u.model, (V4){v.normal.x, v.normal.y, v.normal.z, 0});
  return (Varying){
      mv4(u.mvp, (V4){v.pos.x, v.pos.y, v.pos.z, 1}), {n.x, n.y, n.z}, v.color};
}
// lib/game/softgl.jo: __sw_project, with nf=10 and no flat integer varyings.
NI void project(float *q, float *o, int nf, double vx, double vy, double vw,
                double vh, const unsigned char *flat) {
  float w = q[3], iw = 0;
  if (w != 0)
    iw = 1.0f / w;
  o[0] = (float)(vx + ((double)(q[0] * iw) * 0.5 + 0.5) * vw);
  o[1] = (float)(vy + ((double)(q[1] * iw) * 0.5 + 0.5) * vh);
  o[2] = q[2] * iw * 0.5f + 0.5f;
  o[3] = iw;
  for (int f = 0; f < nf; f++)
    o[4 + f] = flat[f] ? q[f] : q[f] * iw;
}
NI void vertex(Vertex *a, float *out, Params u) {
  unsigned char flat[10] = {0};
  for (int i = 0; i < N; i++) {
    Varying q = cube_vs(a[i], u);
    project((float *)&q, out + i * 14, 10, 0, 0, 640, 480, flat);
  }
}
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  char *mode = argv[1];
  M4 m = {{{1, 2, 3, 0}, {2, 1, 0, 0}, {0, 0, 1, 0}, {3, 2, 1, 1}}};
  if (!strcmp(mode, "mm")) {
    M4 *a = calloc(N, sizeof(M4)), *b = calloc(N, sizeof(M4)),
       *o = calloc(N, sizeof(M4));
    for (int i = 0; i < N; i++)
      a[i] = b[i] = m;
    for (int r = 0; r < R; r++)
      mm(a, b, o);
    printf("%.9g\n", o[73].c[2].z);
  } else if (!strcmp(mode, "cross") || !strcmp(mode, "norm3")) {
    V3 a[N], b[N], o[N];
    for (int i = 0; i < N; i++) {
      a[i] = (V3){(float)i * 0.001f + 1, 2, 3};
      b[i] = (V3){3, 1, 2};
    }
    for (int r = 0; r < R; r++) {
      if (!strcmp(mode, "cross"))
        cross(a, b, o, m);
      else
        norm3(a, b, o, m);
    }
    printf("vec3(%.9g, %.9g, %.9g)\n", o[73].x, o[73].y, o[73].z);
  } else if (!strcmp(mode, "vertex")) {
    Vertex a[N];
    float out[N * 14];
    for (int i = 0; i < N; i++)
      a[i] = (Vertex){
          {(float)i * 0.001f, 0.2f, 0.3f}, {0, 1, 0}, {0.3f, 0.4f, 0.5f}};
    for (int r = 0; r < R; r++)
      vertex(a, out, (Params){m, m});
    printf("%.9g\n", out[73 * 14]);
  } else {
    V4 a[N], b[N], o[N];
    for (int i = 0; i < N; i++) {
      a[i] = (V4){(float)i * 0.001f + 1, 2, 3, 4};
      b[i] = (V4){3, 1, 2, 0.5f};
      o[i] = (V4){0};
    }
    for (int r = 0; r < R; r++) {
#define MODE(name)                                                             \
  if (!strcmp(mode, #name))                                                    \
    name(a, b, o, m);                                                          \
  else
      MODE(add)
      MODE(mul) MODE(dot) MODE(lerp) MODE(norm4)
          MODE(mv) if (!strcmp(mode, "particle")) particle(a, b, o);
    }
    V4 v = !strcmp(mode, "particle") ? a[73] : o[73];
    printf("vec4(%.9g, %.9g, %.9g, %.9g)\n", v.x, v.y, v.z, v.w);
  }
}
