/* Page 2 — ABOUT: version, live sensors, connectivity.
 * Two columns so the page uses the 800×480 face and stays above the swipe dots.
 */
#include "face_about.h"

#include "afr_map.h"
#include "display.h"
#include "gcu/version.h"
#include "wifi_sta.h"

#include <stdio.h>
#include <string.h>

#define C_BANNER lv_color_make(18, 28, 48)
#define C_TITLE lv_color_make(230, 235, 245)
#define C_DIM lv_color_make(140, 150, 170)
#define C_OK lv_color_make(80, 200, 120)
#define C_WARN lv_color_make(230, 170, 60)

/* Leave the chrome dots (48 px hit + 4 px inset) clear. */
#define ABOUT_BOTTOM_RESERVE 56
#define ABOUT_COL_L 36
#define ABOUT_COL_R 416
#define ABOUT_COL_W 348
#define ABOUT_VAL_X 168
#define ABOUT_LINE 38

static lv_obj_t *s_root;
static lv_obj_t *s_lbl_ver;
static lv_obj_t *s_lbl_mix;
static lv_obj_t *s_lbl_rpm;
static lv_obj_t *s_lbl_tps;
static lv_obj_t *s_lbl_usb;
static lv_obj_t *s_lbl_ecu;
static lv_obj_t *s_lbl_wifi;
static lv_obj_t *s_lbl_wifi_ip;
static lv_obj_t *s_lbl_can;
static int s_last_valid = -1;
static int s_last_lambda = -1;
static int s_last_rpm = -1;
static int s_last_tps = -1;
static int s_last_wifi = -1;
static float s_last_afr = -999.f;

static void style_solid(lv_obj_t *o) {
  lv_obj_clear_flag(o, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE); /* let tileview own swipes */
  lv_obj_set_style_pad_all(o, 0, 0);
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_radius(o, 0, 0);
}

static lv_obj_t *mk_label(lv_obj_t *parent, int x, int y, int w,
                          const lv_font_t *font, lv_color_t col,
                          const char *text) {
  lv_obj_t *l = lv_label_create(parent);
  lv_label_set_text(l, text);
  lv_obj_set_style_text_font(l, font, 0);
  lv_obj_set_style_text_color(l, col, 0);
  lv_obj_set_pos(l, x, y);
  if (w > 0) {
    lv_obj_set_width(l, w);
    lv_label_set_long_mode(l, LV_LABEL_LONG_DOT);
  }
  return l;
}

static lv_obj_t *mk_kv(lv_obj_t *parent, int col_x, int y, const char *key,
                       lv_obj_t **value_out) {
  mk_label(parent, col_x, y, ABOUT_VAL_X - 8, &lv_font_montserrat_28, C_DIM,
           key);
  lv_obj_t *v =
      mk_label(parent, col_x + ABOUT_VAL_X, y, ABOUT_COL_W - ABOUT_VAL_X,
               &lv_font_montserrat_28, C_TITLE, "");
  if (value_out) {
    *value_out = v;
  }
  return v;
}

void face_about_init(lv_obj_t *parent) {
  s_root = lv_obj_create(parent);
  style_solid(s_root);
  lv_obj_set_size(s_root, LV_PCT(100), LV_PCT(100));
  lv_obj_set_pos(s_root, 0, 0);
  lv_obj_set_style_bg_color(s_root, lv_color_black(), 0);
  lv_obj_set_style_bg_opa(s_root, LV_OPA_COVER, 0);

  lv_obj_t *banner = lv_obj_create(s_root);
  style_solid(banner);
  lv_obj_set_size(banner, FACE_W, FACE_BANNER_H);
  lv_obj_set_pos(banner, 0, 0);
  lv_obj_set_style_bg_color(banner, C_BANNER, 0);
  lv_obj_set_style_bg_opa(banner, LV_OPA_COVER, 0);

  lv_obj_t *title = lv_label_create(banner);
  lv_label_set_text(title, "ABOUT");
  lv_obj_set_style_text_font(title, &lv_font_montserrat_36, 0);
  lv_obj_set_style_text_color(title, C_TITLE, 0);
  lv_obj_align(title, LV_ALIGN_CENTER, 0, 0);

  int y = FACE_BANNER_H + 20;

  /* Left: firmware + live sensors */
  mk_label(s_root, ABOUT_COL_L, y, ABOUT_COL_W, &lv_font_montserrat_28, C_DIM,
           "Firmware");
  y += ABOUT_LINE;
  s_lbl_ver = mk_label(s_root, ABOUT_COL_L, y, ABOUT_COL_W,
                       &lv_font_montserrat_28, C_TITLE, "");
  y += ABOUT_LINE;
  mk_label(s_root, ABOUT_COL_L, y, ABOUT_COL_W, &lv_font_montserrat_14, C_DIM,
           "Waveshare ESP32-S3-Touch-LCD-4.3B");

  y += ABOUT_LINE + 12;
  mk_label(s_root, ABOUT_COL_L, y, ABOUT_COL_W, &lv_font_montserrat_28, C_DIM,
           "Sensors (live)");
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_L, y, "Mixture", &s_lbl_mix);
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_L, y, "RPM", &s_lbl_rpm);
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_L, y, "TPS", &s_lbl_tps);

  /* Right: connectivity — same vertical start as Firmware */
  y = FACE_BANNER_H + 20;
  mk_label(s_root, ABOUT_COL_R, y, ABOUT_COL_W, &lv_font_montserrat_28, C_DIM,
           "Connectivity");
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_R, y, "USB", &s_lbl_usb);
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_R, y, "ECU", &s_lbl_ecu);
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_R, y, "Wi-Fi", &s_lbl_wifi);
  y += ABOUT_LINE;
  s_lbl_wifi_ip =
      mk_label(s_root, ABOUT_COL_R + ABOUT_VAL_X, y, ABOUT_COL_W - ABOUT_VAL_X,
               &lv_font_montserrat_28, C_OK, "");
  y += ABOUT_LINE;
  mk_kv(s_root, ABOUT_COL_R, y, "CAN", &s_lbl_can);

  (void)ABOUT_BOTTOM_RESERVE;

  char ver[80];
  snprintf(ver, sizeof ver, "%s  %s", GCU_FW_NAME, GCU_FW_VERSION);
  lv_label_set_text(s_lbl_ver, ver);
  lv_label_set_text(s_lbl_usb, "up");
  lv_obj_set_style_text_color(s_lbl_usb, C_OK, 0);
  lv_label_set_text(s_lbl_ecu, "demo");
  lv_obj_set_style_text_color(s_lbl_ecu, C_WARN, 0);
  lv_label_set_text(s_lbl_wifi, "off");
  lv_label_set_text(s_lbl_wifi_ip, "");
  lv_label_set_text(s_lbl_can, "off");
}

