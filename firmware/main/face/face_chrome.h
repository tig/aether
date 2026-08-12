#ifndef AETHER_FACE_CHROME_H
#define AETHER_FACE_CHROME_H

#include "face_state.h"
#include "lvgl.h"

/* Captions (AFR page) + swipe dots (all pages). */
void face_chrome_init(lv_obj_t *afr_parent, lv_obj_t *dots_parent);
void face_chrome_update(const face_state_t *st);
void face_chrome_set_page(int page);
void face_chrome_set_afr_captions_visible(int show);
void face_chrome_raise_dots(void);

/* Called when operator taps a swipe dot (0..FACE_PAGE_COUNT-1). */
typedef void (*face_chrome_page_cb_t)(int page);
void face_chrome_set_page_cb(face_chrome_page_cb_t cb);

#endif
