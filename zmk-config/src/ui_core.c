/*
 * Corne LP OLED renderer.
 *
 *  y   0..4   battery icon + percent
 *  y   7..11  layer name + BT profile (left) / "LINK" status (right)
 *  y  14      divider
 *  y  16..73  spark field: sparks fly up off Blip's antenna, faster and denser
 *             as you type faster; above 70 WPM a flame crown flickers on top
 *  y  75..117 Blip the robot typing (hands swap on every key press)
 *  y 118..127 WPM in big digits
 */
#include <string.h>
#include "ui_core.h"
#include "sprites.h"

#define SPARK_TOP 16
#define SPARK_BOTTOM 73
#define BLIP_Y 75
#define WPM_Y 119 /* digits are drawn from WPM_Y - 1 */
#define MAX_SPARKS 28
#define FAST_WPM 70
#define SLEEP_MS 12000
#define TYPING_MS 900

static uint8_t *fbuf;

static inline void px(int x, int y, int on) {
    if (x < 0 || x >= UI_W || y < 0 || y >= UI_H) {
        return;
    }
    uint8_t m = 0x80 >> (x & 7);
    if (on) {
        fbuf[y * UI_STRIDE + (x >> 3)] |= m;
    } else {
        fbuf[y * UI_STRIDE + (x >> 3)] &= ~m;
    }
}

static void rect(int x0, int y0, int x1, int y1, int on) {
    for (int y = y0; y <= y1; y++) {
        for (int x = x0; x <= x1; x++) {
            px(x, y, on);
        }
    }
}

static void frame(int x0, int y0, int x1, int y1) {
    for (int x = x0; x <= x1; x++) {
        px(x, y0, 1);
        px(x, y1, 1);
    }
    for (int y = y0; y <= y1; y++) {
        px(x0, y, 1);
        px(x1, y, 1);
    }
}

static uint16_t glyph_bits(char c) {
    if (c >= 'a' && c <= 'z') {
        c -= 32;
    }
    for (unsigned i = 0; i < sizeof(font3x5) / sizeof(font3x5[0]); i++) {
        if (font3x5[i].c == c) {
            return font3x5[i].bits;
        }
    }
    return 0x7fff & 0x5555; /* unknown: checker */
}

/* draws a 3x5 glyph scaled by `s`, returns advance */
static int glyph(int x, int y, char c, int s) {
    uint16_t b = glyph_bits(c);
    for (int r = 0; r < 5; r++) {
        for (int col = 0; col < 3; col++) {
            if (b & (1 << (14 - (r * 3 + col)))) {
                rect(x + col * s, y + r * s, x + col * s + s - 1, y + r * s + s - 1, 1);
            }
        }
    }
    return 4 * s;
}

static int text(int x, int y, const char *t, int s, int max_chars) {
    for (int i = 0; t[i] && i < max_chars; i++) {
        x += glyph(x, y, t[i], s);
    }
    return x;
}

static int num_to_str(char *buf, unsigned v) {
    char tmp[6];
    int n = 0;
    do {
        tmp[n++] = '0' + v % 10;
        v /= 10;
    } while (v && n < 5);
    for (int i = 0; i < n; i++) {
        buf[i] = tmp[n - 1 - i];
    }
    buf[n] = 0;
    return n;
}

static void blit_sprite(const uint8_t *spr, int oy) {
    for (int y = 0; y < SPRITE_H; y++) {
        for (int bx = 0; bx < UI_STRIDE; bx++) {
            fbuf[(oy + y) * UI_STRIDE + bx] |= spr[y * UI_STRIDE + bx];
        }
    }
}

/* ---------- tiny deterministic PRNG ---------- */
static uint32_t rng = 0x1234567;
static uint32_t rnd(void) {
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return rng;
}

/* ---------- sparks ---------- */
struct spark {
    int16_t x, y;   /* 8.8 fixed point */
    int16_t vx, vy; /* per frame */
    uint8_t life;
    uint8_t big;
};
static struct spark sparks[MAX_SPARKS];
static uint32_t last_ms;
static uint32_t spawn_acc;

