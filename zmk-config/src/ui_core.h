/*
 * Portable renderer for the Corne LP OLED screen (no ZMK / LVGL dependencies),
 * so the exact same pixels can be previewed on a PC with tools/sim.c.
 *
 * Draws a 32 x 128 portrait frame (1 bit per pixel, row-major, MSB = left).
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define UI_W 32
#define UI_H 128
#define UI_STRIDE (UI_W / 8)

struct ui_state {
    uint8_t battery;        /* 0-100 */
    bool charging;          /* USB power present */
    bool central;           /* left half: shows layer + BT profile */
    const char *layer_name; /* central only, may be NULL */
    uint8_t layer_index;
    uint8_t profile;        /* BT profile 0-4 (central) */
    bool connected;         /* central: host connected, peripheral: linked to left */
    uint16_t wpm;
    uint32_t presses;       /* total key presses seen (hands alternate on each one) */
    uint32_t idle_ms;       /* time since the last key press */
    uint32_t now_ms;
};

void ui_render(uint8_t fb[UI_H * UI_STRIDE], const struct ui_state *s);
