#ifndef AETHER_AFR_DEMO_H
#define AETHER_AFR_DEMO_H

#include "afr_face.h"

#include <stdint.h>

/* Hard rule from afr-demo.md — not inventable. */
#define DEMO_LOOP_S 30
#define DEMO_LOOP_MS (DEMO_LOOP_S * 1000)

/* Sample demo state at t_ms into the seamless 30 s loop (mod DEMO_LOOP_MS). */
void afr_demo_sample(int64_t t_ms, afr_face_state_t *out);

#endif
