# Values as bytes: to_bytes / from_bytes

`to_bytes(value)` writes any value `to_text` can (numbers, bool, str, arrays, fixed-size arrays,
maps, optionals, tuples, structs, enums with fields, unions, vectors) in a binary form.
`from_bytes[T](b)` reads it back with `from_text`'s tolerance. The code is lib/std/binary.jo. The
compiler adds the type-specific parts through four intrinsics in compiler/expr.jo:
`__bin_schema`, `__bin_info`, `__bin_write` and `__bin_read`. The file is read only for programs
that name one of its functions (`on_demand_names`).

## The bytes

```
"SLPB" 1                    magic and version
schema                      varint ntypes, each type, then the value's kind
value                       positional, as the schema says
```

**Schema.** It lists each struct and enum type that the value's type reaches, once, in the order
they are first met. That order is a depth-first walk from the value's type through fields, in
declaration order. It covers every type the static type reaches, whether or not the value holds one.
- A struct entry is `0`, its name, the field count, then each field's name and kind. Fields that
  are function values or pointers are left out, as `from_text` leaves them.
- An enum entry is `1`, its name, the variant count, then each variant's name, its field count
  and each field's kind.
- Names are a varint length and the bytes.

**Kinds.** A kind is a code, followed by more for the compound kinds:

| code | kind | followed by |
|---|---|---|
| 1 | bool | |
| 2-5 | i8, i16, i32, int | |
| 6-9 | u8, u16, u32, u64 | |
| 10, 11 | f32, f64 | |
| 12 | str | |
| 13-15, 16-18 | vec2-vec4, ivec2-ivec4 | |
| 32 | T[] (and `soa T[]`) | T |
| 33 | T[N] | N, T |
| 34 | map | K, V |
| 35 | T? | T |
| 36 | tuple | n, each |
| 37 | union | n, each member (in the compiler's member order) |
| 38, 39 | struct, enum | the type's place in the schema |

**Values.**

| kind | written as |
|---|---|
| bool | one byte, 0 or 1 |
| i8, u8 | one byte, as it is |
| i16, i32, int | a zigzag varint |
| u16, u32 | a varint |
| u64 | 8 bytes, little-endian |
| f32, f64 | 4 or 8 bytes, the float's bits (NaN payloads and -0.0 kept) |
| vectors | their floats' (or i32s') bytes |
| str | a varint length, then its bytes (any bytes, NUL too) |
| T[] | a varint count, then the elements |
| T[N] | N elements, no count |
| T? | 0 for none, or 1 and the value |
| enum | a varint variant number, then that variant's fields |
| union | a varint member number, then the member's value |
| map | a varint count, then key and value in turn, in the map's own (insertion) order |
| tuple, struct | the elements or fields, in order |

An array (`T[]` or `T[N]`) of a leaf kept in a fixed number of bytes is packed. Those leaves are
bool, the numbers and the vectors. Their elements' bytes go as they are in memory: 4 bytes for each
i32 of an `i32[]`, not varints. Packed arrays are written and, when the reading program has the
same element kind, read with one copy.

The same value always gives the same bytes. A map is written in its iteration order, so two
maps that are `==` but were filled in different orders give different bytes, just as their
`to_text` differs.

## Reading: the plan

`from_bytes[T]` parses the schema in the bytes and also the program's own schema for T (the
constant `__bin_schema` makes). When the two are the same bytes, the program's schema is the
saved one, and nothing is parsed twice.

It then makes a plan that says how each saved kind is read as the program's kind:
- Struct fields are matched by name. A saved field the struct no longer has is skipped. To skip
  it, the reader walks its kind in the saved schema.
- A field the struct gained keeps the value `__default_init` gave it.
- Enum variants are matched by name. A variant's fields are matched by position: extra saved
  fields are skipped, and missing ones keep their defaults.
- Union members are matched by their kind as written (`Order`, `int[]`), or else by a numeric
  kind of the same family.
- Whole numbers read as any whole-number kind and are checked against its range. f32 and f64
  read as each other. A saved `T` reads where the program now has a `T?`.
- Any other change of kind becomes an error node. It is reported, with its path, only when a
  value of that kind is actually met (`pets[3].age: saved as int, but PetBadAge.age is str now`).
  An empty array of a changed element kind still reads.

A struct's plan is only made the first time one is read. Until then the plan holds a placeholder.
So the start of a reader costs about the schema's parse, and the rest is spread over the reading
(Aegean Skies' World: 157 types and 1520 fields; the start takes 0.25 ms natively).

Errors are `TextError`s, as `from_text` gives:
- `column` is the byte offset where the problem is.
- `line` is 0.
- `path` is the place in the value, such as `items[2].count`.

Every read is bounds-checked. A count larger than the bytes left can hold is an error before
anything is allocated. Bytes that are cut short or spoiled give an error, never a crash (the
test spoils bytes at random 2000 times).

## A step at a time

`byte_writer(v)` and `byte_reader[T](b)` keep an explicit stack of frames. A frame is a closure
over one struct, array or map, with the index to go on from.
- The writer's frames hold copies of the values they write. Arrays and maps in those copies are
  shared, not copied.
- The reader's frames point at the place being filled. That place sits inside the value being
  built, in an array already sized, so it does not move.
- An optional's or a union's payload is read into a cell of its own. The cell is put in place
  when the payload is done.

The compiler writes a struct's code so that it resumes at any field, and returns after a field
that started a frame. A flat type is written and read whole, with no frame. A flat type has no
arrays (other than packed ones), no maps and no recursion, so its work is bounded by its type.
Steps look at the clock after 4 KB of bytes or 16 frames.

Done whole in one step:
- a string, or a packed array (one memory copy);
- a flat struct;
- a tuple's elements, an enum variant's fields, a map's keys;
- on reading, a field being skipped and the fields of a recursive type that are boxed.

`to_bytes` and `from_bytes` run the same code with no frames: their composites recurse.