lv_obj_t *face_about_root(void) { return s_root; }

void face_about_show(int show) {
  (void)show; /* tileview owns visibility */
}

void face_about_update(const face_state_t *st) {
  if (!st || !s_lbl_mix) {
    return;
  }
  aether_wifi_state_t ws = aether_wifi_state();
  if (st->mixture_valid == s_last_valid && st->use_lambda == s_last_lambda &&
      st->rpm == s_last_rpm && st->tps == s_last_tps &&
      (int)ws == s_last_wifi &&
      (!st->mixture_valid || st->afr == s_last_afr)) {
    return;
  }
  s_last_valid = st->mixture_valid;
  s_last_lambda = st->use_lambda;
  s_last_rpm = st->rpm;
  s_last_tps = st->tps;
  s_last_afr = st->afr;
  s_last_wifi = (int)ws;

  char buf[64];
  if (!st->mixture_valid) {
    snprintf(buf, sizeof buf, "---");
  } else if (st->use_lambda) {
    snprintf(buf, sizeof buf, "%.2f \xCE\xBB", (double)afr_to_lambda(st->afr));
  } else {
    snprintf(buf, sizeof buf, "%.1f AFR", (double)st->afr);
  }
  lv_label_set_text(s_lbl_mix, buf);

  snprintf(buf, sizeof buf, "%d", st->rpm < 0 ? 0 : st->rpm);
  lv_label_set_text(s_lbl_rpm, buf);

  if (st->tps >= 100) {
    snprintf(buf, sizeof buf, "WOT");
  } else {
    int t = st->tps;
    if (t < 0) {
      t = 0;
    }
    if (t > 99) {
      t = 99;
    }
    snprintf(buf, sizeof buf, "%d%%", t);
  }
  lv_label_set_text(s_lbl_tps, buf);

  lv_label_set_text(s_lbl_usb, "up");
  lv_obj_set_style_text_color(s_lbl_usb, C_OK, 0);

  lv_label_set_text(s_lbl_ecu, "demo");
  lv_obj_set_style_text_color(s_lbl_ecu, C_WARN, 0);

  if (ws == AETHER_WIFI_CONNECTED) {
    char ssid[33];
    char ip[16];
    aether_wifi_active_ssid(ssid, sizeof ssid);
    aether_wifi_ip_str(ip, sizeof ip);
    lv_label_set_text(s_lbl_wifi, ssid[0] ? ssid : "up");
    lv_obj_set_style_text_color(s_lbl_wifi, C_OK, 0);
    lv_label_set_text(s_lbl_wifi_ip, ip);
    lv_obj_set_style_text_color(s_lbl_wifi_ip, C_OK, 0);
  } else if (ws == AETHER_WIFI_OFF) {
    lv_label_set_text(s_lbl_wifi, "off");
    lv_obj_set_style_text_color(s_lbl_wifi, C_DIM, 0);
    lv_label_set_text(s_lbl_wifi_ip, "");
  } else {
    char wstat[64];
    aether_wifi_status_line(wstat, sizeof wstat);
    lv_label_set_text(s_lbl_wifi, wstat);
    lv_obj_set_style_text_color(s_lbl_wifi, C_WARN, 0);
    lv_label_set_text(s_lbl_wifi_ip, "");
  }

  lv_label_set_text(s_lbl_can, "off");
  lv_obj_set_style_text_color(s_lbl_can, C_DIM, 0);
}
