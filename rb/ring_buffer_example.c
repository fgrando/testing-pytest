/*
 * Ring buffer with batch push/pop.
 * Two implementations of the copy step are shown:
 *   1) memcpy-based  (RB_USE_MEMCPY = 1)
 *   2) manual word-copy fallback, for environments without memcpy
 *
 * MISRA-ish notes:
 *  - no dynamic allocation; caller owns the backing buffer
 *  - fixed-width uint32_t for all indices/lengths, no size_t
 *  - explicit casts where a fixed-width value crosses into a
 *    size_t-typed API (memcpy), no implicit signed/unsigned mixing
 *  - return value reports bytes actually moved (short push/pop allowed)
 */

#include <stddef.h>
#include <stdint.h>

#ifndef RB_USE_MEMCPY
#define RB_USE_MEMCPY 1
#endif

#if RB_USE_MEMCPY
#include <string.h>
#endif

typedef struct {
    uint8_t  *buffer;
    uint32_t  capacity;
    uint32_t  head;   /* next write index */
    uint32_t  tail;   /* next read index */
    uint32_t  count;  /* bytes currently stored */
} ring_buffer_t;

/**
 * @brief Initialize a ring buffer over caller-owned storage.
 *
 * @param rb       Ring buffer instance to initialize.
 * @param storage  Backing array, owned and allocated by the caller.
 *                 Must remain valid for the lifetime of rb.
 * @param capacity Size of storage in bytes.
 */
void ring_buffer_init(ring_buffer_t *rb, uint8_t *storage, uint32_t capacity)
{
    rb->buffer   = storage;
    rb->capacity = capacity;
    rb->head     = 0U;
    rb->tail     = 0U;
    rb->count    = 0U;
}

/**
 * @brief Get the number of free bytes available to push.
 *
 * @param rb Ring buffer instance.
 * @return   Free space in bytes (capacity - count).
 */
uint32_t ring_buffer_free_space(const ring_buffer_t *rb)
{
    return rb->capacity - rb->count;
}

/**
 * @brief Get the number of bytes currently stored, available to pop.
 *
 * @param rb Ring buffer instance.
 * @return   Bytes currently stored.
 */
uint32_t ring_buffer_used_space(const ring_buffer_t *rb)
{
    return rb->count;
}

/* ---- copy primitive: swap bodies depending on what's available ---- */

/**
 * @brief Internal copy primitive used by push/pop for each contiguous
 *        segment (at most 2 calls per push/pop, split at wrap-around).
 *
 * @param dst Destination address.
 * @param src Source address.
 * @param len Number of bytes to copy.
 */
static void rb_copy(uint8_t *dst, const uint8_t *src, uint32_t len)
{
#if RB_USE_MEMCPY
    (void)memcpy(dst, src, (size_t)len); /* memcpy's size arg is size_t by definition */
#else
    /* Manual word-at-a-time copy, byte remainder handled separately.
     * Assumes dst/src may be unaligned relative to each other, so we
     * only take the fast path when BOTH are aligned to the word size. */
    const uint32_t word_size = (uint32_t)sizeof(uint32_t);
    uint32_t       i         = 0U;

    if ((((uintptr_t)dst % word_size) == 0U) &&
        (((uintptr_t)src % word_size) == 0U)) {
        uint32_t       words  = len / word_size;
        const uint32_t *s_word = (const uint32_t *)(const void *)src;
        uint32_t       *d_word = (uint32_t *)(void *)dst;

        for (i = 0U; i < words; i++) {
            d_word[i] = s_word[i];
        }
        i *= word_size;
    }

    for (; i < len; i++) {
        dst[i] = src[i];
    }
#endif
}

/* ---- push/pop, handling wrap-around with at most two copy calls ---- */

/**
 * @brief Push up to len bytes into the buffer. Partial writes allowed:
 *        if free space is less than len, only what fits is copied.
 *        Call ring_buffer_free_space() beforehand to know ahead of time
 *        whether the full write will fit.
 *
 * @param rb   Ring buffer instance.
 * @param data Source bytes to copy in.
 * @param len  Number of bytes requested to push.
 * @return     Number of bytes actually copied (0 to len).
 */
