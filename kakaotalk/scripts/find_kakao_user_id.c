#include <CommonCrypto/CommonDigest.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define DIGEST_LEN CC_SHA512_DIGEST_LENGTH

typedef struct {
    uint8_t target[DIGEST_LEN];
    uint64_t start;
    uint64_t end;
    uint64_t stride;
    uint64_t index;
    atomic_ullong *found;
    atomic_ullong *checked;
    atomic_ullong *done;
} worker_args_t;

static int hex_value(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static bool parse_hex_digest(const char *hex, uint8_t out[DIGEST_LEN]) {
    if (strlen(hex) != DIGEST_LEN * 2) return false;
    for (size_t i = 0; i < DIGEST_LEN; i++) {
        int high = hex_value(hex[i * 2]);
        int low = hex_value(hex[i * 2 + 1]);
        if (high < 0 || low < 0) return false;
        out[i] = (uint8_t)((high << 4) | low);
    }
    return true;
}

static int u64_to_ascii(uint64_t value, char buf[32]) {
    char tmp[32];
    int len = 0;
    if (value == 0) {
        buf[0] = '0';
        return 1;
    }
    while (value > 0) {
        tmp[len++] = (char)('0' + (value % 10));
        value /= 10;
    }
    for (int i = 0; i < len; i++) {
        buf[i] = tmp[len - i - 1];
    }
    return len;
}

static void *worker(void *raw) {
    worker_args_t *args = (worker_args_t *)raw;
    uint8_t digest[DIGEST_LEN];
    char text[32];
    uint64_t local_checked = 0;

    for (uint64_t value = args->start + args->index; value < args->end; value += args->stride) {
        if (atomic_load(args->found) != 0) break;
        int len = u64_to_ascii(value, text);
        CC_SHA512(text, (CC_LONG)len, digest);
        if (memcmp(digest, args->target, DIGEST_LEN) == 0) {
            atomic_store(args->found, value);
            break;
        }
        local_checked++;
        if ((local_checked & 0xFFFFF) == 0) {
            atomic_fetch_add(args->checked, 0x100000);
        }
    }
    atomic_fetch_add(args->checked, local_checked & 0xFFFFF);
    atomic_fetch_add(args->done, 1);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <sha512hex> [start] [end] [threads]\n", argv[0]);
        return 2;
    }

    uint8_t target[DIGEST_LEN];
    if (!parse_hex_digest(argv[1], target)) {
        fprintf(stderr, "invalid SHA-512 hex digest\n");
        return 2;
    }

    uint64_t start = argc > 2 ? strtoull(argv[2], NULL, 10) : 100000000ULL;
    uint64_t end = argc > 3 ? strtoull(argv[3], NULL, 10) : 10000000000ULL;
    uint64_t threads = argc > 4 ? strtoull(argv[4], NULL, 10) : 8ULL;
    if (threads < 1) threads = 1;
    if (threads > 64) threads = 64;

    pthread_t *handles = calloc((size_t)threads, sizeof(pthread_t));
    worker_args_t *args = calloc((size_t)threads, sizeof(worker_args_t));
    atomic_ullong found;
    atomic_ullong checked;
    atomic_ullong done;
    atomic_init(&found, 0);
    atomic_init(&checked, 0);
    atomic_init(&done, 0);

    time_t started = time(NULL);
    for (uint64_t i = 0; i < threads; i++) {
        memcpy(args[i].target, target, DIGEST_LEN);
        args[i].start = start;
        args[i].end = end;
        args[i].stride = threads;
        args[i].index = i;
        args[i].found = &found;
        args[i].checked = &checked;
        args[i].done = &done;
        pthread_create(&handles[i], NULL, worker, &args[i]);
    }

    while (atomic_load(&found) == 0 && atomic_load(&done) < threads) {
        sleep(10);
        uint64_t current = atomic_load(&checked);
        double elapsed = difftime(time(NULL), started);
        fprintf(stderr, "checked=%llu rate=%.0f/s\n", current, current / (elapsed > 0 ? elapsed : 1));
    }

    uint64_t result = atomic_load(&found);
    if (result != 0) {
        printf("%llu\n", result);
    }

    for (uint64_t i = 0; i < threads; i++) {
        if (handles[i]) pthread_join(handles[i], NULL);
    }
    free(handles);
    free(args);
    return result == 0 ? 1 : 0;
}
