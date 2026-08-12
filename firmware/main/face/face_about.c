/* Page 2 — ABOUT: version, live sensors, connectivity. */
#include "face_about.h"

#include "afr_map.h"
#include "display.h"
#include "gcu/version.h"
#include "wifi_sta.h"

#include <stdio.h>

#define C_BANNER lv_color_make(18, 28, 48)
#define C_TITLE lv_color_make(230, 235, 245)
#define C_DIM lv_color_make(140, 150, 170)
#define C_OK lv_color_make(80, 200, 120)
#define C_WARN lv_color_make(230, 170, 60)

static lv_obj_t *s_root;
static lv_obj_t *s_lbl_ver;
static lv_obj_t *s_lbl_mix;
static lv_obj_t *s_lbl_rpm;
static lv_obj_t *s_lbl_tps;
static lv_obj_t *s_lbl_usb;
static lv_obj_t *s_lbl_ecu;
static lv_obj_t *s_lbl_wifi;
static lv_obj_t *s_lbl_can;

static void style_solid(lv_obj_t *o) {
  lv_obj_clear_flag(o, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE); /* let tileview own swipes */
  lv_obj_set_style_pad_all(o, 0, 0);
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_radius(o, 0, 0);
}

static lv_obj_t *mk_label(lv_obj_t *parent, int x, int y, const lv_font_t *font,
                          lv_color_t col, const char *text) {
  lv_obj_t *l = lv_label_create(parent);
  lv_label_set_text(l, text);
  lv_obj_set_style_text_font(l, font, 0);
  lv_obj_set_style_text_color(l, col, 0);
  lv_obj_set_pos(l, x, y);
  return l;
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
  mk_label(s_root, 36, y, &lv_font_montserrat_28, C_DIM, "Firmware");
  y += 36;
  s_lbl_ver = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_TITLE, "");
  y += 44;
  mk_label(s_root, 36, y, &lv_font_montserrat_14, C_DIM,
           "Board  Waveshare ESP32-S3-Touch-LCD-4.3B");

  y += 40;
  mk_label(s_root, 36, y, &lv_font_montserrat_28, C_DIM, "Sensors (live)");
  y += 36;
  s_lbl_mix = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_TITLE, "");
  y += 36;
  s_lbl_rpm = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_TITLE, "");
  y += 36;
  s_lbl_tps = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_TITLE, "");

  y += 44;
  mk_label(s_root, 36, y, &lv_font_montserrat_28, C_DIM, "Connectivity");
  y += 36;
  s_lbl_usb = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_OK, "");
  y += 36;
  s_lbl_ecu = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_WARN, "");
  y += 36;
  s_lbl_wifi = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_DIM, "");
  y += 36;
  s_lbl_can = mk_label(s_root, 36, y, &lv_font_montserrat_28, C_DIM, "");

  char ver[80];
  snprintf(ver, sizeof ver, "%s  %s", GCU_FW_NAME, GCU_FW_VERSION);
  lv_label_set_text(s_lbl_ver, ver);
  lv_label_set_text(s_lbl_usb, "USB serial   up");
  lv_label_set_text(s_lbl_ecu, "ECU link     demo (not linked)");
  lv_label_set_text(s_lbl_wifi, "Wi-Fi        off");
  lv_label_set_text(s_lbl_can, "CAN          off");
}

lv_obj_t *face_about_root(void) { return s_root; }

void face_about_show(int show) {
  (void)show; /* tileview owns visibility */
}

void face_about_update(const face_state_t *st) {
  if (!st || !s_lbl_mix) {
    return;
  }
  char buf[64];
  if (!st->mixture_valid) {
    snprintf(buf, sizeof buf, "Mixture     ---");
  } else if (st->use_lambda) {
    snprintf(buf, sizeof buf, "Mixture     %.2f \xCE\xBB",
             (double)afr_to_lambda(st->afr));
  } else {
    snprintf(buf, sizeof buf, "Mixture     %.1f AFR", (double)st->afr);
  }
  lv_label_set_text(s_lbl_mix, buf);

  snprintf(buf, sizeof buf, "RPM         %d", st->rpm < 0 ? 0 : st->rpm);
  lv_label_set_text(s_lbl_rpm, buf);

  if (st->tps >= 100) {
    snprintf(buf, sizeof buf, "TPS         WOT");
  } else {
    int t = st->tps;
    if (t < 0) {
      t = 0;
    }
    if (t > 99) {
      t = 99;
    }
    snprintf(buf, sizeof buf, "TPS         %d%%", t);
  }
  lv_label_set_text(s_lbl_tps, buf);

  /* USB is how host talks to us — always "up" while this UI is running. */
  lv_label_set_text(s_lbl_usb, "USB serial   up");
  lv_obj_set_style_text_color(s_lbl_usb, C_OK, 0);

  /* Demo path until live ECU client is wired. */
  lv_label_set_text(s_lbl_ecu, "ECU link     demo (not linked)");
  lv_obj_set_style_text_color(s_lbl_ecu, C_WARN, 0);

  char wline[80];
  char wstat[64];
  aether_wifi_status_line(wstat, sizeof wstat);
  snprintf(wline, sizeof wline, "Wi-Fi        %s", wstat);
  lv_label_set_text(s_lbl_wifi, wline);
  aether_wifi_state_t ws = aether_wifi_state();
  if (ws == AETHER_WIFI_CONNECTED) {
    lv_obj_set_style_text_color(s_lbl_wifi, C_OK, 0);
  } else if (ws == AETHER_WIFI_OFF) {
    lv_obj_set_style_text_color(s_lbl_wifi, C_DIM, 0);
  } else {
    lv_obj_set_style_text_color(s_lbl_wifi, C_WARN, 0);
  }
}
