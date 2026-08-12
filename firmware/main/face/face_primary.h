#ifndef AETHER_FACE_PRIMARY_H
#define AETHER_FACE_PRIMARY_H

#include "face_state.h"
#include "lvgl.h"

/* Primary is drawn into the dial canvas layer for now (same buffer).
 * API still separate so primary can move to its own surface later. */
void face_primary_init(lv_obj_t *parent);
void face_primary_update(const face_state_t *st);

#endif
