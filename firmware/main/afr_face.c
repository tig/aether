/* Multi-page face: AFR | SETTINGS | ABOUT via LVGL tileview (native swipe).
 * Demo sensors always advance; units are user-owned (banner button).
 */
#include "afr_face.h"

#include "display.h"
#include "face/face_about.h"
#include "face/face_aux.h"
#include "face/face_banner.h"
#include "face/face_chrome.h"
#include "face/face_dial.h"
#include "face/face_primary.h"
#include "face/face_settings.h"
#include "face/face_state.h"

#include "lvgl.h"

#include <string.h>

static face_state_t s_st;
static int s_scene_hold;
static int s_page = FACE_PAGE_AFR;
static lv_obj_t *s_tv;
static lv_obj_t *s_tiles[FACE_PAGE_COUNT];

static void apply_page_chrome(int page) {
  face_chrome_set_afr_captions_visible(page == FACE_PAGE_AFR);
  face_chrome_set_page(page);
  face_banner_set_units_visible(page == FACE_PAGE_AFR);
  face_chrome_raise_dots();
  if (page == FACE_PAGE_ABOUT) {
    face_about_update(&s_st);
  }
}

static void sync_page_from_tileview(void) {
  if (!s_tv) {
    return;
  }
  lv_obj_t *act = lv_tileview_get_tile_active(s_tv);
  int page = FACE_PAGE_AFR;
  for (int i = 0; i < FACE_PAGE_COUNT; i++) {
    if (s_tiles[i] == act) {
      page = i;
      break;
    }
  }
  s_page = page;
  s_st.page = page;
  apply_page_chrome(page);
}

static void on_tile_changed(lv_event_t *e) {
  (void)e;
  sync_page_from_tileview();
}

void afr_face_set_page(int page) {
  if (page < 0) {
    page = 0;
  }
  if (page >= FACE_PAGE_COUNT) {
    page = FACE_PAGE_COUNT - 1;
  }
  if (!s_tv) {
    s_page = page;
    return;
  }
  if (page == s_page && lv_tileview_get_tile_active(s_tv) == s_tiles[page]) {
    return;
  }
  s_page = page;
  s_st.page = page;
  lv_tileview_set_tile_by_index(s_tv, (uint32_t)page, 0, LV_ANIM_ON);
  apply_page_chrome(page);
}

int afr_face_page(void) { return s_page; }

static void on_dot_page(int page) {
  /* Instant jump when tapping dots (no anim thrash). */
  if (page < 0) {
    page = 0;
  }
  if (page >= FACE_PAGE_COUNT) {
    page = FACE_PAGE_COUNT - 1;
  }
  s_page = page;
  s_st.page = page;
  if (s_tv && s_tiles[page]) {
    lv_tileview_set_tile_by_index(s_tv, (uint32_t)page, 0, LV_ANIM_OFF);
  }
  apply_page_chrome(page);
}

static void on_units_toggle(void) {
  if (s_scene_hold) {
    return;
  }
  s_st.use_lambda = s_st.use_lambda ? 0 : 1;
  face_banner_update(&s_st);
  face_primary_update(&s_st);
  face_about_update(&s_st);
}

