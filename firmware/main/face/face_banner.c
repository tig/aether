/* Banner — MODE · log LED · inverse LAMBDA/AFR button (tap to toggle units).
 *
 * Units control is parented to the screen chrome layer (not the tileview tile)
 * so LVGL hit-tests it as a normal button without the tileview scroll stealing
 * short taps.
 */
#include "face_banner.h"

#include "display.h"

#define C_BANNER lv_color_make(18, 28, 48)
#define C_DIM lv_color_make(200, 210, 225)
#define C_LOG_ON lv_color_make(255, 40, 40)
#define C_LOG_OFF lv_color_make(120, 20, 28)

static lv_obj_t *s_banner;
static lv_obj_t *s_lbl_mode;
static lv_obj_t *s_units_btn;
static lv_obj_t *s_lbl_units;
static lv_obj_t *s_log_led;
static int s_last_lambda = -1;
static int s_last_log = -1;
static face_banner_units_cb_t s_units_cb;

static void style_solid(lv_obj_t *o) {
  lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_remove_flag(o, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_pad_all(o, 0, 0);
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_radius(o, 0, 0);
}

static void on_units_tap(lv_event_t *e) {
  (void)e;
  if (s_units_cb) {
    s_units_cb();
  }
}

void face_banner_set_units_cb(face_banner_units_cb_t cb) { s_units_cb = cb; }

void face_banner_init(lv_obj_t *afr_parent, lv_obj_t *chrome_parent) {
  /* Visual strip lives on the AFR tile. */
  s_banner = lv_obj_create(afr_parent);
  style_solid(s_banner);
  lv_obj_set_size(s_banner, FACE_W, FACE_BANNER_H);
  lv_obj_set_pos(s_banner, 0, 0);
  lv_obj_set_style_bg_color(s_banner, C_BANNER, 0);
  lv_obj_set_style_bg_opa(s_banner, LV_OPA_COVER, 0);

  s_lbl_mode = lv_label_create(s_banner);
  lv_label_set_text(s_lbl_mode, "MODE");
  lv_obj_set_style_text_font(s_lbl_mode, &lv_font_montserrat_36, 0);
  lv_obj_set_style_text_color(s_lbl_mode, C_DIM, 0);
  lv_obj_align(s_lbl_mode, LV_ALIGN_LEFT_MID, 36, 0);

  s_log_led = lv_obj_create(s_banner);
  style_solid(s_log_led);
  lv_obj_set_size(s_log_led, 18, 18);
  lv_obj_set_style_radius(s_log_led, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_color(s_log_led, C_LOG_OFF, 0);
  lv_obj_set_style_bg_opa(s_log_led, LV_OPA_COVER, 0);
  lv_obj_align(s_log_led, LV_ALIGN_CENTER, 0, 0);

  /* Units button on screen chrome — outside tileview scroll. */
  s_units_btn = lv_button_create(chrome_parent);
  lv_obj_set_size(s_units_btn, 220, FACE_BANNER_H);
  lv_obj_align(s_units_btn, LV_ALIGN_TOP_RIGHT, 0, 0);
  lv_obj_set_style_bg_opa(s_units_btn, LV_OPA_TRANSP, 0);
  lv_obj_set_style_bg_opa(s_units_btn, LV_OPA_20, LV_STATE_PRESSED);
  lv_obj_set_style_bg_color(s_units_btn, lv_color_white(), LV_STATE_PRESSED);
  lv_obj_set_style_shadow_width(s_units_btn, 0, 0);
  lv_obj_set_style_border_width(s_units_btn, 0, 0);
  lv_obj_set_style_pad_all(s_units_btn, 0, 0);
  lv_obj_set_style_radius(s_units_btn, 0, 0);
  lv_obj_set_ext_click_area(s_units_btn, 12);
  /* Do not let gestures bubble into the tileview under us. */
  lv_obj_remove_flag(s_units_btn, LV_OBJ_FLAG_GESTURE_BUBBLE);
  lv_obj_remove_flag(s_units_btn, LV_OBJ_FLAG_EVENT_BUBBLE);
  lv_obj_add_event_cb(s_units_btn, on_units_tap, LV_EVENT_CLICKED, NULL);

  s_lbl_units = lv_label_create(s_units_btn);
  lv_label_set_text(s_lbl_units, "LAMBDA");
  lv_obj_set_style_text_font(s_lbl_units, &lv_font_montserrat_36, 0);
  lv_obj_set_style_text_color(s_lbl_units, C_DIM, 0);
  lv_obj_center(s_lbl_units);

  s_last_lambda = 0;
  s_last_log = 0;
}

void face_banner_set_units_visible(int show) {
  if (!s_units_btn) {
    return;
  }
  if (show) {
    lv_obj_remove_flag(s_units_btn, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(s_units_btn);
  } else {
    lv_obj_add_flag(s_units_btn, LV_OBJ_FLAG_HIDDEN);
  }
}

void face_banner_update(const face_state_t *st) {
  if (!st || !s_banner) {
    return;
  }
  if (st->use_lambda != s_last_lambda) {
    /* Inverse: names what a press switches TO. */
    lv_label_set_text(s_lbl_units, st->use_lambda ? "AFR" : "LAMBDA");
    s_last_lambda = st->use_lambda;
  }
  if (st->logging != s_last_log) {
    lv_obj_set_style_bg_color(s_log_led, st->logging ? C_LOG_ON : C_LOG_OFF, 0);
    s_last_log = st->logging;
  }
}
