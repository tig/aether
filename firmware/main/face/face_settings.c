/* SETTINGS — product options + Wi-Fi (ESP-IDF station via wifi_sta).
 * Scan / password overlays parent to the active screen so tileview swipe
 * does not steal taps.
 */
#include "face_settings.h"

#include "display.h"
#include "wifi_sta.h"

#include <stdio.h>
#include <string.h>

#define C_BANNER lv_color_make(18, 28, 48)
#define C_TITLE lv_color_make(230, 235, 245)
#define C_DIM lv_color_make(140, 150, 170)
#define C_ROW lv_color_make(28, 34, 48)
#define C_OK lv_color_make(80, 200, 120)
#define C_WARN lv_color_make(230, 170, 60)
#define C_ACCENT lv_color_make(60, 120, 220)

static lv_obj_t *s_root;
static lv_obj_t *s_sw_wifi;
static lv_obj_t *s_lbl_status;
static lv_obj_t *s_lbl_net;
static lv_obj_t *s_btn_scan;
static lv_obj_t *s_btn_connect;

/* Full-screen overlays on lv_screen_active (outside tileview). */
static lv_obj_t *s_scan_ov;
static lv_obj_t *s_scan_list;
static lv_obj_t *s_pass_ov;
static lv_obj_t *s_pass_ta;
static lv_obj_t *s_kb;
static char s_pick_ssid[33];
static uint8_t s_pick_auth;
static int s_last_state = -1;
static int s_waiting_scan;

