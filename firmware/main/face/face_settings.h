#ifndef AETHER_FACE_SETTINGS_H
#define AETHER_FACE_SETTINGS_H

#include "face_state.h"
#include "lvgl.h"

void face_settings_init(lv_obj_t *parent);
void face_settings_show(int show);
void face_settings_update(const face_state_t *st);
lv_obj_t *face_settings_root(void);

#endif
