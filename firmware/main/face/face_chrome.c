/* Captions (AFR only) + swipe dots as real LVGL buttons on the screen chrome
 * layer (outside tileview). Fat invisible hit targets + small visual dots.
 */
#include "face_chrome.h"

#include "display.h"

#include <stdint.h>

#define C_DIM lv_color_make(160, 170, 190)
#define C_ON lv_color_make(220, 220, 230)
#define C_OFF lv_color_make(60, 64, 72)

/* Visible disc inside a larger hit target. */
#define DOT_HIT 48
#define DOT_VIS 16

static lv_obj_t *s_rpm_cap;
static lv_obj_t *s_tps_cap;
static lv_obj_t *s_dots[FACE_PAGE_COUNT]; /* hit targets (buttons) */
static lv_obj_t *s_dot_vis[FACE_PAGE_COUNT];
static int s_last_page = -1;
static face_chrome_page_cb_t s_page_cb;

static void on_dot(lv_event_t *e) {
  int page = (int)(intptr_t)lv_event_get_user_data(e);
  if (s_page_cb) {
    s_page_cb(page);
  }
}

void face_chrome_set_page_cb(face_chrome_page_cb_t cb) { s_page_cb = cb; }

void face_chrome_init(lv_obj_t *afr_parent, lv_obj_t *chrome_parent) {
  const int gap = 6;
  s_rpm_cap = lv_label_create(afr_parent);
  lv_label_set_text(s_rpm_cap, "RPM");
  lv_obj_set_style_text_font(s_rpm_cap, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(s_rpm_cap, C_DIM, 0);
  lv_obj_align(s_rpm_cap, LV_ALIGN_BOTTOM_LEFT, 40, -gap);

  s_tps_cap = lv_label_create(afr_parent);
  lv_label_set_text(s_tps_cap, "TPS");
  lv_obj_set_style_text_font(s_tps_cap, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(s_tps_cap, C_DIM, 0);
  lv_obj_align(s_tps_cap, LV_ALIGN_BOTTOM_RIGHT, -40, -gap);

  for (int i = 0; i < FACE_PAGE_COUNT; i++) {
    /* Fat transparent button — LVGL hit-tests this reliably. */
    s_dots[i] = lv_button_create(chrome_parent);
    lv_obj_remove_flag(s_dots[i], LV_OBJ_FLAG_SCROLL_ON_FOCUS);
    lv_obj_set_size(s_dots[i], DOT_HIT, DOT_HIT);
    lv_obj_set_style_bg_opa(s_dots[i], LV_OPA_TRANSP, 0);
    lv_obj_set_style_bg_opa(s_dots[i], LV_OPA_20, LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(s_dots[i], lv_color_white(), LV_STATE_PRESSED);
    lv_obj_set_style_shadow_width(s_dots[i], 0, 0);
    lv_obj_set_style_border_width(s_dots[i], 0, 0);
    lv_obj_set_style_pad_all(s_dots[i], 0, 0);
    lv_obj_set_style_radius(s_dots[i], LV_RADIUS_CIRCLE, 0);
    /* Centered row of 3, slightly above bottom edge. */
    lv_obj_align(s_dots[i], LV_ALIGN_BOTTOM_MID, (i - 1) * 56, -4);
    lv_obj_add_event_cb(s_dots[i], on_dot, LV_EVENT_CLICKED,
                        (void *)(intptr_t)i);

    /* Small visual disc (not clickable — parent button owns the hit). */
    s_dot_vis[i] = lv_obj_create(s_dots[i]);
    lv_obj_remove_flag(s_dot_vis[i], LV_OBJ_FLAG_CLICKABLE);
    lv_obj_remove_flag(s_dot_vis[i], LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_size(s_dot_vis[i], DOT_VIS, DOT_VIS);
    lv_obj_set_style_radius(s_dot_vis[i], LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(s_dot_vis[i], i == 0 ? C_ON : C_OFF, 0);
    lv_obj_set_style_bg_opa(s_dot_vis[i], LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(s_dot_vis[i], 0, 0);
    lv_obj_set_style_pad_all(s_dot_vis[i], 0, 0);
    lv_obj_center(s_dot_vis[i]);
  }
  s_last_page = 0;
}

void face_chrome_set_afr_captions_visible(int show) {
  if (!s_rpm_cap || !s_tps_cap) {
    return;
  }
  if (show) {
    lv_obj_remove_flag(s_rpm_cap, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(s_tps_cap, LV_OBJ_FLAG_HIDDEN);
  } else {
    lv_obj_add_flag(s_rpm_cap, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(s_tps_cap, LV_OBJ_FLAG_HIDDEN);
  }
}

void face_chrome_set_page(int page) {
  if (page < 0) {
    page = 0;
  }
  if (page >= FACE_PAGE_COUNT) {
    page = FACE_PAGE_COUNT - 1;
  }
  for (int i = 0; i < FACE_PAGE_COUNT; i++) {
    if (s_dot_vis[i]) {
      lv_obj_set_style_bg_color(s_dot_vis[i], (i == page) ? C_ON : C_OFF, 0);
    }
  }
  s_last_page = page;
}

void face_chrome_raise_dots(void) {
  for (int i = 0; i < FACE_PAGE_COUNT; i++) {
    if (s_dots[i]) {
      lv_obj_move_foreground(s_dots[i]);
    }
  }
}

void face_chrome_update(const face_state_t *st) {
  if (!st) {
    return;
  }
  if (st->page == s_last_page) {
    return;
  }
  face_chrome_set_page(st->page);
}
