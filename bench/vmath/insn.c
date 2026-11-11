/* QEMU plugin: executed guest instructions, summed at translated-block entry.
 * These kernels have no guest faults or early exits inside translated blocks.
 * Build against the header belonging to the QEMU executable used for measurement.
 */
#include <qemu-plugin.h>
#include <inttypes.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;
static _Atomic uint64_t instructions;

static void execute(unsigned int cpu, void *count) {
    (void)cpu;
    atomic_fetch_add_explicit(&instructions, (uintptr_t)count, memory_order_relaxed);
}
static void translate(qemu_plugin_id_t id, struct qemu_plugin_tb *tb) {
    (void)id;
    qemu_plugin_register_vcpu_tb_exec_cb(tb, execute, QEMU_PLUGIN_CB_NO_REGS,
                                       (void *)(uintptr_t)qemu_plugin_tb_n_insns(tb));
}
static void finish(qemu_plugin_id_t id, void *unused) {
    (void)id;
    (void)unused;
    fprintf(stderr, "guest instructions: %" PRIu64 "\n", atomic_load(&instructions));
}
QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                          const qemu_info_t *info,
                                          int argc, char **argv) {
    (void)info;
    (void)argc;
    (void)argv;
    qemu_plugin_register_vcpu_tb_trans_cb(id, translate);
    qemu_plugin_register_atexit_cb(id, finish, NULL);
    return 0;
}