uint32_t ring_buffer_push_bytes(ring_buffer_t *rb, const uint8_t *data, uint32_t len)
{
    uint32_t free_space = ring_buffer_free_space(rb);
    uint32_t to_copy     = (len < free_space) ? len : free_space;
    uint32_t tail_room   = rb->capacity - rb->head; /* space to end of buffer */

    if (to_copy <= tail_room) {
        rb_copy(&rb->buffer[rb->head], data, to_copy);
    } else {
        rb_copy(&rb->buffer[rb->head], data, tail_room);
        rb_copy(&rb->buffer[0], data + tail_room, to_copy - tail_room);
    }

    rb->head   = (rb->head + to_copy) % rb->capacity;
    rb->count += to_copy;

    /* Partial write allowed: return value may be < len. Caller can
     * call ring_buffer_free_space() beforehand to know ahead of time
     * whether the full write will fit. */
    return to_copy;
}

/**
 * @brief Pop up to len bytes out of the buffer. Partial reads allowed:
 *        if fewer than len bytes are stored, only what's available
 *        is copied out.
 *
 * @param rb   Ring buffer instance.
 * @param data Destination buffer to copy into. Must hold at least len bytes.
 * @param len  Number of bytes requested to pop.
 * @return     Number of bytes actually copied (0 to len).
 */
uint32_t ring_buffer_pop_bytes(ring_buffer_t *rb, uint8_t *data, uint32_t len)
{
    uint32_t to_copy   = (len < rb->count) ? len : rb->count;
    uint32_t tail_room = rb->capacity - rb->tail;

    if (to_copy <= tail_room) {
        rb_copy(data, &rb->buffer[rb->tail], to_copy);
    } else {
        rb_copy(data, &rb->buffer[rb->tail], tail_room);
        rb_copy(data + tail_room, &rb->buffer[0], to_copy - tail_room);
    }

    rb->tail   = (rb->tail + to_copy) % rb->capacity;
    rb->count -= to_copy;

    return to_copy; /* may be < len if buffer didn't have that much data */
}

/* ==================================================================
 * Test harness (host-only). Not part of the embedded/freestanding
 * build - uses stdio, only meant to run on a host during development.
 *
 * Build/run against each copy path:
 *   gcc -DRB_USE_MEMCPY=1 -Wall -Wextra ring_buffer_example.c -o rb_memcpy && ./rb_memcpy
 *   gcc -DRB_USE_MEMCPY=0 -Wall -Wextra ring_buffer_example.c -o rb_fallback && ./rb_fallback
 * ================================================================== */

#include <stdio.h>
#if !RB_USE_MEMCPY
#include <string.h> /* memcmp used by tests either way */
#endif

static int g_pass = 0;
static int g_fail = 0;

#define RB_CHECK(cond, desc)                                   \
    do {                                                       \
        if (cond) {                                            \
            g_pass++;                                          \
            printf("[PASS] %s\n", desc);                       \
        } else {                                               \
            g_fail++;                                          \
            printf("[FAIL] %s (line %d)\n", desc, __LINE__);   \
        }                                                       \
    } while (0)

static void test_basic_push_pop(void)
{
    uint8_t storage[8];
    ring_buffer_t rb;
    uint8_t in[4]  = { 'A', 'B', 'C', 'D' };
    uint8_t out[4];

    ring_buffer_init(&rb, storage, 8U);

    RB_CHECK(ring_buffer_push_bytes(&rb, in, 4U) == 4U, "basic: push of 4 bytes returns 4");
    RB_CHECK(ring_buffer_used_space(&rb) == 4U, "basic: used_space reflects push");
    RB_CHECK(ring_buffer_free_space(&rb) == 4U, "basic: free_space reflects push");

    RB_CHECK(ring_buffer_pop_bytes(&rb, out, 4U) == 4U, "basic: pop of 4 bytes returns 4");
    RB_CHECK(memcmp(out, in, 4U) == 0, "basic: popped bytes match pushed bytes");
    RB_CHECK(ring_buffer_used_space(&rb) == 0U, "basic: used_space is 0 after full drain");
}

