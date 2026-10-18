/*
 * Host simulator: renders the real ui_core.c through a scripted typing session
 * and writes raw frames (left, right) to stdout for tools/preview.py.
 *
 *   cc -O2 -Isrc tools/sim.c src/ui_core.c -o sim && ./sim > frames.bin
 */
#include <stdio.h>
#include <string.h>
#include "ui_core.h"

/* wpm target over time (ms) */
static int target_wpm(int t) {
    if (t < 2500) return 0;
    if (t < 7000) return 45;
    if (t < 12500) return 115;
    if (t < 14500) return 60;
    return 0;
}

int main(void) {
    uint8_t fb[UI_H * UI_STRIDE];
    double acc = 0, wpm_s = 0;
    unsigned presses = 0, last_press = 0;
    const char *layers[] = {"BASE", "BASE", "NUM", "BASE"};
    for (int t = 0; t <= 30000; t += 100) {
        int tw = target_wpm(t);
        acc += tw * 5.0 / 60.0 * 0.1; /* key presses this frame */
        while (acc >= 1.0) {
            acc -= 1.0;
            presses++;
            last_press = t;
        }
        wpm_s = wpm_s * 0.85 + tw * 0.15;
        if (tw == 0 && t - last_press > 3000) wpm_s = 0;
        struct ui_state s = {
            .battery = 87, .charging = false, .central = true,
            .layer_name = layers[(t / 4000) % 4], .profile = 0, .connected = true,
            .wpm = (uint16_t)(wpm_s + 0.5), .presses = presses,
            .idle_ms = t - last_press + (presses ? 0 : 5000), .now_ms = t,
        };
        ui_render(fb, &s);
        fwrite(fb, 1, sizeof fb, stdout);
        s.central = false;
        s.battery = 64;
        ui_render(fb, &s);
        fwrite(fb, 1, sizeof fb, stdout);
    }
    return 0;
}