void afr_face_init(void) {
  lv_obj_t *scr = lv_screen_active();
  lv_obj_set_style_bg_color(scr, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
  lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);

  /* Stock LVGL tileview: one row of tiles, swipe is built-in. */
  s_tv = lv_tileview_create(scr);
  lv_obj_set_size(s_tv, FACE_W, FACE_H);
  lv_obj_set_style_bg_color(s_tv, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(s_tv, LV_OPA_COVER, 0);
  lv_obj_set_scrollbar_mode(s_tv, LV_SCROLLBAR_MODE_OFF);

  s_tiles[FACE_PAGE_AFR] =
      lv_tileview_add_tile(s_tv, 0, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
  s_tiles[FACE_PAGE_SETTINGS] =
      lv_tileview_add_tile(s_tv, 1, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
  s_tiles[FACE_PAGE_ABOUT] =
      lv_tileview_add_tile(s_tv, 2, 0, LV_DIR_LEFT | LV_DIR_RIGHT);

  for (int i = 0; i < FACE_PAGE_COUNT; i++) {
    lv_obj_set_style_bg_color(s_tiles[i], lv_color_black(), 0);
    lv_obj_set_style_bg_opa(s_tiles[i], LV_OPA_COVER, 0);
    /* Tiles must not scroll themselves — the tileview does. */
    lv_obj_remove_flag(s_tiles[i], LV_OBJ_FLAG_SCROLLABLE);
  }

  face_dial_init(s_tiles[FACE_PAGE_AFR]);
  face_primary_init(s_tiles[FACE_PAGE_AFR]);
  face_aux_init(s_tiles[FACE_PAGE_AFR]);
  /* Dots / units live on the screen, not the tileview. A FLOATING child of
   * the scroller still starts a swipe when the finger moves a few pixels. */
  face_banner_init(s_tiles[FACE_PAGE_AFR], scr);
  face_banner_set_units_cb(on_units_toggle);
  face_chrome_init(s_tiles[FACE_PAGE_AFR], scr);
  face_chrome_set_page_cb(on_dot_page);

  face_settings_init(s_tiles[FACE_PAGE_SETTINGS]);
  face_about_init(s_tiles[FACE_PAGE_ABOUT]);

  lv_obj_add_event_cb(s_tv, on_tile_changed, LV_EVENT_VALUE_CHANGED, NULL);
  lv_tileview_set_tile_by_index(s_tv, 0, 0, LV_ANIM_OFF);

  memset(&s_st, 0, sizeof s_st);
  s_st.afr = 14.7f;
  s_st.use_lambda = 0;
  s_st.page = FACE_PAGE_AFR;
  s_page = FACE_PAGE_AFR;
  s_scene_hold = 0;
  apply_page_chrome(FACE_PAGE_AFR);

  (void)display_touch_lvgl_init();
}

void afr_face_update(const afr_face_state_t *st) {
  if (!st) {
    return;
  }
  if (s_scene_hold) {
    return;
  }

  s_st.mixture_valid = st->mixture_valid;
  s_st.afr = st->afr;
  /* use_lambda is user-owned (banner button). */
  s_st.rpm = st->rpm;
  s_st.tps = st->tps;
  s_st.logging = st->logging;
  s_st.redline_warn = st->redline_warn;
  s_st.page = s_page;

  /* Always advance AFR pipeline (multitasking while other tiles are front).
   * Skip the software bezel while the tileview is scrolling — a 800×324
   * raster mid-swipe underruns the RGB bounce buffer. */
  if (!s_tv || !lv_obj_is_scrolling(s_tv)) {
    face_dial_update(&s_st);
  }
  face_primary_update(&s_st);
  face_aux_update(&s_st);
  face_banner_update(&s_st);
  face_chrome_update(&s_st);
  face_about_update(&s_st);
  face_settings_update(&s_st);
}

void afr_face_handler(void) {
  lv_timer_handler();
}

int afr_face_scene_hold(void) { return s_scene_hold; }

void afr_face_live(void) { s_scene_hold = 0; }

static void apply_state(const face_state_t *st) {
  s_st = *st;
  s_scene_hold = 1;
  afr_face_set_page(st->page);
  s_st.page = s_page;
  face_dial_force_dirty();
  face_dial_update(&s_st);
  face_primary_update(&s_st);
  face_aux_update(&s_st);
  face_banner_update(&s_st);
  face_chrome_update(&s_st);
  face_about_update(&s_st);
}

int afr_face_apply_scene(const char *id) {
  face_state_t st;
  memset(&st, 0, sizeof st);
  st.afr = 14.7f;
  st.mixture_valid = 1;

  if (strcmp(id, "banner_afr") == 0) {
    st.use_lambda = 0;
    st.logging = 0;
  } else if (strcmp(id, "banner_lambda") == 0) {
    st.use_lambda = 1;
    st.rpm = 2400;
    st.tps = 18;
  } else if (strcmp(id, "banner_log_on") == 0) {
    st.logging = 1;
    st.rpm = 2400;
    st.tps = 18;
  } else if (strcmp(id, "dial_off") == 0 || strcmp(id, "primary_invalid") == 0) {
    st.mixture_valid = 0;
  } else if (strcmp(id, "dial_stoich") == 0 ||
             strcmp(id, "primary_stoich_afr") == 0 ||
             strcmp(id, "chrome_page0") == 0) {
    st.logging = 1;
    st.rpm = 2400;
    st.tps = 18;
  } else if (strcmp(id, "dial_rich") == 0) {
    st.afr = 11.5f;
    st.logging = 1;
    st.rpm = 3000;
    st.tps = 40;
  } else if (strcmp(id, "primary_lambda") == 0) {
    st.use_lambda = 1;
    st.logging = 1;
    st.rpm = 2400;
    st.tps = 18;
  } else if (strcmp(id, "aux_idle") == 0) {
    st.logging = 1;
    st.rpm = 750;
    st.tps = 0;
  } else if (strcmp(id, "aux_wot") == 0) {
    st.afr = 12.5f;
    st.logging = 1;
    st.rpm = 5500;
    st.tps = 100;
  } else if (strcmp(id, "aux_redline") == 0) {
    st.afr = 12.4f;
    st.logging = 1;
    st.rpm = 6200;
    st.tps = 100;
    st.redline_warn = 1;
  } else if (strcmp(id, "page_about") == 0) {
    st.logging = 1;
    st.rpm = 2400;
    st.tps = 18;
    st.page = FACE_PAGE_ABOUT;
  } else {
    return -1;
  }

  apply_state(&st);
  return 0;
}
