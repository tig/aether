#ifndef AETHER_FACE_DIAL_H
#define AETHER_FACE_DIAL_H

#include "face_state.h"
#include "lvgl.h"

void face_dial_init(lv_obj_t *parent);
void face_dial_update(const face_state_t *st);

/* Shared canvas for primary stamps (same dial layer). */
uint16_t *face_dial_buf(void);
int face_dial_w(void);
int face_dial_h(void);
void face_dial_invalidate(void);
void face_dial_force_dirty(void); /* bust cache (scene apply) */

#endif
