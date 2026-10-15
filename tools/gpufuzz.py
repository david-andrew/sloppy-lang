#!/usr/bin/env python3
"""GPU differential fuzzing: generate random compute functions (numbers of every width, bools,
vectors, fixed-size arrays, structs, helper functions with mut parameters, compound assignments,
branches and loops) and check that the CPU, Vulkan on the GPU and Vulkan on Mesa's software
driver (lavapipe) compute the same results. Every invocation writes what its variables hold at the
end into buffers, which the program prints.

What may differ is left out: `int`, `i64`, `u64` and `f64` (32 bits on the GPU), float division
and functions the GPU computes approximately. Floats are compared with a tolerance (a GPU may fuse
a * b + c).

usage: tools/gpufuzz.py [count] [--seed N] [--keep] [--no-lavapipe] [--shaders]
       tools/gpufuzz.py --reduce build/gpufuzz/fail_<seed>.jo
--shaders puts the code in fragment shaders instead, and compares the frames the software
renderer, OpenGL (GLSL) and Vulkan (SPIR-V) draw.
Failing programs are saved to build/gpufuzz/fail_<seed>.jo; --reduce leaves out what it can
while the results still differ (into fail_<seed>_min.jo).
"""
import os, random, subprocess, sys

F2I_MARK = "# (integers made from floats)"


def off_by_one(a, b):
    try: return abs(int(a) - int(b)) <= 1
    except ValueError: return a == b

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOPPY = os.environ.get("SLOPPY_FUZZ_COMPILER") or os.path.join(ROOT, "bin", "sloppy")
ENV = dict(os.environ, SLOPPY_LIB=os.path.join(ROOT, "lib"))
OUT = os.path.join(ROOT, "build", "gpufuzz")
LVP = "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json"
os.makedirs(OUT, exist_ok=True)

INTS = ["i32", "u32", "i16", "u16", "i8", "u8"]
BITS = {"i32": 32, "u32": 32, "i16": 16, "u16": 16, "i8": 8, "u8": 8}
SIGNED = {"i32", "i16", "i8"}
NIDS = 96


def fits(v, t):
    b = BITS[t]
    if t in SIGNED: return -(1 << (b - 1)) <= v < (1 << (b - 1))
    return 0 <= v < (1 << b)


# integers are made from floats through these (shader frames that differ are made again with
# them giving 0: a hash of the results cannot tell an integer off by one from any other mistake)
FI = ["fi = (x: f32) -> f32: x", "fi2 = (x: vec2) -> vec2: x", "fi3 = (x: vec3) -> vec3: x"]
FI0 = ["fi = (x: f32) -> f32: 0.0", "fi2 = (x: vec2) -> vec2: vec2(0.0, 0.0)", "fi3 = (x: vec3) -> vec3: vec3(0.0, 0.0, 0.0)"]

# what every program has: structs, and helpers with mut parameters, early returns, loops, and
# arrays and structs as parameters and results
COMMON = ["struct S:", "    a: i32", "    b: f32", "    c: u8",
          "struct T:", "    v: vec2", "    arr: i16[2]", "    s: S", "    f: bool",
          "struct B:", "    a: u8", "    b: i16", "    c: bool", "    d: u32", "    e: ivec2", "    f: i8",
          "bump = (v: mut i32, k: i32):", "    v = v * i32(3) + k", "    pass",
          "grow = (s: mut S, k: u8):", "    s.c += k", "    s.a -= i32(k)", "    pass",
          "mks = (a: i32, b: f32) -> S: S(a * i32(2), b, u8(a))",
          "hret = (x: i32) -> i32:", "    if x < i32(0): return -x / i32(3)",
          "    loop k in [0..3):", "        if x > i32(k * 100): return x - i32(k)", "    x xor i32(5)",
          "sum4 = (a: i32[4]) -> i32: a[0] + a[1] * i32(3) + a[2] * i32(5) + a[3] * i32(7)",
          "rev = (a: i32[4]) -> i32[4]: [a[3], a[2], a[1], a[0]]"] + FI


