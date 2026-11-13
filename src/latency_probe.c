/* piStomp MIDI Latency Probe - SPDX-License-Identifier: GPL-3.0-only
 * Copyright (C) 2026 Ken Spanks
 * Audio input is copied directly to the left output.
 * The right output carries a losslessly decodable, fixed-length PCM packet
 * for each channel MIDI event, including its ORIGINAL audio-frame timestamp.
 * No memory allocation, disk I/O, locks or logging in run().
 */
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <lv2/core/lv2.h>
#include <lv2/atom/atom.h>
#include <lv2/atom/util.h>
#include <lv2/midi/midi.h>
#include <lv2/urid/urid.h>

#define PLUGIN_URI "https://github.com/tothoseofus/piStomp-MIDI-Latency-Probe"
#define QUEUE_CAPACITY 1024u
#define PACKET_SAMPLES 15u
#define PACKET_VERSION 1u

enum { PORT_AUDIO_IN = 0, PORT_MIDI_IN = 1, PORT_AUDIO_LEFT = 2, PORT_AUDIO_RIGHT = 3 };

typedef struct {
    uint64_t frame;          /* Original MIDI event timestamp in the LV2 sample clock */
    uint8_t status, data1, data2;
} MidiRecord;

typedef struct {
    const float *audio_in;
    const LV2_Atom_Sequence *midi_in;
    float *audio_left;
    float *audio_right;
    LV2_URID midi_urid;
    uint64_t frame_clock;
    MidiRecord queue[QUEUE_CAPACITY];
    uint32_t queue_head, queue_tail;
    uint8_t packet[PACKET_SAMPLES - 2u]; /* 13 encoded bytes between sync and end */
    uint8_t packet_index;
    bool packet_active;
    uint64_t dropped_events; /* Inspect via debugger; no RT logging */
} Probe;

static bool queue_push(Probe *p, MidiRecord r) {
    const uint32_t next = (p->queue_tail + 1u) % QUEUE_CAPACITY;
    if (next == p->queue_head) {
        ++p->dropped_events;
        return false;
    }
    p->queue[p->queue_tail] = r;
    p->queue_tail = next;
    return true;
}

static void packet_start(Probe *p, MidiRecord r) {
    p->packet[0] = PACKET_VERSION;
    p->packet[1] = r.status;
    p->packet[2] = r.data1;
    p->packet[3] = r.data2;
    uint8_t checksum = 0;
    for (uint32_t j = 0; j < 4; ++j) checksum ^= p->packet[j];
    for (uint32_t j = 0; j < 8; ++j) {
        const uint8_t b = (uint8_t)((r.frame >> (j * 8u)) & 0xFFu);
        p->packet[4u + j] = b;
        checksum ^= b;
    }
    p->packet[12] = checksum;
    p->packet_index = 0;
    p->packet_active = true;
}

static float packet_sample(Probe *p) {
    const uint32_t k = p->packet_index++;
    if (k == 0u) return -1.0f;                         /* Unambiguous sync */
    if (k <= 13u) return (float)(p->packet[k - 1u] + 1u) / 512.0f;
    p->packet_active = false;
    return -0.75f;                                     /* End marker */
}

static LV2_Handle instantiate(const LV2_Descriptor *descriptor, double rate,
                              const char *bundle_path, const LV2_Feature *const *features) {
    (void)descriptor; (void)rate; (void)bundle_path;
    const LV2_URID_Map *map = NULL;
    for (const LV2_Feature *const *f = features; f && *f; ++f) {
        if (!strcmp((*f)->URI, LV2_URID__map)) map = (const LV2_URID_Map *)(*f)->data;
    }
    if (!map) return NULL;
    Probe *p = (Probe *)calloc(1, sizeof(Probe));
    if (!p) return NULL;
    p->midi_urid = map->map(map->handle, LV2_MIDI__MidiEvent);
    return p;
}

static void connect_port(LV2_Handle handle, uint32_t port, void *data) {
    Probe *p = (Probe *)handle;
    switch (port) {
    case PORT_AUDIO_IN:    p->audio_in = (const float *)data; break;
    case PORT_MIDI_IN:     p->midi_in = (const LV2_Atom_Sequence *)data; break;
    case PORT_AUDIO_LEFT:  p->audio_left = (float *)data; break;
    case PORT_AUDIO_RIGHT: p->audio_right = (float *)data; break;
    default: break;
    }
}

static void run(LV2_Handle handle, uint32_t n_samples) {
    Probe *p = (Probe *)handle;
    if (!p->audio_left || !p->audio_right) return;

    /* The left-channel copy is sample-accurate: no lookahead or delay. */
    if (p->audio_in) {
        if (p->audio_left != p->audio_in)
            memmove(p->audio_left, p->audio_in, (size_t)n_samples * sizeof(float));
    } else {
        memset(p->audio_left, 0, (size_t)n_samples * sizeof(float));
    }
    memset(p->audio_right, 0, (size_t)n_samples * sizeof(float));

    /* MIDI events arrive ordered by frame offset in an LV2 Atom Sequence.
     * Store their original timestamps before any serialisation delay.
     */
    if (p->midi_in) {
        LV2_ATOM_SEQUENCE_FOREACH(p->midi_in, ev) {
            if (ev->body.type != p->midi_urid || ev->body.size < 1) continue;
            const uint8_t *bytes = (const uint8_t *)LV2_ATOM_BODY(&ev->body);
            const uint8_t status = bytes[0];
            if (status < 0x80u || status >= 0xF0u) continue;  /* channel voice only */
            const uint8_t type = status & 0xF0u;
            const uint32_t expected = (type == 0xC0u || type == 0xD0u) ? 2u : 3u;
            if (ev->body.size < expected) continue;
            const int64_t offset = ev->time.frames;
            const uint64_t frame = p->frame_clock +
                (offset < 0 ? 0u : (uint64_t)offset >= n_samples ? (n_samples ? n_samples - 1u : 0u) : (uint64_t)offset);
            const MidiRecord r = {frame, status, bytes[1], expected == 3u ? bytes[2] : 0u};
            queue_push(p, r);
        }
    }

    /* Fixed-size packets can span LV2 blocks. Each packet includes the
     * ORIGINAL timestamp, so even simultaneous messages remain sample-accurate
     * after decoding. No new packet begins before its actual event frame.
     */
    for (uint32_t i = 0; i < n_samples; ++i) {
        if (!p->packet_active && p->queue_head != p->queue_tail &&
            p->queue[p->queue_head].frame <= p->frame_clock + i) {
            packet_start(p, p->queue[p->queue_head]);
            p->queue_head = (p->queue_head + 1u) % QUEUE_CAPACITY;
        }
        if (p->packet_active) p->audio_right[i] = packet_sample(p);
    }
    p->frame_clock += n_samples;
}

static void cleanup(LV2_Handle handle) { free(handle); }
static const void *extension_data(const char *uri) { (void)uri; return NULL; }
static const LV2_Descriptor descriptor = {
    PLUGIN_URI, instantiate, connect_port, NULL, run, NULL, cleanup, extension_data
};
LV2_SYMBOL_EXPORT const LV2_Descriptor *lv2_descriptor(uint32_t index) {
    return index == 0 ? &descriptor : NULL;
}
