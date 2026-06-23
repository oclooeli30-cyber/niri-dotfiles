#include "blur.h"
#include "ext-background-effect-v1-client-protocol.h"

#include <wayland-client.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>


static struct wl_compositor                    *g_compositor   = NULL;
static struct ext_background_effect_manager_v1 *g_blur_manager = NULL;
static struct wl_registry                      *g_registry     = NULL;

typedef struct {
    struct wl_compositor                    *compositor;
    struct ext_background_effect_manager_v1 *blur_manager;
    int                                      blur_supported;
} RegistryData;

static void registry_handle_global(
        void *data, struct wl_registry *registry,
        uint32_t name, const char *interface, uint32_t version)
{
    RegistryData *rd = data;

    if (strcmp(interface, wl_compositor_interface.name) == 0) {
        rd->compositor = wl_registry_bind(registry, name,
                                          &wl_compositor_interface,
                                          (version < 4 ? version : 4));
    } else if (strcmp(interface,
                      ext_background_effect_manager_v1_interface.name) == 0) {
        rd->blur_manager = wl_registry_bind(registry, name,
                                            &ext_background_effect_manager_v1_interface,
                                            1);
        rd->blur_supported = 1;
    }
}

static void registry_handle_global_remove(
        void *data, struct wl_registry *registry, uint32_t name)
{
    (void)data; (void)registry; (void)name;
}

static const struct wl_registry_listener registry_listener = {
    .global        = registry_handle_global,
    .global_remove = registry_handle_global_remove,
};

static struct wl_registry *bind_registry(struct wl_display *display,
                                         RegistryData *rd)
{
    struct wl_registry *registry = wl_display_get_registry(display);
    if (!registry) return NULL;

    wl_registry_add_listener(registry, &registry_listener, rd);
    wl_display_roundtrip(display);

    return registry;
}

struct BlurContext {
    struct wl_display                       *display;
    struct wl_surface                       *surface;
    struct wl_registry                      *registry;
    struct wl_compositor                    *compositor;
    struct ext_background_effect_manager_v1 *manager;
    struct ext_background_effect_surface_v1 *effect;
};


int blur_supported(void *wl_display)
{
    RegistryData rd = {0};
    struct wl_registry *registry = bind_registry((struct wl_display *)wl_display, &rd);
    if (!registry) return 0;

    int supported = rd.blur_supported;

    if (rd.compositor)   wl_compositor_destroy(rd.compositor);
    if (rd.blur_manager) ext_background_effect_manager_v1_destroy(rd.blur_manager);
    wl_registry_destroy(registry);

    return supported;
}

BlurContext *blur_enable(void *wl_display, void *wl_surface)
{
    if (!g_registry) {
        RegistryData rd = {0};
        g_registry = bind_registry((struct wl_display *)wl_display, &rd);
        if (!g_registry) {
            fprintf(stderr, "[blur] failed to get registry\n");
            return NULL;
        }
        g_compositor   = rd.compositor;
        g_blur_manager = rd.blur_manager;
    }

    if (!g_blur_manager) {
        fprintf(stderr, "[blur] compositor does not support ext_background_effect_manager_v1\n");
        return NULL;
    }

    if (!g_compositor) {
        fprintf(stderr, "[blur] wl_compositor not found in registry\n");
        return NULL;
    }

    BlurContext *ctx = calloc(1, sizeof(BlurContext));
    if (!ctx) return NULL;

    ctx->display    = (struct wl_display *)wl_display;
    ctx->surface    = (struct wl_surface *)wl_surface;
    ctx->registry   = g_registry;
    ctx->compositor = g_compositor;
    ctx->manager    = g_blur_manager;

    ctx->effect = ext_background_effect_manager_v1_get_background_effect(
        ctx->manager, ctx->surface);

    if (!ctx->effect) {
        fprintf(stderr, "[blur] failed to get background effect object\n");
        free(ctx);
        return NULL;
    }

    blur_set_region(ctx, 0, 0, INT32_MAX, INT32_MAX);

    return ctx;
}

void blur_set_region(BlurContext *ctx, int32_t x, int32_t y,
                     int32_t width, int32_t height)
{
    if (!ctx || !ctx->effect) return;

    struct wl_region *region = wl_compositor_create_region(ctx->compositor);
    if (!region) {
        fprintf(stderr, "[blur] failed to create wl_region\n");
        return;
    }

    wl_region_add(region, x, y, width, height);
    ext_background_effect_surface_v1_set_blur_region(ctx->effect, region);
    wl_region_destroy(region);
    wl_surface_commit(ctx->surface);
}

void blur_set_regions(BlurContext *ctx,
                      const int32_t *xs, const int32_t *ys,
                      const int32_t *widths, const int32_t *heights,
                      int count)
{
    if (!ctx || !ctx->effect || count <= 0) return;

    struct wl_region *region = wl_compositor_create_region(ctx->compositor);
    if (!region) {
        fprintf(stderr, "[blur] failed to create wl_region\n");
        return;
    }

    for (int i = 0; i < count; i++)
        wl_region_add(region, xs[i], ys[i], widths[i], heights[i]);

    ext_background_effect_surface_v1_set_blur_region(ctx->effect, region);
    wl_region_destroy(region);
    wl_surface_commit(ctx->surface);
}

void blur_disable(BlurContext *ctx)
{
    if (!ctx || !ctx->effect) return;
    ext_background_effect_surface_v1_set_blur_region(ctx->effect, NULL);
    wl_surface_commit(ctx->surface);
}

void blur_free(BlurContext *ctx)
{
    if (!ctx) return;
    if (ctx->effect) ext_background_effect_surface_v1_destroy(ctx->effect);
    free(ctx);
}