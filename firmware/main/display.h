#ifndef AETHER_DISPLAY_H
#define AETHER_DISPLAY_H

#include <stdbool.h>
#include <stdint.h>

/* Waveshare ESP32-S3-Touch-LCD-4.3B / 4.3B-BOX (BO):
 * 4.3″ IPS RGB 800×480, ST7262-class RGB panel, GT911 touch, CH422G expander. */
#define DISP_PANEL_W 800
#define DISP_PANEL_H 480
#define FACE_W 800
#define FACE_H 480

/* RGB565 helpers (host-endian; RGB panel takes native RGB565 — no SPI swap). */
#define RGB565(r, g, b)                                                        \
  ((uint16_t)((((r)&0xF8) << 8) | (((g)&0xFC) << 3) | (((b)&0xF8) >> 3)))

/* RGB panel + CH422G backlight + PSRAM face buffer. */
bool display_init(void);

/* Register LVGL display (RGB565, FACE_W×FACE_H) flush → RGB panel. */
bool display_lvgl_init(void);

/* Push logical RGB565 face to the panel (1:1, native endian). */
void display_present(const uint16_t *face_rgb565);

/* PSRAM logical face buffer (also used as LVGL full-frame draw buffer). */
uint16_t *display_face_buffer(void);

/* PSRAM RGB565 buffer for LVGL canvas (dial bezel). Caller owns lifetime. */
uint16_t *display_alloc_canvas(int w, int h);

/* Optional: sample GT911 outside LVGL. Prefer LVGL indev read_cb (used by
 * display_touch_lvgl_init) — do not also call this immediately before
 * lv_timer_handler or the second read empties the controller. */
void display_touch_poll(void);

/* Latest sample (non-destructive). */
bool display_touch_get(int *x, int *y, int *pressed);

/* Register LVGL pointer indev; samples GT911 inside the read callback. */
bool display_touch_lvgl_init(void);

#endif
