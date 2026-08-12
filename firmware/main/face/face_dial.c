/* Element: dial — LED bezel + scale marks (no primary digits).
 * Primary is a separate LVGL label layer so it owns the aperture.
 *
 * Bezel: fill everything outside the rounded-rect inner hole except the open
 * bottom mid-span (L → top → R only). That keeps soft inner corners.
 */
#include "face_dial.h"

#include "afr_map.h"
#include "display.h"
#include "fonts/aether_fonts.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

/* Thicker bezel on 4.3″ so band reads at a glance. */
#define LED_THICK 38
#define INNER_R 56

static lv_obj_t *s_canvas;
static uint16_t *s_buf;
static int s_w, s_h;
static int s_last_lit = -1;
static int s_last_valid = -1;
static int s_last_lambda = -1;
static float s_last_afr = -999.f;
static lv_obj_t *s_marks[6];
#define MARK_N 6

/*
 * Legend placement uses the *aperture* polyline that already looked good for
 * AFR (L wall → top → R wall), parameterized by LED fill fraction u.
 * That way λ marks share the same visual path as AFR marks, and 1.00 (u of
 * AFR 14.7) lands on the stoich segment without gluing labels to outer LEDs.
 */
static const struct {
  float u;  /* afr_map_fill_frac at this knot */
  float fx; /* aperture-normalized 0..1 */
  float fy;
} s_path[] = {
    {0.00f, 0.04f, 0.80f}, /* AFR 8  / rich end, lower left */
    {0.18f, 0.04f, 0.40f}, /* AFR 11 */
    {0.38f, 0.32f, 0.14f}, /* AFR 13 */
    {0.52f, 0.50f, 0.14f}, /* stoich 14.7 — top center (λ 1.00) */
    {0.56f, 0.68f, 0.14f}, /* AFR 15 */
    {0.80f, 0.96f, 0.40f}, /* AFR 17 */
    {1.00f, 0.96f, 0.80f}, /* AFR 20 / lean end, lower right */
};
#define PATH_N ((int)(sizeof s_path / sizeof s_path[0]))

/* AFR mark values (match fill knots except we omit explicit 14.7). */
static const float s_afr_marks[MARK_N] = {8.f, 11.f, 13.f, 15.f, 17.f, 20.f};
/* λ-native scale — spaced for readable path positions around 1.00. */
static const float s_lam_marks[MARK_N] = {0.70f, 0.85f, 1.00f, 1.10f, 1.20f,
                                         1.35f};

static void fill_u_to_fx_fy(float u, float *fx, float *fy) {
  if (u <= s_path[0].u) {
    *fx = s_path[0].fx;
    *fy = s_path[0].fy;
    return;
  }
  if (u >= s_path[PATH_N - 1].u) {
    *fx = s_path[PATH_N - 1].fx;
    *fy = s_path[PATH_N - 1].fy;
    return;
  }
  for (int i = 0; i < PATH_N - 1; i++) {
    if (u <= s_path[i + 1].u) {
      float du = s_path[i + 1].u - s_path[i].u;
      float t = du > 1e-6f ? (u - s_path[i].u) / du : 0.f;
      *fx = s_path[i].fx + t * (s_path[i + 1].fx - s_path[i].fx);
      *fy = s_path[i].fy + t * (s_path[i + 1].fy - s_path[i].fy);
      return;
    }
  }
  *fx = s_path[PATH_N - 1].fx;
  *fy = s_path[PATH_N - 1].fy;
}