class Gen:
    def __init__(self, rnd):
        self.r = rnd
        self.lines = []
        self.vars = {t: [] for t in INTS + ["f32", "bool", "ivec2", "vec2", "vec3", "vec4", "ivec3"]}
        self.f2i = False        # (integers made from floats)
        self.grids = []          # (name, elem type) of 2 x 2 arrays of arrays
        self.ts = []             # T variables
        self.sarrs = []          # S[2] variables
        self.ro = set()          # names that cannot be assigned (loop variables)
        self.arrays = []         # (name, elem type, length) of fixed-size arrays
        self.structs = []        # names of S variables (a: i32, b: f32, c: u8)
        self.depth = 1
        self.n = 0
        self.helpers = []        # (name, param types, result type)

    def fresh(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def emit(self, s):
        self.lines.append("    " * self.depth + s)

    # ---------------- expressions ----------------
    def lit(self, t):
        r = self.r
        if t == "f32": return f"f32({r.choice(['0.0', '1.0', '-1.5', '0.25', '3.0', '-7.75', '100.0', '0.5', '-0.125'])})"
        if t == "bool": return r.choice(["true", "false"])
        vals = [0, 1, 2, 3, 5, 7, 31, 32, 33, 63, 64, 100, 127, 128, 255, 256, 1000, 32767, 32768, 65535,
                2147483647, -1, -2, -7, -128, -129, -32768, -2147483648]
        return f"{t}({r.choice([v for v in vals if fits(v, t)])})"

    def leaf(self, t):
        r = self.r
        c = r.random()
        if t in INTS or t == "f32" or t == "bool":
            if c < 0.55 and self.vars[t]: return r.choice(self.vars[t])
            if c < 0.65 and t == "i32" and self.vars["ivec2"]: return f"{r.choice(self.vars['ivec2'])}.{r.choice('xy')}"
            if c < 0.68 and t == "i32" and self.vars["ivec3"]: return f"{r.choice(self.vars['ivec3'])}.{r.choice('xyz')}"
            if c < 0.65 and t == "f32":
                vs = [(v, k) for k in ("vec2", "vec3", "vec4") for v in self.vars[k]]
                if vs:
                    v, k = r.choice(vs)
                    return f"{v}.{r.choice('xyzw'[:int(k[3])])}"
            gs = [g for g in self.grids if g[1] == t]
            if c < 0.7 and gs: return f"{r.choice(gs)[0]}[{self.index(2)}][{self.index(2)}]"
            arrs = [a for a in self.arrays if a[1] == t]
            if c < 0.75 and arrs:
                a, _, n = r.choice(arrs)
                return f"{a}[{self.index(n)}]"
            if c < 0.8 and self.structs and t in ("i32", "f32", "u8"):
                return f"{r.choice(self.structs)}.{ {'i32': 'a', 'f32': 'b', 'u8': 'c'}[t] }"
            if c < 0.85 and self.ts:
                tv = r.choice(self.ts)
                if t == "i16": return f"{tv}.arr[{self.index(2)}]"
                if t == "bool": return f"{tv}.f"
                if t == "f32": return f"{tv}.v.{r.choice('xy')}"
                if t in ("i32", "u8"): return f"{tv}.s.{ {'i32': 'a', 'u8': 'c'}[t] }"
            if c < 0.88 and self.sarrs and t in ("i32", "f32", "u8"):
                return f"{r.choice(self.sarrs)}[{self.index(2)}].{ {'i32': 'a', 'f32': 'b', 'u8': 'c'}[t] }"
            return self.lit(t)
        if self.vars[t] and c < 0.6: return r.choice(self.vars[t])
        if t == "ivec2":
            if self.vars["ivec3"] and c < 0.75: return f"{r.choice(self.vars['ivec3'])}.{r.choice(['xy', 'zx', 'yz'])}"
            return f"ivec2({self.expr('i32', 3)}, {self.expr('i32', 3)})"
        if t == "ivec3": return f"ivec3({self.expr('i32', 3)}, {self.expr('i32', 3)}, {self.expr('i32', 3)})"
        if t == "vec3":
            if self.vars["vec4"] and c < 0.8: return f"{r.choice(self.vars['vec4'])}.{r.choice(['xyz', 'yzw', 'zyx', 'xxy'])}"
            return f"vec3({self.expr('f32', 3)}, {self.expr('f32', 3)}, {self.expr('f32', 3)})"
        if t == "vec4": return f"vec4({self.expr('vec2', 3)}, {self.expr('f32', 3)}, {self.expr('f32', 3)})"
        if self.vars["vec3"] and c < 0.8: return f"{r.choice(self.vars['vec3'])}.{r.choice(['xy', 'yz', 'zx'])}"
        return f"vec2({self.expr('f32', 3)}, {self.expr('f32', 3)})"

    def index(self, n):
        # (in bounds: the low bits of any integer)
        return f"int({self.expr(self.r.choice(INTS), 3)}) & {n - 1}"

    def expr(self, t, d=0):
        r = self.r
        if d >= 4 or r.random() < 0.25: return self.leaf(t)
        if t in INTS: return self.iexpr(t, d)
        if t == "f32": return self.fexpr(d)
        if t == "bool": return self.bexpr(d)
        if t == "ivec2":
            op = r.choice(["+", "-", "*", "neg", "conv", "ctor", "/", "*s", "if"])
            if op == "neg": return f"(-{self.expr(t, d + 1)})"
            if op == "/": return f"({self.expr(t, d + 1)} / ivec2({self.expr('i32', d + 2)} | i32(1), {self.expr('i32', d + 2)} | i32(1)))"
            if op == "*s": return f"({self.expr(t, d + 1)} * {self.expr('i32', d + 2)})"
            if op == "if": return f"(if {self.expr('bool', d + 1)}: {self.expr(t, d + 1)} else: {self.expr(t, d + 1)})"
            if op == "conv":
                self.f2i = True
                return f"ivec2(fi2({self.expr('vec2', d + 1)}))"
            if op == "ctor": return f"ivec2({self.expr('i32', d + 1)}, {self.expr('i32', d + 1)})"
            return f"({self.expr(t, d + 1)} {op} {self.expr(t, d + 1)})"
        if t == "ivec3":
            op = r.choice(["+", "-", "*", "neg", "conv", "leaf", "*s"])
            if op == "neg": return f"(-{self.expr(t, d + 1)})"
            if op == "conv":
                self.f2i = True
                return f"ivec3(fi3({self.expr('vec3', d + 1)}))"
            if op == "*s": return f"({self.expr(t, d + 1)} * {self.expr('i32', d + 2)})"
            if op == "leaf": return self.leaf(t)
            return f"({self.expr(t, d + 1)} {op} {self.expr(t, d + 1)})"
        if t in ("vec3", "vec4"):
            op = r.choice(["+", "-", "*s", "neg", "leaf", "if"])
            if op == "if": return f"(if {self.expr('bool', d + 1)}: {self.expr(t, d + 1)} else: {self.expr(t, d + 1)})"
            if op == "neg": return f"(-{self.expr(t, d + 1)})"
            if op == "*s": return f"({self.expr(t, d + 1)} * {self.lit('f32')})"
            if op == "leaf": return self.leaf(t)
            return f"({self.expr(t, d + 1)} {op} {self.expr(t, d + 1)})"
        op = r.choice(["+", "-", "*s", "neg", "conv", "ctor"])
        if op == "neg": return f"(-{self.expr(t, d + 1)})"
        if op == "conv": return f"vec2(ivec2({self.small('i32', d + 1)}, {self.small('i32', d + 1)}))"
        if op == "ctor": return f"vec2({self.expr('f32', d + 1)}, {self.expr('f32', d + 1)})"
        if op == "*s": return f"({self.expr(t, d + 1)} * {self.lit('f32')})"
        return f"({self.expr(t, d + 1)} {op} {self.expr(t, d + 1)})"

    def small(self, t, d):
        # an integer that stays small (for floats made from it)
        return f"({self.expr(t, d)} % {t}(1000))"

    def iexpr(self, t, d):
        r = self.r
        op = r.choice(["+", "-", "*", "&", "|", "xor", "/", "%", "<<", ">>", "neg", "not", "conv", "fconv",
                       "bconv", "min", "max", "abs", "if", "call", "clamp"])
        a = lambda: self.expr(t, d + 1)
        if op in ("+", "-", "*", "&", "|", "xor", "<<", ">>"): return f"({a()} {op} {a()})"
        if op in ("/", "%"): return f"({a()} {op} ({a()} | {t}(1)))"
        if op == "neg": return f"(-{a()})"
        if op == "not": return f"(~{a()})"
        if op == "conv": return f"{t}({self.expr(r.choice(INTS), d + 1)})"
        if op == "fconv":
            self.f2i = True
            return f"{t}(fi({self.expr('f32', d + 1)}))"
        if op == "bconv": return f"{t}({self.expr('bool', d + 1)})"
        if op in ("min", "max"): return f"{op}({a()}, {a()})"
        if op == "abs" and t in SIGNED: return f"abs({a()})"
        if op == "clamp":
            lo, hi = sorted([int(self.lit(t)[len(t) + 1:-1]), int(self.lit(t)[len(t) + 1:-1])])
            return f"clamp({a()}, {t}({lo}), {t}({hi}))"
        if op == "if": return f"(if {self.expr('bool', d + 1)}: {a()} else: {a()})"
        if op == "call" and t == "i32" and r.random() < 0.5:
            k = r.random()
            if k < 0.4: return f"hret({a()})"
            arrs = [x for x in self.arrays if x[1] == "i32" and x[2] == 4]
            if k < 0.7 and arrs: return f"sum4({r.choice(arrs)[0]})"
            if k < 0.85 and arrs: return f"rev({r.choice(arrs)[0]})[{self.index(4)}]"
            return f"mks({a()}, {self.expr('f32', d + 1)}).a"
        if op == "call":
            hs = [h for h in self.helpers if h[2] == t]
            if hs:
                name, ps, _ = r.choice(hs)
                return f"{name}({', '.join(self.expr(p, d + 2) for p in ps)})"
        return a()

    def fexpr(self, d):
        r = self.r
        op = r.choice(["+", "-", "*", "neg", "conv", "abs", "floor", "min", "max", "if", "trunc", "ceil", "fract", "sign", "step", "mix", "mat"])
        if op in ("ceil", "fract", "sign"): return f"{op}({self.expr('f32', d + 1)})"
        if op == "step": return f"step({self.expr('f32', d + 1)}, {self.expr('f32', d + 1)})"
        if op == "mix": return f"mix({self.expr('f32', d + 1)}, {self.expr('f32', d + 1)}, f32({r.choice(['0.0', '0.5', '1.0', '0.25'])}))"
        if op == "mat" and d <= 1:
            cols = ", ".join(f"vec4({', '.join(self.lit('f32') for _ in range(4))})" for _ in range(4))
            return f"(mat4({cols}) * {self.expr('vec4', d + 1)}).{r.choice('xyzw')}"
        a = lambda: self.expr("f32", d + 1)
        if op == "*": return f"({a()} * {self.lit('f32')})"
        if op in ("+", "-"): return f"({a()} {op} {a()})"
        if op == "neg": return f"(-{a()})"
        if op == "conv": return f"f32({self.expr(r.choice(['i8', 'u8', 'i16', 'u16']), d + 1)})"
        if op in ("abs", "floor", "trunc"): return f"{op}({a()})"
        if op in ("min", "max"): return f"{op}({a()}, {a()})"
        return f"(if {self.expr('bool', d + 1)}: {a()} else: {a()})"

    def bexpr(self, d):
        r = self.r
        op = r.choice(["cmp", "fcmp", "and", "or", "not", "veq"])
        if op == "cmp":
            t = r.choice(INTS)
            return f"({self.expr(t, d + 1)} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {self.expr(t, d + 1)})"
        if op == "fcmp": return f"({self.expr('f32', d + 1)} {r.choice(['<', '>=', '=='])} {self.expr('f32', d + 1)})"
        if op == "and": return f"({self.expr('bool', d + 1)} and {self.expr('bool', d + 1)})"
        if op == "or": return f"({self.expr('bool', d + 1)} or {self.expr('bool', d + 1)})"
        if op == "veq": return f"({self.expr('ivec2', d + 1)} == {self.expr('ivec2', d + 1)})"
        return f"(not {self.expr('bool', d + 1)})"

    # ---------------- statements ----------------
    def assignable(self, t):
        return [v for v in self.vars[t] if v not in self.ro]

    def stmt(self, budget):
        r = self.r
        c = r.random()
        t = r.choice(INTS + ["f32", "bool", "ivec2", "vec2", "vec3", "vec4", "ivec3"])
        if c < 0.25 or not any(self.assignable(x) for x in self.vars):
            v = self.fresh("v")
            self.emit(f"{v}: {t} = {self.expr(t)}")
            self.vars[t].append(v)
        elif c < 0.5:
            vs = self.assignable(t)
            if not vs: return
            v = r.choice(vs)
            if t in INTS:
                op = r.choice(["+=", "-=", "*=", "&=", "|=", "<<=", ">>=", "/=", "%=", "="])
                e = self.expr(t, 1)
                if op in ("/=", "%="): e = f"({e} | {t}(1))"
                self.emit(f"{v} {op} {e}")
            elif t == "f32": self.emit(f"{v} {r.choice(['+=', '-=', '='])} {self.expr(t, 1)}")
            elif t == "bool": self.emit(f"{v} {r.choice(['and=', 'or=', '='])} {self.expr(t, 1)}")
            elif t in ("vec3", "vec4") and r.random() < 0.5:
                # (a swizzle as the target)
                sw = r.choice(["x", "yz", "zx", "w"[:int(t[3]) - 3] or "y", "xy"])
                st = "f32" if len(sw) == 1 else f"vec{len(sw)}"
                self.emit(f"{v}.{sw} {r.choice(['+=', '-=', '='])} {self.expr(st, 1)}")
            else: self.emit(f"{v} {r.choice(['+=', '-=', '='])} {self.expr(t, 1)}")
        elif c < 0.6 and self.arrays:
            a, et, n = r.choice(self.arrays)
            op = "="
            if et in INTS: op = r.choice(["=", "+=", "-=", "*=", "<<="])
            self.emit(f"{a}[{self.index(n)}] {op} {self.expr(et, 1)}")
        elif c < 0.66 and self.structs:
            s = r.choice(self.structs)
            f, ft = r.choice([("a", "i32"), ("b", "f32"), ("c", "u8")])
            op = "+=" if ft != "u8" else r.choice(["+=", "*=", "="])
            self.emit(f"{s}.{f} {op} {self.expr(ft, 1)}")
        elif c < 0.74 and budget > 2:
            self.emit(f"if {self.expr('bool')}:")
            self.block(budget // 2)
            if r.random() < 0.5:
                self.emit("else:")
                self.block(budget // 2)
        elif c < 0.8 and budget > 2:
            k = self.fresh("k")
            self.emit(f"loop {k} in [0..{r.randint(1, 4)}):")
            kv = self.fresh("q")
            self.depth += 1
            self.emit(f"{kv} = i32({k})")
            self.vars["i32"].append(kv)
            self.ro.add(kv)
            self.depth -= 1
            self.block(budget // 2, keep=[kv])
            self.vars["i32"].remove(kv)
        elif c < 0.83:
            vs = self.assignable("i32")
            if vs: self.emit(f"bump({r.choice(vs)}, {self.expr('i32', 2)})")
        elif c < 0.86 and budget > 2:
            # a loop while a condition holds, with continue and break
            w = self.fresh("w")
            self.emit(f"{w} = i32(0)")
            self.emit(f"loop {w} < i32({r.randint(1, 5)}):")
            self.depth += 1
            self.emit(f"{w} += i32(1)")
            self.emit(f"if {self.expr('bool', 2)}: continue")
            self.depth -= 1
            self.block(budget // 2)
            self.depth += 1
            self.emit(f"if {self.expr('bool', 2)}: break")
            self.depth -= 1
            self.vars["i32"].append(w)
            self.ro.add(w)
        elif c < 0.89 and len(self.grids) < 2:
            g = self.fresh("g")
            et = r.choice(["i32", "u8", "f32"])
            self.emit(f"{g}: {et}[2][2] = [[{self.expr(et, 2)}, {self.expr(et, 2)}], [{self.expr(et, 2)}, {self.expr(et, 2)}]]")
            self.grids.append((g, et))
        elif c < 0.905 and self.grids:
            g, et = r.choice(self.grids)
            if r.random() < 0.3: self.emit(f"{g}[{self.index(2)}] = [{self.expr(et, 2)}, {self.expr(et, 2)}]")
            else: self.emit(f"{g}[{self.index(2)}][{self.index(2)}] {'+=' if et != 'u8' else '='} {self.expr(et, 1)}")
        elif c < 0.915 and len(self.ts) < 2:
            tv = self.fresh("t")
            self.emit(f"{tv} = T({self.expr('vec2', 2)}, [{self.expr('i16', 2)}, {self.expr('i16', 2)}], {'mks(' + self.expr('i32', 2) + ', ' + self.expr('f32', 2) + ')' if r.random() < 0.5 else 'S(' + self.expr('i32', 2) + ', ' + self.expr('f32', 2) + ', ' + self.expr('u8', 2) + ')'}, {self.expr('bool', 2)})")
            self.ts.append(tv)
        elif c < 0.93 and self.ts:
            tv = r.choice(self.ts)
            k = r.random()
            if k < 0.25: self.emit(f"{tv}.arr[{self.index(2)}] {r.choice(['+=', '*=', '-=', '='])} {self.expr('i16', 1)}")
            elif k < 0.45: self.emit(f"{tv}.s.c {r.choice(['+=', '*=', '='])} {self.expr('u8', 1)}")
            elif k < 0.6:
                sw = r.choice(["yx", "x", "xy"])
                self.emit(f"{tv}.v.{sw} {r.choice(['+=', '='])} {self.expr('f32' if len(sw) == 1 else 'vec2', 1)}")
            elif k < 0.75: self.emit(f"grow({tv}.s, {self.expr('u8', 2)})")
            elif k < 0.85: self.emit(f"{tv}.f = {self.expr('bool', 1)}")
            else: self.emit(f"{tv}.s = mks({self.expr('i32', 2)}, {self.expr('f32', 2)})")
        elif c < 0.94 and len(self.sarrs) < 2:
            sa_ = self.fresh("sa")
            self.emit(f"{sa_}: S[2] = [mks({self.expr('i32', 2)}, {self.expr('f32', 2)}), S({self.expr('i32', 2)}, {self.expr('f32', 2)}, {self.expr('u8', 2)})]")
            self.sarrs.append(sa_)
        elif c < 0.95 and self.sarrs:
            sa_ = r.choice(self.sarrs)
            k = r.random()
            if k < 0.4: self.emit(f"{sa_}[{self.index(2)}].c {r.choice(['+=', '*=', '-='])} {self.expr('u8', 1)}")
            elif k < 0.7: self.emit(f"grow({sa_}[{self.index(2)}], {self.expr('u8', 2)})")
            else: self.emit(f"{sa_}[{self.index(2)}] = mks({self.expr('i32', 2)}, {self.expr('f32', 2)})")
        elif c < 0.97 and len(self.arrays) < 3:
            a = self.fresh("arr")
            et = r.choice(["i32", "u8", "f32", "i16"])
            n = r.choice([2, 4])
            self.emit(f"{a}: {et}[{n}] = [{', '.join(self.expr(et, 2) for _ in range(n))}]")
            self.arrays.append((a, et, n))
        elif len(self.structs) < 2:
            s = self.fresh("s")
            self.emit(f"{s} = S({self.expr('i32', 2)}, {self.expr('f32', 2)}, {self.expr('u8', 2)})")
            self.structs.append(s)

    def block(self, budget, keep=()):
        # (what a block declares is gone after it)
        saved = {t: list(vs) for t, vs in self.vars.items()}
        sa, ss, sg, st, sr = list(self.arrays), list(self.structs), list(self.grids), list(self.ts), list(self.sarrs)
        self.depth += 1
        n0 = len(self.lines)
        for _ in range(max(1, self.r.randint(1, max(1, budget)))): self.stmt(budget - 1)
        if len(self.lines) == n0: self.emit("pass")
        self.depth -= 1
        for t in self.vars: self.vars[t] = saved[t] + [v for v in keep if v in self.vars[t] and v not in saved[t]]
        self.arrays, self.structs, self.grids, self.ts, self.sarrs = sa, ss, sg, st, sr

    def helper(self):
        name = self.fresh("h")
        t = self.r.choice(["i32", "u8", "i16", "u32"])
        ps = [self.r.choice(INTS) for _ in range(self.r.randint(1, 2))]
        saved = self.vars
        self.vars = {x: [] for x in saved}
        pn = []
        for p in ps:
            v = self.fresh("p")
            self.vars[p].append(v)
            self.ro.add(v)
            pn.append(f"{v}: {p}")
        body = self.expr(t, 1)
        self.vars = saved
        self.helpers.append((name, ps, t))
        return f"{name} = ({', '.join(pn)}) -> {t}: {body}"

    def program(self):
        r = self.r
        out = COMMON + ["struct P:", "    inp: GpuBuffer[i32]", "    oi: GpuBuffer[i32]", "    of: GpuBuffer[f32]", "    bs: GpuBuffer[B]"]
        for _ in range(r.randint(0, 3)): out.append(self.helper())
        self.lines = []
        for j, t in enumerate(["i32", "u32", "i16", "u8", "i8", "u16"]):
            v = self.fresh("in")
            self.emit(f"{v}: {t} = {t}(u.inp[id * 6 + {j}])")
            self.vars[t].append(v)
        f = self.fresh("f")
        self.emit(f"{f}: f32 = f32(i16(u.inp[id * 6 + 2])) * 0.25")
        self.vars["f32"].append(f)
        for _ in range(r.randint(4, 14)): self.stmt(4)
        # an element of a buffer of narrow fields, changed and written back
        self.emit("bb = u.bs[id]")
        for f, t in [("a", "u8"), ("b", "i16"), ("d", "u32"), ("f", "i8")]:
            if r.random() < 0.7: self.emit(f"bb.{f} {r.choice(['+=', '*=', '=', '-='])} {self.expr(t, 2)}")
        if r.random() < 0.5: self.emit(f"bb.c = {self.expr('bool', 2)}")
        if r.random() < 0.5: self.emit(f"bb.e {r.choice(['+=', '='])} {self.expr('ivec2', 2)}")
        self.emit("u.bs[id] = bb")
        # the results
        ints, floats = [], []
        for t in INTS:
            for v in self.vars[t]: ints.append(f"i32({v})")
        for v in self.vars["bool"]: ints.append(f"i32({v})")
        for v in self.vars["ivec2"]: ints += [f"{v}.x", f"{v}.y"]
        for v in self.vars["ivec3"]: ints += [f"{v}.x", f"{v}.y", f"{v}.z"]
        for v in self.vars["f32"]: floats.append(v)
        for k in ("vec2", "vec3", "vec4"):
            for v in self.vars[k]: floats += [f"{v}.{c}" for c in "xyzw"[:int(k[3])]]
        for g, et in self.grids:
            for i in range(2):
                for j in range(2): (floats if et == "f32" else ints).append(f"{'' if et == 'f32' else 'i32'}({g}[{i}][{j}])")
        for a, et, n in self.arrays:
            for i in range(n): (floats if et == "f32" else ints).append(f"{'' if et == 'f32' else 'i32'}({a}[{i}])")
        for s_ in self.structs + [f"{x}[{i}]" for x in self.sarrs for i in range(2)] + [f"{x}.s" for x in self.ts]:
            ints += [f"{s_}.a", f"i32({s_}.c)"]
            floats.append(f"{s_}.b")
        for x in self.ts:
            ints += [f"i32({x}.arr[0])", f"i32({x}.arr[1])", f"i32({x}.f)"]
            floats += [f"{x}.v.x", f"{x}.v.y"]
        ni, nf = max(len(ints), 1), max(len(floats), 1)
        for i, e in enumerate(ints): self.emit(f"u.oi[id * {ni} + {i}] = {e}")
        for i, e in enumerate(floats): self.emit(f"u.of[id * {nf} + {i}] = {e}")
        self.emit("pass")
        out.append("kern = (id: int, u: P):")
        out += self.lines
        vals = []
        for _ in range(NIDS * 6):
            vals.append(r.choice([r.randint(-2**31, 2**31 - 1), r.randint(-300, 300), r.choice([0, 1, -1, 2**31 - 1, -2**31, 255, 65535, 32767, -32768, 128])]))
        out.append(f"inp: i32[] = [{', '.join(f'i32({v})' for v in vals)}]")
        bs = []
        for _ in range(NIDS):
            bs.append(f"B(u8({r.randint(0, 255)}), i16({r.randint(-32768, 32767)}), {r.choice(['true', 'false'])}, u32({r.randint(0, 2**32 - 1)}), ivec2(i32({r.randint(-2**31, 2**31 - 1)}), i32({r.randint(-1000, 1000)})), i8({r.randint(-128, 127)}))")
        out.append(f"bs0: B[] = [{', '.join(bs)}]")
        out.append(f"p = P(gpu_buffer(inp), gpu_buffer[i32]({NIDS * ni}), gpu_buffer[f32]({NIDS * nf}), gpu_buffer(bs0))")
        out.append(f"dispatch(compute(kern), {NIDS}, p)")
        out.append("print(cpu(p.bs))")
        out.append("print(cpu(p.oi))")
        out.append("print(cpu(p.of))")
        if self.f2i: out.insert(0, F2I_MARK)
        return "\n".join(out) + "\n"


def shader_program(g):
    """the same kind of code in a fragment shader: each pixel makes its inputs from its position,
    and its color is a hash of the integer results (exact in 8-bit channels)"""
    r = g.r
    out = COMMON + ["struct V:", "    pos: vec2", "struct U:", "    k: f32", "struct O:", "    pos: vec4",
           "mix32 = (h: u32, x: u32) -> u32: (h xor x) * u32(16777619)",
           "pick = (s: u32, k: u32) -> u32:",
           "    x = (s xor k) * u32(747796405)",
           "    x = x xor (x >> u32(13))",
           "    c = x & u32(15)",
           "    if c == u32(0): return u32(0x80000000)",
           "    if c == u32(1): return u32(0x7FFFFFFF)",
           "    if c == u32(2): return u32(0xFFFFFFFF)",
           "    if c == u32(3): return x & u32(511)",
           "    x"]
    for _ in range(r.randint(0, 3)): out.append(g.helper())
    g.lines = []
    g.emit("seed = u32(i32(i.pos.x) + i32(i.pos.y) * i32(64)) * u32(2654435761)")
    for j, t in enumerate(["i32", "u32", "i16", "u8", "i8", "u16"]):
        v = g.fresh("in")
        g.emit(f"{v}: {t} = {t}(i32(pick(seed, u32({j + 1}))))")
        g.vars[t].append(v)
    f = g.fresh("f")
    g.emit(f"{f}: f32 = f32(i16(i32(pick(seed, u32(9))))) * 0.25")
    g.vars["f32"].append(f)
    for _ in range(r.randint(4, 14)): g.stmt(4)
    ints = []
    for t in INTS:
        for v in g.vars[t]: ints.append(f"u32(i32({v}))")
    for v in g.vars["bool"]: ints.append(f"u32({v})")
    for v in g.vars["ivec2"]: ints += [f"u32({v}.x)", f"u32({v}.y)"]
    for v in g.vars["ivec3"]: ints += [f"u32({v}.x)", f"u32({v}.y)", f"u32({v}.z)"]
    for a, et, n in g.arrays:
        if et != "f32":
            for k in range(n): ints.append(f"u32(i32({a}[{k}]))")
    for gd, et in g.grids:
        if et != "f32":
            for i_ in range(2):
                for j_ in range(2): ints.append(f"u32(i32({gd}[{i_}][{j_}]))")
    for s_ in g.structs + [f"{x}[{i_}]" for x in g.sarrs for i_ in range(2)] + [f"{x}.s" for x in g.ts]: ints += [f"u32({s_}.a)", f"u32({s_}.c)"]
    for x in g.ts: ints += [f"u32(i32({x}.arr[0]))", f"u32(i32({x}.arr[1]))", f"u32({x}.f)"]
    g.emit("h = u32(2166136261)")
    for e in ints: g.emit(f"h = mix32(h, {e})")
    g.emit("vec4(f32(h & u32(255)) / 255.0, f32((h >> u32(8)) & u32(255)) / 255.0, f32((h >> u32(16)) & u32(255)) / 255.0, 1)")
    out.append("vs = (v: V, u: U) -> O: O(vec4(v.pos, 0, 1))")
    out.append("fs = (i: O, u: U) -> vec4:")
    out += g.lines
    out += ["sh = make_shader(shader(vs, fs))",
            "m = mesh([V(vec2(-1, -1)), V(vec2(3, -1)), V(vec2(-1, 3))])",
            "draw = ():", "    clear()", "    draw(sh, m, U(1.0))"]
    return "\n".join(out) + "\n"


SHADER_RUNS = [("software", {"SLOPPY_SOFTWARE": "1", "SLOPPY_SOFT_SCALE": "1"}), ("opengl", {"SLOPPY_VULKAN": "0"}), ("vulkan", {"SLOPPY_VULKAN": "1"})]
# (with no desktop, over ssh on Windows: no OpenGL, which needs a window)
if os.environ.get("SLOPPY_HEADLESS"): SHADER_RUNS = [r for r in SHADER_RUNS if r[0] != "opengl"]


def shader_frames(prog):
    """the frame each renderer draws, as bytes (None and the error where it fails)"""
    exe = prog[:-3]
    if os.name == "nt": exe += ".exe"
    b = subprocess.run([SLOPPY, "build", prog, "-o", exe], capture_output=True, text=True, env=ENV)
    if b.returncode != 0: return None, "build failed:\n" + b.stderr[-2000:]
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from pngutil import png_rows
    frames = []
    for name, env in SHADER_RUNS:
        png = f"{exe}_{name}.png"
        if os.path.exists(png): os.remove(png)
        e = dict(ENV, SLOPPY_SCREENSHOT=png, SLOPPY_FRAMES="1", SLOPPY_WINDOW="64x64", SLOPPY_SCALE="1", **env)
        try:
            r = subprocess.run([exe], capture_output=True, text=True, timeout=120, env=e)
        except subprocess.TimeoutExpired:
            return None, f"{name}: timeout"
        if r.returncode != 0 or not os.path.exists(png): return None, f"{name} failed:\n{(r.stdout + r.stderr)[-2000:]}"
        w, h, bpp, rows = png_rows(png)
        frames.append((name, w, bpp, rows))
        os.remove(png)
    os.remove(exe)
    return frames, ""


def shader_diff(frames):
    _, w0, b0, r0 = frames[0]
    for name, w, bpp, rows in frames[1:]:
        for y, (ra, rb) in enumerate(zip(r0, rows)):
            for x in range(min(w0, w)):
                if ra[x * b0:x * b0 + 3] != rb[x * bpp:x * bpp + 3]:
                    return f"{frames[0][0]} and {name} differ at pixel ({x}, {y}): {tuple(ra[x * b0:x * b0 + 3])} vs {tuple(rb[x * bpp:x * bpp + 3])}"
    return ""


def run(prog, extra_env, timeout=60):
    env = dict(ENV, **extra_env)
    try:
        r = subprocess.run([SLOPPY, prog], capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    # (what it prints, without warnings: they go to stderr, and would come after it)
    if r.returncode == 0: return 0, r.stdout
    return r.returncode, r.stdout + r.stderr


def parse(out):
    lines = out.strip().split("\n")
    if len(lines) < 3: return None, None
    ints = [lines[-3]] + lines[-2].strip("[]").split(", ")     # (the buffer of B first, as written)
    floats = lines[-1].strip("[]").split(", ")
    return ints, floats


def same_floats(a, b):
    if len(a) != len(b): return False, -1
    for i, (x, y) in enumerate(zip(a, b)):
        if x == y: continue
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            return False, i
        if abs(fx - fy) <= 1e-3 + 1e-4 * max(abs(fx), abs(fy)): continue
        return False, i
    return True, -1


def differs(prog, lvp):
    """does the program run on the CPU and give other results on a GPU?"""
    if "fs = (" in open(prog).read():
        frames, err = shader_frames(prog)
        if frames is None: return not err.startswith("build failed") and not err.startswith("software")
        return shader_diff(frames) != ""
    c0, o0 = run(prog, {"SLOPPY_NO_GPU": "1"})
    if c0 != 0: return False
    i0, f0 = parse(o0)
    envs = [{}] + ([{"VK_ICD_FILENAMES": LVP}] if lvp else [])
    for env in envs:
        c1, o1 = run(prog, env)
        if c1 != 0: return True
        i1, f1 = parse(o1)
        if i1 != i0 or not same_floats(f0, f1)[0]: return True
    return False


def reduce(path, lvp):
    """drop lines of the compute function (and whole blocks) while the results still differ"""
    lines = open(path).read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("kern = ") or l.startswith("fs = ")) + 1
    tmp = os.path.join(OUT, "reduce.jo")
    changed = True
    while changed:
        changed = False
        i = start
        while i < len(lines) and lines[i].startswith("    "):
            ind = len(lines[i]) - len(lines[i].lstrip())
            j = i + 1
            while j < len(lines) and lines[j].startswith(" " * (ind + 4)): j += 1
            cand = lines[:i] + lines[j:]
            with open(tmp, "w") as f: f.write("\n".join(cand))
            if differs(tmp, lvp):
                lines = cand
                changed = True
                print(f"  {sum(1 for l in lines if l.startswith('    '))} lines")
            else: i += 1
    out = path.replace(".jo", "_min.jo")
    with open(out, "w") as f: f.write("\n".join(lines))
    print(f"reduced: {out}")


def main():
    args = sys.argv[1:]
    if "--reduce" in args:
        reduce(args[args.index("--reduce") + 1], "--no-lavapipe" not in args and os.path.exists(LVP))
        return
    count, seed, keep, lvp = 50, None, "--keep" in args, "--no-lavapipe" not in args and os.path.exists(LVP)
    if "--seed" in args: seed = int(args[args.index("--seed") + 1])
    nums = [a for a in args if a.isdigit() and (seed is None or a != str(seed))]
    if nums: count = int(nums[0])
    base = seed if seed is not None else random.randrange(1 << 30)
    shaders = "--shaders" in args
    failed = 0
    for k in range(count):
        s = base + k
        if shaders:
            prog = os.path.join(OUT, f"p_{s}.jo")
            g = Gen(random.Random(s))
            src = shader_program(g)
            with open(prog, "w") as f: f.write(src)
            frames, err = shader_frames(prog)
            msg = err if frames is None else shader_diff(frames)
            if msg and frames is not None and g.f2i:
                # (integers made from floats can be off by one: the floats may be too, as a GPU
                # may fuse a * b + c; the same program without them must agree)
                with open(prog, "w") as f: f.write(src.replace("\n".join(FI), "\n".join(FI0)))
                frames0, err0 = shader_frames(prog)
                if frames0 is not None and not shader_diff(frames0):
                    print(f"(inexact {s}: {msg}; the same without integers made from floats agrees)")
                    msg = ""
                with open(prog, "w") as f: f.write(src)
            if not msg:
                if not keep: os.remove(prog)
                print(f"ok {s}")
            else:
                failed += 1
                dst = os.path.join(OUT, f"fail_{s}.jo")
                os.replace(prog, dst)
                print(f"FAIL {s}: {msg}\n  saved {dst}")
            continue
        src = Gen(random.Random(s)).program()
        prog = os.path.join(OUT, f"p_{s}.jo")
        with open(prog, "w") as f: f.write(src)
        runs = [("cpu", {"SLOPPY_NO_GPU": "1"}), ("gpu", {})]
        if lvp: runs.append(("lavapipe", {"VK_ICD_FILENAMES": LVP}))
        outs = []
        for name, env in runs:
            code, out = run(prog, env)
            outs.append((name, code, out))
        ok = True
        msg = ""
        c0, o0 = outs[0][1], outs[0][2]
        if c0 != 0:
            ok = False
            msg = f"cpu run failed ({c0}):\n{o0[-2000:]}"
        else:
            i0, f0 = parse(o0)
            for name, code, out in outs[1:]:
                if code != 0:
                    ok, msg = False, f"{name} failed ({code}):\n{out[-2000:]}"
                    break
                i1, f1 = parse(out)
                # (integers made from floats, f32 -> i32 and vec -> ivec, can be off by one: the
                # floats may be too, as a GPU may fuse a * b + c, and land on either side of a
                # whole number)
                if i1 != i0 and len(i1) == len(i0) and all(off_by_one(a, b) for a, b in zip(i0, i1)) and F2I_MARK in src:
                    print(f"(inexact {s}: integers made from floats are off by one on {name})")
                    i1 = i0
                if i1 != i0:
                    j = next((j for j in range(min(len(i0), len(i1))) if i0[j] != i1[j]), -1)
                    ok, msg = False, f"{name}: integer result {j} differs: cpu {i0[j] if j >= 0 else len(i0)} vs {i1[j] if j >= 0 else len(i1)}"
                    break
                sf, j = same_floats(f0, f1)
                if not sf:
                    ok, msg = False, f"{name}: float result {j} differs: cpu {f0[j] if 0 <= j < len(f0) else len(f0)} vs {f1[j] if 0 <= j < len(f1) else len(f1)}"
                    break
        if ok:
            if not keep: os.remove(prog)
            print(f"ok {s}")
        else:
            failed += 1
            dst = os.path.join(OUT, f"fail_{s}.jo")
            os.replace(prog, dst)
            print(f"FAIL {s}: {msg}\n  saved {dst}")
    print(f"{count - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
