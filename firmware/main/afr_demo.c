#include "afr_demo.h"

#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static float clampf(float v, float lo, float hi) {
  if (v < lo) {
    return lo;
  }
  if (v > hi) {
    return hi;
  }
  return v;
}

static float lerpf(float a, float b, float t) {
  return a + (b - a) * t;
}

static float smoothstep(float edge0, float edge1, float x) {
  float t = clampf((x - edge0) / (edge1 - edge0), 0.f, 1.f);
  return t * t * (3.f - 2.f * t);
}

/* Phase edges (seconds) from afr-demo.md; ±0.3 s ease allowed. */
enum {
  T_OFF_END = 2,
  T_CRANK_END = 32,   /* 3.2 s * 10 */
  T_IDLE_END = 55,    /* 5.5 */
  T_PULL_END = 80,    /* 8.0 */
  T_WOT2_END = 112,   /* 11.2 */
  T_SHIFT_END = 120,  /* 12.0 */
  T_WOT3_END = 170,   /* 17.0 */
  /* cruise → 30 */
};

static float t10(float sec) { return sec * 10.f; }

void afr_demo_sample(int64_t t_ms, afr_face_state_t *out) {
  if (!out) {
    return;
  }

  int64_t mod = t_ms % (int64_t)DEMO_LOOP_MS;
  if (mod < 0) {
    mod += DEMO_LOOP_MS;
  }
  const float t = (float)mod / 1000.f; /* seconds into loop */
  const float u = t10(t);              /* deci-seconds for phase compares */

  /* page + units are owned by afr_face (nav / banner tap) — demo never sets them. */
  out->mixture_valid = 0;
  out->afr = 14.7f;
  out->rpm = 0;
  out->tps = 0;
  out->logging = 0;
  out->redline_warn = 0;
  /* Leave out->use_lambda / out->page untouched for the face to own. */

  /* Logging off only in early off window; on from ~2 s onward. */
  out->logging = (t >= 2.f) ? 1 : 0;

  if (u < t10(2.f)) {
    /* Off: RPM 0, TPS 0, invalid mixture */
    out->mixture_valid = 0;
    out->rpm = 0;
    out->tps = 0;
    return;
  }

  out->mixture_valid = 1;

  if (u < t10(3.2f)) {
    /* Crank / fire: RPM climbs; AFR appears lean-ish then richward */
    float p = smoothstep(2.f, 3.2f, t);
    out->rpm = (int)lerpf(0.f, 900.f, p);
    out->tps = (int)lerpf(0.f, 8.f, p);
    out->afr = lerpf(16.5f, 13.2f, p);
    return;
  }

  if (u < t10(5.5f)) {
    /* Idle settle ~750, AFR near stoich with wander */
    float p = smoothstep(3.2f, 5.5f, t);
    float wander = 0.15f * sinf(t * 6.f);
    out->rpm = (int)lerpf(900.f, 750.f, p) + (int)(20.f * sinf(t * 4.f));
    out->tps = 4 + (int)(2.f * sinf(t * 3.f));
    out->afr = 14.7f + wander * (0.5f + 0.5f * p);
    return;
  }

  if (u < t10(8.f)) {
    /* Pull 1→2: TPS rises, RPM builds then dips on shift, AFR richer */
    float p = smoothstep(5.5f, 8.f, t);
    float shift = smoothstep(7.2f, 7.8f, t); /* RPM dip */
    out->tps = (int)lerpf(10.f, 70.f, p);
    float rpm_build = lerpf(800.f, 4200.f, p);
    out->rpm = (int)lerpf(rpm_build, 2800.f, shift);
    out->afr = lerpf(14.5f, 12.4f, p);
    return;
  }

  if (u < t10(11.2f)) {
    /* 2nd WOT to redline ~6200 with limiter chatter */
    float p = smoothstep(8.f, 11.2f, t);
    out->tps = 100;
    float rpm = lerpf(3000.f, 6200.f, p);
    if (rpm > 6000.f) {
      rpm += 80.f * sinf(t * 40.f); /* chatter */
      out->redline_warn = 1;
    }
    out->rpm = (int)rpm;
    out->afr = lerpf(12.4f, 11.6f, p);
    return;
  }

  if (u < t10(12.f)) {
    /* Shift 2→3 still WOT, RPM drops */
    float p = smoothstep(11.2f, 12.f, t);
    out->tps = 100;
    out->rpm = (int)lerpf(6100.f, 3800.f, p);
    out->afr = 11.8f;
    out->redline_warn = (out->rpm > 5800);
    return;
  }

  if (u < t10(17.f)) {
    /* 3rd WOT hold ~5 s */
    float p = smoothstep(12.f, 17.f, t);
    out->tps = 100;
    float rpm = lerpf(3800.f, 6000.f, p);
    if (rpm > 5800.f) {
      out->redline_warn = 1;
      rpm += 40.f * sinf(t * 30.f);
    }
    out->rpm = (int)rpm;
    out->afr = lerpf(11.9f, 12.2f, p);
    return;
  }

  /* Cruise: TPS falls, RPM ~2400, AFR → ~14.7 through end of loop.
   * Loop is seamless: t is always mod DEMO_LOOP_S (see afr_demo_sample). */
  {
    float p = smoothstep(17.f, 29.5f, t);
    out->tps = (int)lerpf(100.f, 18.f, p);
    out->rpm = (int)lerpf(5200.f, 2400.f, p) + (int)(30.f * sinf(t * 2.f));
    out->afr = lerpf(12.3f, 14.7f, p) + 0.08f * sinf(t * 3.f);
    out->redline_warn = 0;
  }
}
