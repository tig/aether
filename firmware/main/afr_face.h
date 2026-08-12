#ifndef AETHER_AFR_FACE_H
#define AETHER_AFR_FACE_H

#include <stdint.h>

typedef struct {
  int mixture_valid;
  float afr;
  int use_lambda;
  int rpm;
  int tps;
  int logging;
  int page;
  int redline_warn;
} afr_face_state_t;

void afr_face_init(void);
void afr_face_update(const afr_face_state_t *st);
void afr_face_handler(void);

/* Multi-page: 0=AFR, 1=SETTINGS, 2=ABOUT. */
void afr_face_set_page(int page);
int afr_face_page(void);

/* Scene freeze for esprec element harness (specs/face-elements.md). */
int afr_face_apply_scene(const char *scene_id); /* 0 ok, -1 unknown */
void afr_face_live(void);
int afr_face_scene_hold(void);

#endif
