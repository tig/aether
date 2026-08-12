/* Element: primary mixture value + unit — real outline fonts (LVGL labels).
 * Owns the dial aperture; unit is a separate label with a clear gap.
 */
#include "face_primary.h"

#include "afr_map.h"
#include "display.h"
#include "fonts/aether_fonts.h"

#include <math.h>
#include <stdio.h>

static lv_obj_t *s_row;
static lv_obj_t *s_num;
static lv_obj_t *s_unit;
static int s_last_valid = -1;
static int s_last_lambda = -1;
static float s_last_afr = -999.f;

static lv_color_t color_from_rgb565(uint16_t c) {
  /* RGB565 → 8-bit channels (match LVGL RGB order). */
  uint8_t r = (uint8_t)(((c >> 11) & 0x1F) * 255 / 31);
  uint8_t g = (uint8_t)(((c >> 5) & 0x3F) * 255 / 63);
  uint8_t b = (uint8_t)((c & 0x1F) * 255 / 31);
  return lv_color_make(r, g, b);
}

void face_primary_init(lv_obj_t *parent) {
  /* Transparent flex row: number + unit, centered in dial aperture. */
  s_row = lv_obj_create(parent);
  lv_obj_remove_style_all(s_row);
  lv_obj_set_size(s_row, FACE_W - 200, 140);
  lv_obj_set_style_bg_opa(s_row, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(s_row, 0, 0);
  lv_obj_set_style_pad_all(s_row, 0, 0);
  lv_obj_set_style_pad_column(s_row, 24, 0); /* clear gap number ↔ unit */
  lv_obj_set_flex_flow(s_row, LV_FLEX_FLOW_ROW);
  lv_obj_set_flex_align(s_row, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER,
                        LV_FLEX_ALIGN_CENTER);
  lv_obj_clear_flag(s_row, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_clear_flag(s_row, LV_OBJ_FLAG_CLICKABLE); /* decorative; swipe through */
  /* Vertically center in dial; slight bias down (instrument bias). */
  lv_obj_set_pos(s_row, 100, FACE_DIAL_Y0 + FACE_DIAL_H / 2 - 70 + 8);

  s_num = lv_label_create(s_row);
  lv_obj_set_style_text_font(s_num, &font_aether_primary_112, 0);
  lv_obj_set_style_text_color(s_num, lv_color_white(), 0);
  lv_label_set_text(s_num, "14.7");

  s_unit = lv_label_create(s_row);
  lv_obj_set_style_text_font(s_unit, &font_aether_unit_36, 0);
  lv_obj_set_style_text_color(s_unit, lv_color_white(), 0);
  lv_label_set_text(s_unit, "AFR");
}

void face_primary_update(const face_state_t *st) {
  if (!st || !s_num || !s_unit) {
    return;
  }
  /* Lambda needs finer dirty threshold (2 dp). */
  float afr_eps = st->use_lambda ? 0.008f : 0.05f;
  if (st->mixture_valid == s_last_valid && st->use_lambda == s_last_lambda &&
      st->mixture_valid && fabsf(st->afr - s_last_afr) < afr_eps) {
    return;
  }

  char num[16];
  lv_color_t col = lv_color_make(180, 185, 195);

  if (!st->mixture_valid) {
    lv_label_set_text(s_num, "---");
    lv_obj_add_flag(s_unit, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_text_color(s_num, col, 0);
  } else {
    col = color_from_rgb565(afr_map_value_color(st->afr));
    if (st->use_lambda) {
      /* Two decimals: 1.00 not 1.0 */
      snprintf(num, sizeof num, "%0.2f", (double)afr_to_lambda(st->afr));
      lv_label_set_text(s_unit, "\xCE\xBB"); /* UTF-8 λ */
    } else {
      snprintf(num, sizeof num, "%0.1f", (double)st->afr);
      lv_label_set_text(s_unit, "AFR");
    }
    lv_label_set_text(s_num, num);
    lv_obj_clear_flag(s_unit, LV_OBJ_FLAG_HIDDEN);
    lv_obj_set_style_text_color(s_num, col, 0);
    lv_obj_set_style_text_color(s_unit, col, 0);
  }

  s_last_valid = st->mixture_valid;
  s_last_lambda = st->use_lambda;
  s_last_afr = st->afr;
}