static void place_mark_at(int i, float fx, float fy) {
  if (!s_marks[i] || s_w <= 0 || s_h <= 0) {
    return;
  }
  float ox0 = 0, oy0 = 0, ox1 = (float)(s_w - 1), oy1 = (float)(s_h - 1);
  float ix0 = ox0 + LED_THICK, iy0 = oy0 + LED_THICK;
  float ix1 = ox1 - LED_THICK, iy1 = oy1 - LED_THICK;
  const int pad = 4;
  int mx = (int)(ix0 + fx * (ix1 - ix0));
  int my = (int)(iy0 + fy * (iy1 - iy0));
  lv_obj_update_layout(s_marks[i]);
  lv_coord_t tw = lv_obj_get_width(s_marks[i]);
  lv_coord_t th = lv_obj_get_height(s_marks[i]);
  int x;
  if (fx < 0.25f) {
    x = (int)ix0 + pad;
  } else if (fx > 0.75f) {
    x = (int)ix1 - pad - (int)tw;
  } else {
    x = mx - (int)tw / 2;
  }
  int y = FACE_DIAL_Y0 + my - (int)th / 2;
  lv_obj_set_pos(s_marks[i], x, y);
}

static void apply_marks(int use_lambda) {
  char lab[8];
  for (int i = 0; i < MARK_N; i++) {
    if (!s_marks[i]) {
      continue;
    }
    float afr;
    if (use_lambda) {
      snprintf(lab, sizeof lab, "%.2f", (double)s_lam_marks[i]);
      afr = s_lam_marks[i] * AFR_STOICH;
    } else {
      snprintf(lab, sizeof lab, "%d", (int)(s_afr_marks[i] + 0.5f));
      afr = s_afr_marks[i];
    }
    lv_label_set_text(s_marks[i], lab);
    float fx, fy;
    fill_u_to_fx_fy(afr_map_fill_frac(afr), &fx, &fy);
    place_mark_at(i, fx, fy);
  }
}

uint16_t *face_dial_buf(void) { return s_buf; }
int face_dial_w(void) { return s_w; }
int face_dial_h(void) { return s_h; }
void face_dial_invalidate(void) {
  if (s_canvas) {
    lv_obj_invalidate(s_canvas);
  }
}

void face_dial_force_dirty(void) {
  s_last_lit = -1;
  s_last_valid = -1;
  s_last_lambda = -1;
  s_last_afr = -999.f;
}

static void put(int x, int y, uint16_t c) {
  if ((unsigned)x < (unsigned)s_w && (unsigned)y < (unsigned)s_h) {
    s_buf[y * s_w + x] = c;
  }
}

/* Soft rounded-rect hole (inner wall of the LED bezel). */
static int inside_rr(float px, float py, float x0, float y0, float x1, float y1,
                     float r) {
  if (px < x0 || px > x1 || py < y0 || py > y1) {
    return 0;
  }
  float lx = x0 + r, rx = x1 - r, ty = y0 + r, by = y1 - r;
  if (px >= lx && px <= rx) {
    return 1;
  }
  if (py >= ty && py <= by) {
    return 1;
  }
  float qx = px < lx ? lx : rx;
  float qy = py < ty ? ty : by;
  float dx = px - qx, dy = py - qy;
  return (dx * dx + dy * dy) <= (r * r);
}

