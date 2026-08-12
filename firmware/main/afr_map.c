#include "afr_map.h"

#include "display.h" /* RGB565 */

#include <math.h>

/* Non-linear AFR → fill fraction. Compress far rich/lean; expand midrange.
 * Control points (AFR → normalized 0..1 path):
 *   8 → 0, 11 → 0.18, 13 → 0.38, 14.7 → 0.52, 15 → 0.56, 17 → 0.80, 20 → 1
 */
static float afr_to_fill(float afr) {
  static const float xa[] = {8.f, 11.f, 13.f, 14.7f, 15.f, 17.f, 20.f};
  static const float ya[] = {0.f, 0.18f, 0.38f, 0.52f, 0.56f, 0.80f, 1.f};
  const int n = (int)(sizeof(xa) / sizeof(xa[0]));
  if (afr <= xa[0]) {
    return ya[0];
  }
  if (afr >= xa[n - 1]) {
    return ya[n - 1];
  }
  for (int i = 0; i < n - 1; i++) {
    if (afr <= xa[i + 1]) {
      const float t = (afr - xa[i]) / (xa[i + 1] - xa[i]);
      return ya[i] + t * (ya[i + 1] - ya[i]);
    }
  }
  return 1.f;
}

float afr_map_fill_frac(float afr) {
  float f = afr_to_fill(afr);
  if (f < 0.f) {
    f = 0.f;
  }
  if (f > 1.f) {
    f = 1.f;
  }
  return f;
}

int afr_map_lit_count(float afr) {
  float f = afr_map_fill_frac(afr);
  int lit = (int)(f * (float)AFR_SEG_COUNT + 0.5f);
  if (lit < 0) {
    lit = 0;
  }
  if (lit > AFR_SEG_COUNT) {
    lit = AFR_SEG_COUNT;
  }
  return lit;
}

int afr_map_stoich_seg(void) {
  /* Segment that contains fill position for 14.7 (ya = 0.52). */
  float f = afr_to_fill(AFR_STOICH);
  int seg = (int)(f * (float)AFR_SEG_COUNT);
  if (seg < 0) {
    seg = 0;
  }
  if (seg >= AFR_SEG_COUNT) {
    seg = AFR_SEG_COUNT - 1;
  }
  return seg;
}

uint16_t afr_map_stoich_dim_color(void) {
  /* Subtle green tick — readable vs unlit gray, not as bright as lit band. */
  return RGB565(48, 110, 68);
}

/* Segment midpoint AFR for band paint (approximate inverse of fill). */
static float seg_mid_afr(int seg_index) {
  static const float xa[] = {8.f, 11.f, 13.f, 14.7f, 15.f, 17.f, 20.f};
  static const float ya[] = {0.f, 0.18f, 0.38f, 0.52f, 0.56f, 0.80f, 1.f};
  const int n = (int)(sizeof(ya) / sizeof(ya[0]));
  float u = ((float)seg_index + 0.5f) / (float)AFR_SEG_COUNT;
  if (u <= ya[0]) {
    return xa[0];
  }
  if (u >= ya[n - 1]) {
    return xa[n - 1];
  }
  for (int i = 0; i < n - 1; i++) {
    if (u <= ya[i + 1]) {
      const float t = (u - ya[i]) / (ya[i + 1] - ya[i]);
      return xa[i] + t * (xa[i + 1] - xa[i]);
    }
  }
  return xa[n - 1];
}

uint16_t afr_map_band_color(int seg_index) {
  const float a = seg_mid_afr(seg_index);
  /* Red rich extreme, green healthy mid, amber lean transition, red lean extreme. */
  if (a < 12.0f) {
    return RGB565(220, 40, 40); /* rich red */
  }
  if (a < 13.5f) {
    return RGB565(40, 200, 70); /* healthy green rising */
  }
  if (a < 15.5f) {
    return RGB565(30, 210, 90); /* stoich neighborhood green */
  }
  if (a < 17.5f) {
    return RGB565(230, 170, 30); /* amber lean */
  }
  return RGB565(220, 40, 40); /* lean red */
}

uint16_t afr_map_value_color(float afr) {
  if (afr < 12.0f) {
    return RGB565(230, 50, 50);
  }
  if (afr < 13.5f) {
    return RGB565(50, 210, 80);
  }
  if (afr < 15.5f) {
    return RGB565(40, 220, 100);
  }
  if (afr < 17.5f) {
    return RGB565(240, 180, 40);
  }
  return RGB565(230, 50, 50);
}

float afr_to_lambda(float afr) { return afr / AFR_STOICH; }
