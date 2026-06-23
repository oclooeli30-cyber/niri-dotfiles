#pragma once
#include <stdint.h>

typedef struct BlurContext BlurContext;

/* Returns 1 if the compositor supports ext_background_effect_manager_v1, 0 otherwise */
int blur_supported(void *wl_display);

/* Enable blur on a wl_surface. Returns NULL on failure. */
BlurContext* blur_enable(void *wl_display, void *wl_surface);

/* Update the blur region on an existing context.
 * Pass width/height of -1 to cover the full surface. */
void blur_set_region(BlurContext *ctx, int32_t x, int32_t y,
                     int32_t width, int32_t height);

/* Update the blur region using multiple rectangles.
 * xs, ys, widths, heights are parallel arrays of length count. */
void blur_set_regions(BlurContext *ctx,
                      const int32_t *xs, const int32_t *ys,
                      const int32_t *widths, const int32_t *heights,
                      int count);

/* Remove the blur effect (sends NULL region + commit) */
void blur_disable(BlurContext *ctx);

/* Destroy and free the context. Call blur_disable first if needed. */
void blur_free(BlurContext *ctx);