static void test_wraparound_push(void)
{
    uint8_t storage[8];
    ring_buffer_t rb;
    uint8_t seed[6]     = { 'A', 'B', 'C', 'D', 'E', 'F' };
    uint8_t drain[2];
    uint8_t new_data[4] = { 0xAAU, 0xBBU, 0xCCU, 0xDDU };
    uint8_t out[8];
    uint8_t expected[8] = { 'C', 'D', 'E', 'F', 0xAAU, 0xBBU, 0xCCU, 0xDDU };

    ring_buffer_init(&rb, storage, 8U);

    RB_CHECK(ring_buffer_push_bytes(&rb, seed, 6U) == 6U, "wrap-push: seed fills slots 0-5");
    RB_CHECK(ring_buffer_pop_bytes(&rb, drain, 2U) == 2U, "wrap-push: drain advances tail to 2");
    RB_CHECK(rb.head == 6U && rb.tail == 2U && rb.count == 4U,
             "wrap-push: state is head=6 tail=2 count=4 before the wrapping push");

    RB_CHECK(ring_buffer_push_bytes(&rb, new_data, 4U) == 4U,
             "wrap-push: push of 4 splits across the end of the buffer");
    RB_CHECK(rb.count == 8U, "wrap-push: buffer is now full");
    RB_CHECK(ring_buffer_free_space(&rb) == 0U, "wrap-push: free_space is 0 when full");

    RB_CHECK(ring_buffer_pop_bytes(&rb, out, 8U) == 8U, "wrap-push: pop all 8 bytes back out");
    RB_CHECK(memcmp(out, expected, 8U) == 0,
             "wrap-push: popped order matches C,D,E,F,AA,BB,CC,DD");
}

static void test_wraparound_pop(void)
{
    uint8_t storage[8];
    ring_buffer_t rb;
    uint8_t fill_a[6]   = { 1, 2, 3, 4, 5, 6 };
    uint8_t drain[2];
    uint8_t fill_b[4]   = { 7, 8, 9, 10 };
    uint8_t out[7];
    uint8_t expected[7] = { 3, 4, 5, 6, 7, 8, 9 };

    ring_buffer_init(&rb, storage, 8U);

    (void)ring_buffer_push_bytes(&rb, fill_a, 6U);
    (void)ring_buffer_pop_bytes(&rb, drain, 2U);   /* tail -> 2, head -> 6, count -> 4 */
    (void)ring_buffer_push_bytes(&rb, fill_b, 4U); /* wraps head back to 2, count -> 8 */

    RB_CHECK(rb.tail == 2U && rb.head == 2U && rb.count == 8U,
             "wrap-pop: buffer full, head==tail==2 (unambiguous via count)");

    RB_CHECK(ring_buffer_pop_bytes(&rb, out, 7U) == 7U,
             "wrap-pop: pop of 7 splits across the end of the buffer");
    RB_CHECK(memcmp(out, expected, 7U) == 0,
             "wrap-pop: popped order matches 3,4,5,6,7,8,9");
    RB_CHECK(rb.tail == 1U, "wrap-pop: tail wraps to index 1 = (2+7) % 8");
    RB_CHECK(rb.count == 1U, "wrap-pop: one byte remains in the buffer");
}