static void update_sparks(const struct ui_state *s, int dt) {
    /* spawn: about wpm/12 sparks per second */
    spawn_acc += (uint32_t)s->wpm * dt;
    while (spawn_acc >= 12000) {
        spawn_acc -= 12000;
        for (int i = 0; i < MAX_SPARKS; i++) {
            if (!sparks[i].life) {
                int speed = 40 + s->wpm * 2 + (rnd() % 40); /* px/s * 256 / 1000 */
                sparks[i].x = (15 + (int)(rnd() % 3)) << 8;
                sparks[i].y = (BLIP_Y - 1) << 8;
                sparks[i].vx = (int)(rnd() % 161) - 80;
                sparks[i].vy = -speed;
                sparks[i].life = 255;
                sparks[i].big = (s->wpm > FAST_WPM) && (rnd() % 3 == 0);
                break;
            }
        }
    }
    for (int i = 0; i < MAX_SPARKS; i++) {
        struct spark *p = &sparks[i];
        if (!p->life) {
            continue;
        }
        p->x += p->vx * dt / 100;
        p->y += p->vy * dt / 100;
        p->vx += ((int)(rnd() % 41) - 20); /* wobble */
        int y = p->y >> 8;
        if (y < SPARK_TOP || (p->x >> 8) < 0 || (p->x >> 8) >= UI_W) {
            p->life = 0;
        }
    }
}

static void draw_sparks(void) {
    for (int i = 0; i < MAX_SPARKS; i++) {
        struct spark *p = &sparks[i];
        if (!p->life) {
            continue;
        }
        int x = p->x >> 8, y = p->y >> 8;
        if (y > SPARK_BOTTOM) {
            continue;
        }
        px(x, y, 1);
        if (p->big) {
            px(x + 1, y, 1);
            px(x, y + 1, 1);
            px(x + 1, y + 1, 1);
        } else if ((rnd() & 3) == 0) {
            px(x, y + 1, 1); /* short trail */
        }
    }
}

/* background stars that slowly twinkle, so the field is never empty */
static void draw_stars(uint32_t now) {
    static const uint8_t star[][2] = {{3, 20}, {27, 24}, {8, 33}, {24, 41}, {4, 52},
                                      {28, 58}, {12, 63}, {21, 70}, {2, 72}, {29, 18}};
    for (unsigned i = 0; i < sizeof(star) / 2; i++) {
        uint32_t phase = (now / 160 + i * 7) % 20;
        if (phase < 15) {
            px(star[i][0], star[i][1], 1);
        }
        if (phase == 0) { /* twinkle cross */
            px(star[i][0] - 1, star[i][1], 1);
            px(star[i][0] + 1, star[i][1], 1);
            px(star[i][0], star[i][1] - 1, 1);
            px(star[i][0], star[i][1] + 1, 1);
        }
    }
}

/* one teardrop layer of the flame; widest about a quarter of the way up */
static void flame_layer(int h, int maxw, int sway, int on, int y0) {
    for (int dy = 0; dy < h; dy++) {
        int t = (dy * 4 < h) ? maxw * (dy + 2) * 4 / (h + 8) : maxw * (h - dy) * 4 / (3 * h);
        if (t > maxw) {
            t = maxw;
        }
        int cx = 16 + sway * dy / h + ((rnd() % 6) == 0 ? (int)(rnd() % 3) - 1 : 0);
        for (int x = cx - t; x <= cx + t; x++) {
            px(x, y0 - dy, on);
        }
    }
}

/* flame crown above the head when typing fast; height follows WPM */
static void draw_flame(const struct ui_state *s) {
    int h = 10 + (s->wpm - FAST_WPM) / 3;
    if (h > 30) {
        h = 30;
    }
    h += (int)(rnd() % 3) - 1; /* flicker */
    int sway = (int)((s->now_ms / 140) % 5) - 2;
    flame_layer(h, 8, sway, 1, BLIP_Y - 1);
    flame_layer(h * 6 / 10, 5, sway, 0, BLIP_Y - 1);
    flame_layer(h * 3 / 10, 2, sway / 2, 1, BLIP_Y - 1);
}

