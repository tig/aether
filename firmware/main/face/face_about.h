#ifndef AETHER_FACE_ABOUT_H
#define AETHER_FACE_ABOUT_H

#include "face_state.h"
#include "lvgl.h"

void face_about_init(lv_obj_t *parent);
void face_about_show(int show);
void face_about_update(const face_state_t *st);
lv_obj_t *face_about_root(void);

#endif
