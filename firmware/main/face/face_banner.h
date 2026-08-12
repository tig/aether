#ifndef AETHER_FACE_BANNER_H
#define AETHER_FACE_BANNER_H

#include "face_state.h"
#include "lvgl.h"

/* afr_parent: visual MODE/log strip on the AFR tile.
 * chrome_parent: screen-level parent for the units button (outside tileview). */
void face_banner_init(lv_obj_t *afr_parent, lv_obj_t *chrome_parent);
void face_banner_update(const face_state_t *st);
void face_banner_set_units_visible(int show);

/* Tap on the AFR/LAMBDA control (right side of banner). */
typedef void (*face_banner_units_cb_t)(void);
void face_banner_set_units_cb(face_banner_units_cb_t cb);

#endif