static void draw_battery(const struct ui_state *s) {
    frame(0, 0, 9, 4);
    rect(10, 1, 10, 3, 1);
    int fill = (s->battery * 8 + 50) / 100;
    if (fill > 0) {
        rect(1, 1, fill, 3, 1);
    }
    if (s->charging) { /* bolt: punch it out of the fill */
        rect(1, 1, 8, 3, 1);
        px(4, 1, 0);
        px(5, 1, 0);
        px(3, 2, 0);
        px(4, 2, 0);
        px(5, 2, 0);
        px(6, 2, 0);
        px(4, 3, 0);
        px(5, 3, 0);
    }
    char buf[6];
    int n = num_to_str(buf, s->battery > 100 ? 100 : s->battery);
    int x = UI_W - n * 4 + 1;
    text(x, 0, buf, 1, 3);
}

static void draw_status(const struct ui_state *s) {
    if (s->central) {
        char name[8];
        if (s->layer_name && s->layer_name[0]) {
            strncpy(name, s->layer_name, 5);
            name[5] = 0;
        } else {
            name[0] = 'L';
            num_to_str(name + 1, s->layer_index);
        }
        text(0, 7, name, 1, 5);
        /* BT profile box: filled = connected */
        char p[2] = {(char)('1' + s->profile), 0};
        if (s->connected) {
            rect(25, 6, 31, 12, 1);
            int x = 27;
            uint16_t b = glyph_bits(p[0]);
            for (int r = 0; r < 5; r++)
                for (int c = 0; c < 3; c++)
                    if (b & (1 << (14 - (r * 3 + c))))
                        px(x + c, 7 + r, 0);
        } else {
            frame(25, 6, 31, 12);
            text(27, 7, p, 1, 1);
        }
    } else {
        text(0, 7, "R", 1, 1);
        if (s->connected) {
            text(12, 7, "LINK", 1, 4);
        } else if ((s->now_ms / 500) & 1) {
            text(12, 7, "----", 1, 4);
        }
    }
    for (int x = 0; x < UI_W; x += 2) {
        px(x, 14, 1);
    }
}

static void draw_zz(uint32_t now) {
    /* three Z's drifting up and right, staggered */
    for (int i = 0; i < 3; i++) {
        uint32_t t = (now / 90 + i * 14) % 42;
        int y = BLIP_Y - 2 - (int)t;
        int x = 18 + (int)t / 6 + i;
        if (y > SPARK_TOP + 2) {
            glyph(x, y, 'Z', (t > 24 && i == 0) ? 2 : 1);
        }
    }
}

static void draw_wpm(const struct ui_state *s) {
    char buf[6];
    int n = num_to_str(buf, s->wpm > 999 ? 999 : s->wpm);
    int w = n * 8 - 2;
    text((UI_W - w) / 2, WPM_Y - 1, buf, 2, 3);
}

void ui_render(uint8_t fb[UI_H * UI_STRIDE], const struct ui_state *s) {
    fbuf = fb;
    memset(fb, 0, UI_H * UI_STRIDE);
    rng ^= s->now_ms * 2654435761u | 1;

    int dt = (int)(s->now_ms - last_ms);
    if (dt < 0 || dt > 500) {
        dt = 100;
    }
    last_ms = s->now_ms;

    bool sleeping = s->idle_ms > SLEEP_MS;
    bool typing = s->idle_ms < TYPING_MS && s->wpm > 0;
    bool fast = typing && s->wpm >= FAST_WPM;

    draw_battery(s);
    draw_status(s);

    if (!sleeping) {
        update_sparks(s, dt);
        draw_stars(s->now_ms);
        if (fast) {
            draw_flame(s);
        }
        draw_sparks();
    } else {
        draw_zz(s->now_ms);
    }

    enum blip_frame f;
    if (sleeping) {
        f = BLIP_SLEEP;
    } else if (typing) {
        bool a = s->presses & 1;
        f = fast ? (a ? BLIP_FAST_A : BLIP_FAST_B) : (a ? BLIP_TYPE_A : BLIP_TYPE_B);
    } else {
        f = ((s->now_ms / 100) % 35 < 2) ? BLIP_BLINK : BLIP_IDLE;
    }
    int bob = (!typing && !sleeping && (s->now_ms / 600) % 2) ? 1 : 0; /* idle breathing */
    blit_sprite(blip_frames[f], BLIP_Y + bob);

    draw_wpm(s);
}
