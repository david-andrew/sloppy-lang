#include <stdint.h>
int64_t c_apply(int64_t (*f)(int64_t), int64_t n) { return f(n); }