static void test_full_buffer_partial_push(void)
{
    uint8_t storage[4];
    ring_buffer_t rb;
    uint8_t fill[4]         = { 1, 2, 3, 4 };
    uint8_t extra[5]        = { 9, 9, 9, 9, 9 };
    uint8_t partial_fill[3] = { 1, 2, 3 };

    ring_buffer_init(&rb, storage, 4U);
    RB_CHECK(ring_buffer_push_bytes(&rb, fill, 4U) == 4U, "full-push: fills buffer completely");
    RB_CHECK(ring_buffer_push_bytes(&rb, extra, 5U) == 0U,
             "full-push: push into an already-full buffer returns 0");
    RB_CHECK(rb.count == 4U, "full-push: count unchanged after rejected push");

    ring_buffer_init(&rb, storage, 4U);
    RB_CHECK(ring_buffer_push_bytes(&rb, partial_fill, 3U) == 3U,
             "full-push: partial fill leaves 1 byte free");
    RB_CHECK(ring_buffer_push_bytes(&rb, extra, 5U) == 1U,
             "full-push: request bigger than free_space returns only what fits");
    RB_CHECK(rb.count == 4U, "full-push: buffer now full after the partial write");
}

static void test_empty_buffer_partial_pop(void)
{
    uint8_t storage[4];
    ring_buffer_t rb;
    uint8_t out[5];
    uint8_t fill[3] = { 1, 2, 3 };

    ring_buffer_init(&rb, storage, 4U);
    RB_CHECK(ring_buffer_pop_bytes(&rb, out, 5U) == 0U, "empty-pop: pop from an empty buffer returns 0");

    (void)ring_buffer_push_bytes(&rb, fill, 3U);
    RB_CHECK(ring_buffer_pop_bytes(&rb, out, 5U) == 3U,
             "empty-pop: request bigger than used_space returns only what's stored");
    RB_CHECK(rb.count == 0U, "empty-pop: buffer is empty after the partial pop drains it");
}

static void test_head_tail_ambiguity(void)
{
    uint8_t storage[4];
    ring_buffer_t rb;
    uint8_t fill[4] = { 1, 2, 3, 4 };

    ring_buffer_init(&rb, storage, 4U);
    RB_CHECK(rb.head == rb.tail && rb.count == 0U, "ambiguity: head==tail on init means empty");
    RB_CHECK(ring_buffer_free_space(&rb) == 4U, "ambiguity: free_space is full capacity when empty");

    (void)ring_buffer_push_bytes(&rb, fill, 4U);
    RB_CHECK(rb.head == rb.tail && rb.count == 4U,
             "ambiguity: head==tail after wrapping full push means full, not empty");
    RB_CHECK(ring_buffer_free_space(&rb) == 0U,
             "ambiguity: free_space is 0 when full, despite head==tail");
}

static void test_zero_length_push_pop(void)
{
    uint8_t storage[4];
    ring_buffer_t rb;
    uint8_t dummy[1] = { 0xFFU };

    ring_buffer_init(&rb, storage, 4U);

    RB_CHECK(ring_buffer_push_bytes(&rb, dummy, 0U) == 0U, "zero-len: push of 0 bytes returns 0");
    RB_CHECK(rb.count == 0U, "zero-len: push of 0 bytes leaves count unchanged");

    RB_CHECK(ring_buffer_pop_bytes(&rb, dummy, 0U) == 0U, "zero-len: pop of 0 bytes returns 0");
    RB_CHECK(rb.count == 0U, "zero-len: pop of 0 bytes leaves count unchanged");
}

static void test_push_exceeds_capacity(void)
{
    uint8_t storage[4];
    ring_buffer_t rb;
    uint8_t big[10] = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };

    ring_buffer_init(&rb, storage, 4U);

    RB_CHECK(ring_buffer_push_bytes(&rb, big, 10U) == 4U,
             "oversize-push: request bigger than capacity copies only capacity bytes");
    RB_CHECK(memcmp(storage, big, 4U) == 0,
             "oversize-push: first 4 requested bytes copied, rest silently dropped");
}

int main(void)
{
    test_basic_push_pop();
    test_wraparound_push();
    test_wraparound_pop();
    test_full_buffer_partial_push();
    test_empty_buffer_partial_pop();
    test_head_tail_ambiguity();
    test_zero_length_push_pop();
    test_push_exceeds_capacity();

    printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