static void paint_leds(int lit, int valid) {
  const uint16_t black = RGB565(0, 0, 0);
  const uint16_t unlit = RGB565(58, 64, 76);
  const uint16_t hair = RGB565(8, 8, 12);
  const uint16_t stoich_dim = afr_map_stoich_dim_color();
  const int stoich_seg = afr_map_stoich_seg();
  for (int i = 0; i < s_w * s_h; i++) {
    s_buf[i] = black;
  }

  float ox0 = 0, oy0 = 0, ox1 = (float)(s_w - 1), oy1 = (float)(s_h - 1);
  float ix0 = ox0 + LED_THICK, iy0 = oy0 + LED_THICK;
  float ix1 = ox1 - LED_THICK, iy1 = oy1 - LED_THICK;
  /*
   * Path is L → top → R, ending at the *bottom of the aperture* (iy1), not the
   * dial canvas bottom. That drops the first/last feet that sat above RPM/TPS
   * while keeping the rounded-rect inner hole.
   */
  float left_len = iy1 - oy0; /* vertical run stops at aperture bottom */
  float top_len = ox1 - ox0;
  float path_len = left_len + top_len + left_len;
  float gap = 0.035f;

  for (int y = 0; y < s_h; y++) {
    for (int x = 0; x < s_w; x++) {
      float px = (float)x, py = (float)y;

      /* Inner hole — rounded rect (soft inner corners). */
      if (inside_rr(px, py, ix0, iy0, ix1, iy1, (float)INNER_R)) {
        continue;
      }

      /* No LEDs below the aperture bottom — open bottom + no BL/BR feet. */
      if (py > iy1) {
        continue;
      }

      /* Map pixel → L / top / R wall for segment index. */
      float dL = px - ox0, dR = ox1 - px, dT = py - oy0;
      int wall = 0;
      float best = dL;
      if (dT < best) {
        best = dT;
        wall = 1;
      }
      if (dR < best) {
        wall = 2;
      }

      float s = (wall == 0)   ? (iy1 - py)              /* aperture bottom → top */
                : (wall == 1) ? (left_len + (px - ox0)) /* left → right */
                              : (left_len + top_len + (py - oy0)); /* top → bot */

      float u = s / path_len;
      if (u < 0.f || u > 1.f) {
        continue;
      }
      float seg_f = u * (float)AFR_SEG_COUNT;
      int seg = (int)seg_f;
      if (seg < 0) {
        seg = 0;
      }
      if (seg >= AFR_SEG_COUNT) {
        seg = AFR_SEG_COUNT - 1;
      }
      float local = seg_f - (float)seg;
      if (local < gap * 0.5f || local > 1.f - gap * 0.5f) {
        put(x, y, hair);
        continue;
      }
      /* Progressive lit band; else soft stoich tick; else dim unlit. */
      uint16_t c = unlit;
      if (valid && seg < lit) {
        c = afr_map_band_color(seg);
      } else if (seg == stoich_seg) {
        c = stoich_dim;
      }
      put(x, y, c);
    }
  }
  face_dial_invalidate();
}

void face_dial_init(lv_obj_t *parent) {
  s_w = FACE_W;
  s_h = FACE_DIAL_H;
  s_buf = display_alloc_canvas(s_w, s_h);
  s_canvas = lv_canvas_create(parent);
  lv_obj_clear_flag(s_canvas, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_clear_flag(s_canvas, LV_OBJ_FLAG_CLICKABLE); /* decorative; swipe through */
  lv_obj_set_style_pad_all(s_canvas, 0, 0);
  lv_obj_set_style_border_width(s_canvas, 0, 0);
  lv_obj_set_pos(s_canvas, 0, FACE_DIAL_Y0);
  if (s_buf) {
    lv_canvas_set_buffer(s_canvas, s_buf, s_w, s_h, LV_COLOR_FORMAT_RGB565);
    paint_leds(0, 0);
  }

  for (int i = 0; i < MARK_N; i++) {
    s_marks[i] = lv_label_create(parent);
    lv_obj_set_style_text_font(s_marks[i], &font_aether_unit_36, 0);
    lv_obj_set_style_text_color(s_marks[i], lv_color_make(160, 170, 185), 0);
  }
  apply_marks(0);
  s_last_lambda = 0;
}

void face_dial_update(const face_state_t *st) {
  if (!st || !s_buf) {
    return;
  }
  int lit = st->mixture_valid ? afr_map_lit_count(st->afr) : 0;
  int marks_dirty = (st->use_lambda != s_last_lambda);
  if (lit == s_last_lit && st->mixture_valid == s_last_valid &&
      fabsf(st->afr - s_last_afr) < 0.02f && !marks_dirty) {
    return;
  }
  if (marks_dirty) {
    apply_marks(st->use_lambda);
    s_last_lambda = st->use_lambda;
  }
  paint_leds(lit, st->mixture_valid);
  s_last_lit = lit;
  s_last_valid = st->mixture_valid;
  s_last_afr = st->afr;
}
