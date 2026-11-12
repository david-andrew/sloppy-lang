/* QEMU plugin: executed guest instructions, summed at translated-block entry.
 * These kernels have no guest faults or early exits inside translated blocks.
 * Build against the header belonging to the QEMU executable used for measurement.
 */
#include <qemu-plugin.h>
#include <inttypes.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;
static _Atomic uint64_t instructions;
/* Optional begin/end function addresses delimit one single-threaded game frame.
 * Marker entry blocks start/stop counting; end's block is excluded. */
static uint64_t begin, end;
static _Atomic bool active = true;
static unsigned starts, stops;

static void start(unsigned int cpu, void *unused) {
    (void)cpu;
    (void)unused;
    atomic_store_explicit(&active, true, memory_order_relaxed);
    starts++;
}
static void stop(unsigned int cpu, void *unused) {
    (void)cpu;
    (void)unused;
    atomic_store_explicit(&active, false, memory_order_relaxed);
    stops++;
}

static void execute(unsigned int cpu, void *count) {
    (void)cpu;
    if (atomic_load_explicit(&active, memory_order_relaxed))
        atomic_fetch_add_explicit(&instructions, (uintptr_t)count, memory_order_relaxed);
}
static void translate(qemu_plugin_id_t id, struct qemu_plugin_tb *tb) {
    (void)id;
    uint64_t pc = qemu_plugin_tb_vaddr(tb);
    if (begin && pc == begin)
        qemu_plugin_register_vcpu_tb_exec_cb(tb, start, QEMU_PLUGIN_CB_NO_REGS, NULL);
    if (end && pc == end)
        qemu_plugin_register_vcpu_tb_exec_cb(tb, stop, QEMU_PLUGIN_CB_NO_REGS, NULL);
    qemu_plugin_register_vcpu_tb_exec_cb(tb, execute, QEMU_PLUGIN_CB_NO_REGS,
                                       (void *)(uintptr_t)qemu_plugin_tb_n_insns(tb));
}
static void finish(qemu_plugin_id_t id, void *unused) {
    (void)id;
    (void)unused;
    fprintf(stderr, "guest instructions: %" PRIu64 "\n", atomic_load(&instructions));
    if (begin) fprintf(stderr, "guest frame markers: %u/%u\n", starts, stops);
}
QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                          const qemu_info_t *info,
                                          int argc, char **argv) {
    (void)info;
    for (int i = 0; i < argc; i++) {
        if (!strncmp(argv[i], "begin=", 6)) begin = strtoull(argv[i] + 6, NULL, 0);
        else if (!strncmp(argv[i], "end=", 4)) end = strtoull(argv[i] + 4, NULL, 0);
        else return -1;
    }
    if ((begin == 0) != (end == 0)) return -1;
    atomic_store_explicit(&active, !begin, memory_order_relaxed);
    qemu_plugin_register_vcpu_tb_trans_cb(id, translate);
    qemu_plugin_register_atexit_cb(id, finish, NULL);
    return 0;
}
