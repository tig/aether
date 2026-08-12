/* Element: aux RPM / TPS — real outline fonts (LVGL labels). */
#include "face_aux.h"

#include "display.h"
#include "fonts/aether_fonts.h"

#include <stdio.h>

static lv_obj_t *s_rpm;
static lv_obj_t *s_tps;
static int s_last_rpm = -1;
static int s_last_tps = -1;
static int s_last_flash = -1;

void face_aux_init(lv_obj_t *parent) {
  /* Aux band sits under dial; leave room for chrome captions at bottom. */
  const int y = FACE_AUX_Y0 + 4;

  s_rpm = lv_label_create(parent);
  lv_obj_set_style_text_font(s_rpm, &font_aether_aux_64, 0);
  lv_obj_set_style_text_color(s_rpm, lv_color_make(240, 240, 245), 0);
  lv_label_set_text(s_rpm, "0");
  lv_obj_align(s_rpm, LV_ALIGN_TOP_LEFT, 40, y);

  s_tps = lv_label_create(parent);
  lv_obj_set_style_text_font(s_tps, &font_aether_aux_64, 0);
  lv_obj_set_style_text_color(s_tps, lv_color_make(240, 240, 245), 0);
  lv_label_set_text(s_tps, "0%");
  lv_obj_align(s_tps, LV_ALIGN_TOP_RIGHT, -40, y);
}

void face_aux_update(const face_state_t *st) {
  if (!st || !s_rpm || !s_tps) {
    return;
  }
  int flash = 0;
  if (st->redline_warn) {
    flash = (int)((lv_tick_get() / 120) & 1u);
  }
  if (st->rpm == s_last_rpm && st->tps == s_last_tps && flash == s_last_flash &&
      !st->redline_warn) {
    return;
  }

  char rbuf[16];
  int rpm = st->rpm;
  if (rpm < 0) {
    rpm = 0;
  }
  snprintf(rbuf, sizeof rbuf, "%d", rpm);
  lv_label_set_text(s_rpm, rbuf);
  if (st->redline_warn && flash) {
    lv_obj_set_style_text_color(s_rpm, lv_color_make(255, 50, 50), 0);
  } else {
    lv_obj_set_style_text_color(s_rpm, lv_color_make(240, 240, 245), 0);
  }

  char tbuf[16];
  if (st->tps >= 100) {
    snprintf(tbuf, sizeof tbuf, "WOT");
    lv_obj_set_style_text_color(s_tps, lv_color_make(60, 140, 255), 0);
  } else {
    int t = st->tps;
    if (t < 0) {
      t = 0;
    }
    if (t > 99) {
      t = 99;
    }
    snprintf(tbuf, sizeof tbuf, "%d%%", t);
    lv_obj_set_style_text_color(s_tps, lv_color_make(240, 240, 245), 0);
  }
  lv_label_set_text(s_tps, tbuf);
  /* Re-align right after text length changes. */
  lv_obj_align(s_tps, LV_ALIGN_TOP_RIGHT, -40, FACE_AUX_Y0 + 4);
  lv_obj_align(s_rpm, LV_ALIGN_TOP_LEFT, 40, FACE_AUX_Y0 + 4);

  s_last_rpm = st->rpm;
  s_last_tps = st->tps;
  s_last_flash = flash;
}
