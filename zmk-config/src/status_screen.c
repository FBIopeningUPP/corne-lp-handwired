/*
 * ZMK custom status screen for Corne LP: hooks ZMK state into ui_core and
 * pushes the portrait frame onto the 128x32 OLED, rotated.
 *
 * Both halves run this. Each half counts the key presses it sees:
 *   left  (central)    sees every key, so WPM is exact
 *   right (peripheral) sees only its own keys, so its WPM is doubled as an estimate
 */
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
#include <string.h>
#include <lvgl.h>

#include <zmk/display/status_screen.h>
#include <zmk/event_manager.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/battery.h>
#include <zmk/keymap.h>
#if IS_ENABLED(CONFIG_ZMK_USB)
#include <zmk/usb.h>
#endif
#if IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL) || !IS_ENABLED(CONFIG_ZMK_SPLIT)
#define IS_CENTRAL 1
#include <zmk/ble.h>
#else
#define IS_CENTRAL 0
#include <zmk/split/bluetooth/peripheral.h>
#endif

#include "ui_core.h"

#define LW 128
#define LH 32
#define WINDOW 30 /* 3 s of 100 ms buckets */

static lv_obj_t *canvas;
static uint8_t canvas_buf[LV_CANVAS_BUF_SIZE_ALPHA_1BIT(LW, LH)];
static uint8_t portrait[UI_H * UI_STRIDE];

static atomic_t presses;
static atomic_t last_press_ms;

static uint8_t buckets[WINDOW];
static uint8_t bucket_idx;
static uint32_t seen_presses;
static uint32_t bucket_t0;
static uint16_t wpm_smooth;

static int on_position(const zmk_event_t *eh) {
    const struct zmk_position_state_changed *ev = as_zmk_position_state_changed(eh);
    if (ev != NULL && ev->state) {
        atomic_inc(&presses);
        atomic_set(&last_press_ms, (atomic_val_t)k_uptime_get_32());
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(corne_lp_screen, on_position);
ZMK_SUBSCRIPTION(corne_lp_screen, zmk_position_state_changed);

static uint16_t update_wpm(uint32_t now) {
    uint32_t total = (uint32_t)atomic_get(&presses);
    /* advance one bucket per 100 ms, even if frames were skipped */
    while (now - bucket_t0 >= 100) {
        bucket_t0 += 100;
        bucket_idx = (bucket_idx + 1) % WINDOW;
        buckets[bucket_idx] = 0;
        if (now - bucket_t0 > 100 * WINDOW) {
            bucket_t0 = now;
            memset(buckets, 0, sizeof(buckets));
        }
    }
    uint32_t fresh = total - seen_presses;
    seen_presses = total;
    buckets[bucket_idx] = MIN(255, buckets[bucket_idx] + fresh);

    uint32_t sum = 0;
    for (int i = 0; i < WINDOW; i++) {
        sum += buckets[i];
    }
    /* presses in 3 s -> per minute, 5 presses per word */
    uint32_t wpm = sum * 4 * (IS_CENTRAL ? 1 : 2);
    wpm_smooth = (uint16_t)((wpm_smooth * 3 + wpm + 2) / 4);
    return wpm_smooth;
}

static void push_to_canvas(void) {
    memset(canvas_buf, 0, sizeof(canvas_buf));
    const int stride = (LW + 7) / 8;
    for (int py = 0; py < UI_H; py++) {
        for (int px = 0; px < UI_W; px++) {
            if (!(portrait[py * UI_STRIDE + (px >> 3)] & (0x80 >> (px & 7)))) {
                continue;
            }
#if IS_ENABLED(CONFIG_CORNE_LP_OLED_FLIP)
            int lx = LW - 1 - py, ly = px;
#else
            int lx = py, ly = LH - 1 - px;
#endif
            canvas_buf[ly * stride + (lx >> 3)] |= 0x80 >> (lx & 7);
        }
    }
    lv_obj_invalidate(canvas);
}

static void tick(lv_timer_t *timer) {
    ARG_UNUSED(timer);
    uint32_t now = k_uptime_get_32();
    uint32_t last = (uint32_t)atomic_get(&last_press_ms);
    uint32_t total = (uint32_t)atomic_get(&presses);

    struct ui_state s = {
        .battery = zmk_battery_state_of_charge(),
        .central = IS_CENTRAL,
        .wpm = update_wpm(now),
        .presses = total,
        .idle_ms = total ? now - last : now + 60000,
        .now_ms = now,
    };
#if IS_ENABLED(CONFIG_ZMK_USB)
    s.charging = zmk_usb_is_powered();
#endif
#if IS_CENTRAL
    zmk_keymap_layer_index_t idx = zmk_keymap_highest_layer_active();
    s.layer_index = idx;
    s.layer_name = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(idx));
#if IS_ENABLED(CONFIG_ZMK_BLE)
    s.profile = zmk_ble_active_profile_index();
    s.connected = zmk_ble_active_profile_is_connected();
#endif
#else
    s.connected = zmk_split_bt_peripheral_is_connected();
#endif

    ui_render(portrait, &s);
    push_to_canvas();
}

lv_obj_t *zmk_display_status_screen(void) {
    lv_obj_t *screen = lv_obj_create(NULL);

    canvas = lv_canvas_create(screen);
    lv_canvas_set_buffer(canvas, canvas_buf, LW, LH, LV_IMG_CF_ALPHA_1BIT);
    lv_obj_align(canvas, LV_ALIGN_TOP_LEFT, 0, 0);
    /* draw lit pixels in the theme's text colour, whatever the panel polarity is */
    lv_obj_set_style_img_recolor(canvas, lv_obj_get_style_text_color(screen, LV_PART_MAIN),
                                 LV_PART_MAIN);
    lv_obj_set_style_img_recolor_opa(canvas, LV_OPA_COVER, LV_PART_MAIN);

    bucket_t0 = k_uptime_get_32();
    tick(NULL);
    lv_timer_create(tick, 1000 / CONFIG_CORNE_LP_FPS, NULL);
    return screen;
}