static void style_solid(lv_obj_t *o) {
  lv_obj_clear_flag(o, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_set_style_pad_all(o, 0, 0);
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_radius(o, 0, 0);
}

static void style_row(lv_obj_t *row) {
  style_solid(row);
  lv_obj_clear_flag(row, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_bg_color(row, C_ROW, 0);
  lv_obj_set_style_bg_opa(row, LV_OPA_COVER, 0);
  lv_obj_set_style_radius(row, 8, 0);
}

static void style_action_btn(lv_obj_t *btn) {
  lv_obj_remove_flag(btn, LV_OBJ_FLAG_GESTURE_BUBBLE);
  lv_obj_remove_flag(btn, LV_OBJ_FLAG_EVENT_BUBBLE);
  lv_obj_set_style_bg_color(btn, C_ACCENT, 0);
  lv_obj_set_style_bg_opa(btn, LV_OPA_COVER, 0);
  lv_obj_set_style_radius(btn, 8, 0);
  lv_obj_set_style_shadow_width(btn, 0, 0);
  lv_obj_set_style_pad_all(btn, 8, 0);
}

static void refresh_status_ui(void) {
  if (!s_lbl_status) {
    return;
  }
  char line[96];
  aether_wifi_status_line(line, sizeof line);
  lv_label_set_text(s_lbl_status, line);

  aether_wifi_state_t st = aether_wifi_state();
  lv_color_t c = C_DIM;
  if (st == AETHER_WIFI_CONNECTED) {
    c = C_OK;
  } else if (st == AETHER_WIFI_FAIL || st == AETHER_WIFI_CONNECTING ||
             st == AETHER_WIFI_SCANNING) {
    c = C_WARN;
  }
  lv_obj_set_style_text_color(s_lbl_status, c, 0);

  char ssid[33];
  aether_wifi_active_ssid(ssid, sizeof ssid);
  if (ssid[0]) {
    lv_label_set_text_fmt(s_lbl_net, "%s", ssid);
  } else {
    lv_label_set_text(s_lbl_net, "(none — Scan)");
  }

  if (s_sw_wifi) {
    bool on = aether_wifi_enabled();
    if (on != lv_obj_has_state(s_sw_wifi, LV_STATE_CHECKED)) {
      if (on) {
        lv_obj_add_state(s_sw_wifi, LV_STATE_CHECKED);
      } else {
        lv_obj_remove_state(s_sw_wifi, LV_STATE_CHECKED);
      }
    }
  }

  if (s_btn_connect) {
    lv_obj_t *lab = lv_obj_get_child(s_btn_connect, 0);
    if (lab) {
      if (st == AETHER_WIFI_CONNECTED) {
        lv_label_set_text(lab, "Disconnect");
      } else {
        lv_label_set_text(lab, "Connect");
      }
    }
  }
}

static void hide_pass_overlay(void) {
  if (s_pass_ov) {
    lv_obj_add_flag(s_pass_ov, LV_OBJ_FLAG_HIDDEN);
  }
  if (s_kb) {
    lv_keyboard_set_textarea(s_kb, NULL);
    lv_obj_add_flag(s_kb, LV_OBJ_FLAG_HIDDEN);
  }
}

static void hide_scan_overlay(void) {
  if (s_scan_ov) {
    lv_obj_add_flag(s_scan_ov, LV_OBJ_FLAG_HIDDEN);
  }
}

static void on_pass_ready(void) {
  const char *pw = lv_textarea_get_text(s_pass_ta);
  hide_pass_overlay();
  hide_scan_overlay();
  (void)aether_wifi_connect(s_pick_ssid, pw ? pw : "");
  refresh_status_ui();
}

static void on_kb_event(lv_event_t *e) {
  lv_event_code_t code = lv_event_get_code(e);
  if (code == LV_EVENT_READY) {
    on_pass_ready();
  } else if (code == LV_EVENT_CANCEL) {
    hide_pass_overlay();
  }
}

static void on_pass_ok(lv_event_t *e) {
  (void)e;
  on_pass_ready();
}

static void on_pass_cancel(lv_event_t *e) {
  (void)e;
  hide_pass_overlay();
}

static void show_pass_overlay(const char *ssid, uint8_t auth) {
  strncpy(s_pick_ssid, ssid, sizeof s_pick_ssid - 1);
  s_pick_ssid[sizeof s_pick_ssid - 1] = 0;
  s_pick_auth = auth;
  (void)s_pick_auth; /* open nets still get this dialog; blank pass OK */

  if (!s_pass_ov) {
    return;
  }
  /* Always show password field (open AP → leave empty and Join).
   * Prefill from NVS when re-selecting the saved network. */
  char saved_ssid[33], saved_pass[65];
  aether_wifi_get_credentials(saved_ssid, sizeof saved_ssid, saved_pass,
                              sizeof saved_pass);
  if (saved_ssid[0] && strcmp(saved_ssid, s_pick_ssid) == 0) {
    lv_textarea_set_text(s_pass_ta, saved_pass);
  } else {
    lv_textarea_set_text(s_pass_ta, "");
  }
  /* Plain text so the operator can verify what they typed. */
  lv_textarea_set_password_mode(s_pass_ta, false);

  lv_obj_t *title = lv_obj_get_child(s_pass_ov, 0);
  if (title) {
    lv_label_set_text_fmt(title, "Password for %s", s_pick_ssid);
  }
  lv_obj_remove_flag(s_pass_ov, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(s_pass_ov);
  if (s_kb) {
    lv_keyboard_set_textarea(s_kb, s_pass_ta);
    lv_obj_remove_flag(s_kb, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(s_kb);
  }
  lv_obj_add_state(s_pass_ta, LV_STATE_FOCUSED);
}

static void on_ap_pick(lv_event_t *e) {
  aether_wifi_ap_t *ap = (aether_wifi_ap_t *)lv_event_get_user_data(e);
  if (!ap || !ap->ssid[0]) {
    return;
  }
  show_pass_overlay(ap->ssid, ap->authmode);
}

static void fill_scan_list(void) {
  if (!s_scan_list) {
    return;
  }
  lv_obj_clean(s_scan_list);
  int n = aether_wifi_scan_count();
  if (n <= 0) {
    lv_obj_t *btn = lv_list_add_button(s_scan_list, NULL, "No networks found");
    lv_obj_clear_flag(btn, LV_OBJ_FLAG_CLICKABLE);
    return;
  }
  /* Keep stable copies in static so user_data survives list rebuild. */
  static aether_wifi_ap_t s_pick_aps[AETHER_WIFI_SCAN_MAX];
  int copy_n = n < AETHER_WIFI_SCAN_MAX ? n : AETHER_WIFI_SCAN_MAX;
  for (int i = 0; i < copy_n; i++) {
    if (!aether_wifi_scan_get(i, &s_pick_aps[i])) {
      continue;
    }
    char line[72];
    const char *lock = s_pick_aps[i].authmode == 0 ? "open" : "secured";
    snprintf(line, sizeof line, "%s  %ddBm  %s", s_pick_aps[i].ssid,
             (int)s_pick_aps[i].rssi, lock);
    lv_obj_t *btn = lv_list_add_button(s_scan_list, NULL, line);
    lv_obj_add_event_cb(btn, on_ap_pick, LV_EVENT_CLICKED, &s_pick_aps[i]);
  }
}

static void on_scan_close(lv_event_t *e) {
  (void)e;
  hide_scan_overlay();
}

static void ensure_overlays(void) {
  lv_obj_t *scr = lv_screen_active();
  if (!scr || s_scan_ov) {
    return;
  }

  /* ---- Scan overlay ---- */
  s_scan_ov = lv_obj_create(scr);
  style_solid(s_scan_ov);
  lv_obj_set_size(s_scan_ov, FACE_W, FACE_H);
  lv_obj_set_pos(s_scan_ov, 0, 0);
  lv_obj_set_style_bg_color(s_scan_ov, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(s_scan_ov, LV_OPA_COVER, 0);
  lv_obj_add_flag(s_scan_ov, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t *scan_title = lv_label_create(s_scan_ov);
  lv_label_set_text(scan_title, "Wi-Fi networks");
  lv_obj_set_style_text_font(scan_title, &lv_font_montserrat_36, 0);
  lv_obj_set_style_text_color(scan_title, C_TITLE, 0);
  lv_obj_align(scan_title, LV_ALIGN_TOP_MID, 0, 16);

  lv_obj_t *close_btn = lv_button_create(s_scan_ov);
  style_action_btn(close_btn);
  lv_obj_set_size(close_btn, 120, 44);
  lv_obj_align(close_btn, LV_ALIGN_TOP_RIGHT, -16, 12);
  lv_obj_add_event_cb(close_btn, on_scan_close, LV_EVENT_CLICKED, NULL);
  lv_obj_t *cl = lv_label_create(close_btn);
  lv_label_set_text(cl, "Close");
  lv_obj_set_style_text_font(cl, &lv_font_montserrat_28, 0);
  lv_obj_center(cl);

  s_scan_list = lv_list_create(s_scan_ov);
  lv_obj_set_size(s_scan_list, FACE_W - 32, FACE_H - 90);
  lv_obj_align(s_scan_list, LV_ALIGN_BOTTOM_MID, 0, -12);
  lv_obj_set_style_bg_color(s_scan_list, C_ROW, 0);
  lv_obj_set_style_border_width(s_scan_list, 0, 0);

  /* ---- Password overlay ---- */
  s_pass_ov = lv_obj_create(scr);
  style_solid(s_pass_ov);
  lv_obj_set_size(s_pass_ov, FACE_W, FACE_H / 2);
  lv_obj_set_pos(s_pass_ov, 0, 0);
  lv_obj_set_style_bg_color(s_pass_ov, C_BANNER, 0);
  lv_obj_set_style_bg_opa(s_pass_ov, LV_OPA_COVER, 0);
  lv_obj_add_flag(s_pass_ov, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t *pt = lv_label_create(s_pass_ov);
  lv_label_set_text(pt, "Password");
  lv_obj_set_style_text_font(pt, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(pt, C_TITLE, 0);
  lv_obj_align(pt, LV_ALIGN_TOP_LEFT, 24, 16);

  s_pass_ta = lv_textarea_create(s_pass_ov);
  lv_obj_set_size(s_pass_ta, FACE_W - 48, 52);
  lv_obj_align(s_pass_ta, LV_ALIGN_TOP_MID, 0, 60);
  lv_textarea_set_one_line(s_pass_ta, true);
  lv_textarea_set_password_mode(s_pass_ta, false); /* always show plaintext */
  lv_textarea_set_placeholder_text(s_pass_ta, "password (empty if open)");
  lv_obj_set_style_text_font(s_pass_ta, &lv_font_montserrat_28, 0);

  lv_obj_t *ok = lv_button_create(s_pass_ov);
  style_action_btn(ok);
  lv_obj_set_size(ok, 140, 48);
  lv_obj_align(ok, LV_ALIGN_BOTTOM_RIGHT, -24, -16);
  lv_obj_add_event_cb(ok, on_pass_ok, LV_EVENT_CLICKED, NULL);
  lv_obj_t *okl = lv_label_create(ok);
  lv_label_set_text(okl, "Join");
  lv_obj_set_style_text_font(okl, &lv_font_montserrat_28, 0);
  lv_obj_center(okl);

  lv_obj_t *cancel = lv_button_create(s_pass_ov);
  style_action_btn(cancel);
  lv_obj_set_style_bg_color(cancel, C_ROW, 0);
  lv_obj_set_size(cancel, 140, 48);
  lv_obj_align(cancel, LV_ALIGN_BOTTOM_LEFT, 24, -16);
  lv_obj_add_event_cb(cancel, on_pass_cancel, LV_EVENT_CLICKED, NULL);
  lv_obj_t *cxl = lv_label_create(cancel);
  lv_label_set_text(cxl, "Cancel");
  lv_obj_set_style_text_font(cxl, &lv_font_montserrat_28, 0);
  lv_obj_center(cxl);

  s_kb = lv_keyboard_create(scr);
  lv_obj_set_size(s_kb, FACE_W, FACE_H / 2);
  lv_obj_align(s_kb, LV_ALIGN_BOTTOM_MID, 0, 0);
  lv_obj_add_flag(s_kb, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_event_cb(s_kb, on_kb_event, LV_EVENT_ALL, NULL);
}

static void on_wifi_sw(lv_event_t *e) {
  (void)e;
  bool on = lv_obj_has_state(s_sw_wifi, LV_STATE_CHECKED);
  (void)aether_wifi_set_enabled(on);
  refresh_status_ui();
}

static void on_scan(lv_event_t *e) {
  (void)e;
  ensure_overlays();
  if (!s_scan_ov) {
    return;
  }
  lv_obj_clean(s_scan_list);
  lv_list_add_button(s_scan_list, NULL, "Scanning…");
  lv_obj_remove_flag(s_scan_ov, LV_OBJ_FLAG_HIDDEN);
  lv_obj_move_foreground(s_scan_ov);
  s_waiting_scan = 1;
  if (!aether_wifi_scan_start()) {
    lv_obj_clean(s_scan_list);
    lv_list_add_button(s_scan_list, NULL, "Scan failed — try Wi-Fi On");
    s_waiting_scan = 0;
  }
  refresh_status_ui();
}

static void on_connect(lv_event_t *e) {
  (void)e;
  if (aether_wifi_state() == AETHER_WIFI_CONNECTED) {
    (void)aether_wifi_disconnect();
  } else {
    char ssid[33], pass[65];
    aether_wifi_get_credentials(ssid, sizeof ssid, pass, sizeof pass);
    if (!ssid[0]) {
      on_scan(NULL);
      return;
    }
    (void)aether_wifi_connect(ssid, pass);
  }
  refresh_status_ui();
}

void face_settings_init(lv_obj_t *parent) {
  s_root = lv_obj_create(parent);
  style_solid(s_root);
  lv_obj_clear_flag(s_root, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_size(s_root, LV_PCT(100), LV_PCT(100));
  lv_obj_set_pos(s_root, 0, 0);
  lv_obj_set_style_bg_color(s_root, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(s_root, LV_OPA_COVER, 0);

  lv_obj_t *banner = lv_obj_create(s_root);
  style_row(banner);
  lv_obj_set_style_bg_color(banner, C_BANNER, 0);
  lv_obj_set_size(banner, FACE_W, FACE_BANNER_H);
  lv_obj_set_pos(banner, 0, 0);

  lv_obj_t *title = lv_label_create(banner);
  lv_label_set_text(title, "SETTINGS");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_36, 0);
  lv_obj_set_style_text_color(title, C_TITLE, 0);
  lv_obj_align(title, LV_ALIGN_CENTER, 0, 0);

  int y = FACE_BANNER_H + 20;

  /* ---- Wi-Fi enable ---- */
  lv_obj_t *row_en = lv_obj_create(s_root);
  style_row(row_en);
  lv_obj_set_size(row_en, FACE_W - 48, 64);
  lv_obj_set_pos(row_en, 24, y);

  lv_obj_t *lbl_en = lv_label_create(row_en);
  lv_label_set_text(lbl_en, "Wi-Fi");
  lv_obj_set_style_text_font(lbl_en, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(lbl_en, C_TITLE, 0);
  lv_obj_align(lbl_en, LV_ALIGN_LEFT_MID, 20, 0);

  s_sw_wifi = lv_switch_create(row_en);
  lv_obj_align(s_sw_wifi, LV_ALIGN_RIGHT_MID, -20, 0);
  lv_obj_remove_flag(s_sw_wifi, LV_OBJ_FLAG_GESTURE_BUBBLE);
  lv_obj_add_event_cb(s_sw_wifi, on_wifi_sw, LV_EVENT_VALUE_CHANGED, NULL);
  if (aether_wifi_enabled()) {
    lv_obj_add_state(s_sw_wifi, LV_STATE_CHECKED);
  }
  y += 76;

  /* ---- Status ---- */
  lv_obj_t *row_st = lv_obj_create(s_root);
  style_row(row_st);
  lv_obj_set_size(row_st, FACE_W - 48, 64);
  lv_obj_set_pos(row_st, 24, y);

  lv_obj_t *lbl_st = lv_label_create(row_st);
  lv_label_set_text(lbl_st, "Status");
  lv_obj_set_style_text_font(lbl_st, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(lbl_st, C_TITLE, 0);
  lv_obj_align(lbl_st, LV_ALIGN_LEFT_MID, 20, 0);

  s_lbl_status = lv_label_create(row_st);
  lv_label_set_text(s_lbl_status, "off");
  lv_obj_set_style_text_font(s_lbl_status, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(s_lbl_status, C_DIM, 0);
  lv_obj_align(s_lbl_status, LV_ALIGN_RIGHT_MID, -20, 0);
  y += 76;

  /* ---- Network ---- */
  lv_obj_t *row_net = lv_obj_create(s_root);
  style_row(row_net);
  lv_obj_set_size(row_net, FACE_W - 48, 64);
  lv_obj_set_pos(row_net, 24, y);

  lv_obj_t *lbl_net = lv_label_create(row_net);
  lv_label_set_text(lbl_net, "Network");
  lv_obj_set_style_text_font(lbl_net, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(lbl_net, C_TITLE, 0);
  lv_obj_align(lbl_net, LV_ALIGN_LEFT_MID, 20, 0);

  s_lbl_net = lv_label_create(row_net);
  lv_label_set_text(s_lbl_net, "(none)");
  lv_obj_set_style_text_font(s_lbl_net, &lv_font_montserrat_28, 0);
  lv_obj_set_style_text_color(s_lbl_net, C_DIM, 0);
  lv_obj_align(s_lbl_net, LV_ALIGN_RIGHT_MID, -20, 0);
  y += 84;

  /* ---- Actions ---- */
  s_btn_scan = lv_button_create(s_root);
  style_action_btn(s_btn_scan);
  lv_obj_set_size(s_btn_scan, 280, 56);
  lv_obj_set_pos(s_btn_scan, 24, y);
  lv_obj_add_event_cb(s_btn_scan, on_scan, LV_EVENT_CLICKED, NULL);
  lv_obj_t *sl = lv_label_create(s_btn_scan);
  lv_label_set_text(sl, "Scan networks");
  lv_obj_set_style_text_font(sl, &lv_font_montserrat_28, 0);
  lv_obj_center(sl);

  s_btn_connect = lv_button_create(s_root);
  style_action_btn(s_btn_connect);
  lv_obj_set_size(s_btn_connect, 280, 56);
  lv_obj_set_pos(s_btn_connect, FACE_W - 24 - 280, y);
  lv_obj_add_event_cb(s_btn_connect, on_connect, LV_EVENT_CLICKED, NULL);
  lv_obj_t *col = lv_label_create(s_btn_connect);
  lv_label_set_text(col, "Connect");
  lv_obj_set_style_text_font(col, &lv_font_montserrat_28, 0);
  lv_obj_center(col);
  y += 80;

  /* Non-wifi product notes */
  lv_obj_t *hint = lv_label_create(s_root);
  lv_label_set_text(hint,
                    "Units: AFR / lambda via banner. Credentials stored in NVS.");
  lv_obj_set_style_text_font(hint, &lv_font_montserrat_14, 0);
  lv_obj_set_style_text_color(hint, C_DIM, 0);
  lv_obj_set_pos(hint, 28, y);

  ensure_overlays();
  refresh_status_ui();
}

lv_obj_t *face_settings_root(void) { return s_root; }

void face_settings_show(int show) {
  (void)show;
}

void face_settings_update(const face_state_t *st) {
  (void)st;
  if (s_waiting_scan && aether_wifi_scan_done()) {
    s_waiting_scan = 0;
    fill_scan_list();
  }
  int cur = (int)aether_wifi_state();
  if (cur != s_last_state) {
    s_last_state = cur;
    refresh_status_ui();
  } else {
    /* Keep IP/status text fresh while connected. */
    static int s_tick;
    if ((++s_tick & 15) == 0) {
      refresh_status_ui();
    }
  }
}
