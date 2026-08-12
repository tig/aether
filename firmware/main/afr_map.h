#ifndef AETHER_AFR_MAP_H
#define AETHER_AFR_MAP_H

#include <stdint.h>

/* Dense LED ring — invent within afr-face allow-list (30–40). */
#define AFR_SEG_COUNT 36

#define AFR_STOICH 14.7f
#define AFR_SCALE_MIN 8.0f
#define AFR_SCALE_MAX 20.0f

/* How many contiguous segments lit from the rich end for a valid AFR. */
int afr_map_lit_count(float afr);

/* Normalized 0..1 path position on the LED bezel (same map as lit fill). */
float afr_map_fill_frac(float afr);

/* Segment index for gasoline stoich (14.7) on the progressive fill path. */
int afr_map_stoich_seg(void);

/* Band color for segment index i (0 = rich end … SEG_COUNT-1 = lean). */
uint16_t afr_map_band_color(int seg_index);

/* Soft stoich tick when that segment is not in the lit prefix (afr-face.md). */
uint16_t afr_map_stoich_dim_color(void);

/* Color for the *lit* value of the current mixture (primary digits / unit). */
uint16_t afr_map_value_color(float afr);

/* AFR → lambda (gasoline stoich 14.7). */
float afr_to_lambda(float afr);

#endif
