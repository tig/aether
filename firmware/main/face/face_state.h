#ifndef AETHER_FACE_STATE_H
#define AETHER_FACE_STATE_H

#include <stdint.h>

/* Shared product-face state (demo, live, and named esprec scenes). */

typedef struct {
  int mixture_valid; /* 0 = invalid / dashed */
  float afr;         /* gasoline-scale AFR when valid */
  int use_lambda;    /* 0 = show AFR, 1 = show λ / L */
  int rpm;
  int tps;           /* 0..100; ≥100 → WOT label */
  int logging;       /* 0/1 */
  int page;          /* 0=AFR, 1=SETTINGS, 2=ABOUT */
  int redline_warn;  /* RPM near/over redline */
} face_state_t;

/* Pages (swipe dots). */
#define FACE_PAGE_AFR 0
#define FACE_PAGE_SETTINGS 1
#define FACE_PAGE_ABOUT 2
#define FACE_PAGE_COUNT 3

/* Layout constants (logical 800×480 landscape 4.3″) — single source.
 * Dial owns most of the height (critical: not a short ribbon). */
#define FACE_BANNER_H 48
#define FACE_AUX_H 108
#define FACE_DIAL_Y0 FACE_BANNER_H
#define FACE_DIAL_H (480 - FACE_BANNER_H - FACE_AUX_H) /* 324 */
#define FACE_AUX_Y0 (FACE_BANNER_H + FACE_DIAL_H)

/* Element focus (future: dim non-focus). 0 = all. */
typedef enum {
  FACE_EL_ALL = 0,
  FACE_EL_BANNER,
  FACE_EL_DIAL,
  FACE_EL_PRIMARY,
  FACE_EL_AUX,
  FACE_EL_CHROME,
} face_element_t;

#endif
