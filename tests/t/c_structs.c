// The C side of tests/t/c_structs.jo: structs passed and given back by value, built by
// tools/runtests.py into the shared library the test loads (no libc: only arithmetic).
#include <stdint.h>

#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif

typedef struct { float x, y; } V2;
typedef struct { float x, y, z; } V3;
typedef struct { float x, y, w, h; } Rect;
typedef struct { uint8_t r, g, b, a; } Color;
typedef struct { double x, y; } D2;
typedef struct { int32_t n; float f; } IF;
typedef struct { double d; int64_t n; } DN;
typedef struct { int64_t a, b, c; } Big;
typedef struct { uint32_t id; int32_t width, height, mipmaps, format; } Tex;
typedef struct { float m[16]; } Mat;
typedef struct { uint8_t a; uint16_t b; } Small;
typedef struct { V2 pos; float r; uint8_t tag[4]; } Mixed;
typedef struct { int64_t a, b; } I2;
typedef struct { double x, y, z; } D3;
typedef struct { uint8_t a, b, c; } Three;

API V2 v2_add(V2 a, V2 b) { V2 r = { a.x + b.x, a.y + b.y }; return r; }
API float v2_dot(V2 a, V2 b) { return a.x * b.x + a.y * b.y; }
API V3 v3_cross(V3 a, V3 b) { V3 r = { a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x }; return r; }
API Rect rect_grow(Rect r, float by) { Rect o = { r.x - by, r.y - by, r.w + 2 * by, r.h + 2 * by }; return o; }
API float rect_area(Rect r) { return r.w * r.h; }
API Color color_mix(Color a, Color b) { Color c = { (uint8_t)((a.r + b.r) / 2), (uint8_t)((a.g + b.g) / 2), (uint8_t)((a.b + b.b) / 2), (uint8_t)((a.a + b.a) / 2) }; return c; }
API uint32_t color_pack(Color c) { return (uint32_t)c.r << 24 | (uint32_t)c.g << 16 | (uint32_t)c.b << 8 | c.a; }
API D2 d2_scale(D2 a, double k) { D2 r = { a.x * k, a.y * k }; return r; }
API IF if_swap(IF a) { IF r = { (int32_t)a.f, (float)a.n }; return r; }
API DN dn_next(DN a) { DN r = { a.d * 2, a.n + 1 }; return r; }
API Big big_sum(Big a, Big b) { Big r = { a.a + b.a, a.b + b.b, a.c + b.c }; return r; }
API int64_t big_clobber(Big a) { int64_t s = a.a + a.b + a.c; a.a = 999; a.b = 999; return s; }
API Tex tex_make(uint32_t id, int32_t w, int32_t h) { Tex t = { id, w, h, 1, 7 }; return t; }
API int64_t tex_pixels(Tex t, int32_t scale) { return (int64_t)t.width * t.height * scale + t.id + t.format; }
API float mat_trace(Mat m) { return m.m[0] + m.m[5] + m.m[10] + m.m[15]; }
API Mat mat_scale(float k) { Mat m = {{0}}; m.m[0] = k; m.m[5] = k; m.m[10] = k; m.m[15] = 1; return m; }
API Small small_inc(Small s) { Small r = { (uint8_t)(s.a + 1), (uint16_t)(s.b + 1000) }; return r; }
API Mixed mixed_move(Mixed m, V2 by) { m.pos.x += by.x; m.pos.y += by.y; m.r *= 2; m.tag[3] = (uint8_t)(m.tag[0] + m.tag[1]); return m; }
API D3 d3_add(D3 a, D3 b) { D3 r = { a.x + b.x, a.y + b.y, a.z + b.z }; return r; }
API Three three_rev(Three t) { Three r = { t.c, t.b, t.a }; return r; }
// (registers run out: on x86-64 Linux the struct goes on the stack, g in the last register)
API int64_t many_ints(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e, I2 s, int64_t g) { return a + b * 10 + c * 100 + d * 1000 + e * 10000 + s.a * 100000 + s.b * 1000000 + g * 10000000; }
API double many_floats(double a, double b, double c, double d, double e, double f, double g, V3 v, double h) { return a + b + c + d + e + f + g + v.x * 10 + v.y * 100 + v.z * 1000 + h * 10000; }
API int64_t many_ints8(int64_t a, int64_t b, int64_t c, int64_t d, int64_t e, int64_t f, int64_t g, I2 s, int64_t h) { return a + b * 2 + c * 3 + d * 4 + e * 5 + f * 6 + g * 7 + s.a * 100 + s.b * 1000 + h * 10000; }
API double d3_late(double a, double b, double c, double d, double e, double f, D3 v, float g, int32_t n) { return a + b + c + d + e + f + v.x * 10 + v.y * 100 + v.z * 1000 + g * 10000 + n * 100000; }
// (a struct among scalars of both kinds)
API double interleave(int32_t i, V2 a, double d, Color c, Big big, float f, Rect r) { return i + a.x + a.y + d + c.r + c.a + big.a + big.c + f + r.x + r.h; }
// (a C function pointer taking and giving structs)
typedef V2 (*V2Fn)(V2, V2);
API V2Fn get_v2_add(void) { return v2_add; }
