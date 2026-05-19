/*
 * lingot, a musical instrument tuner.
 *
 * Copyright (C) 2004-2020  Iban Cereijo.
 * Copyright (C) 2004-2008  Jairo Chapela.
 *
 * This file is part of lingot.
 *
 * lingot is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifdef HAVE_CONFIG_H
#  include "config.h"
#endif

#include "lingot-audio-alsa.h"
#include "lingot-audio-jack.h"
#include "lingot-audio-oss.h"
#include "lingot-audio-pulseaudio.h"
#include "lingot-config-scale.h"
#include "lingot-config.h"
#include "lingot-core.h"
#include "lingot-io-config.h"
#include "lingot-io-ui-settings.h"
#include "lingot-pyqt-api.h"

struct lingot_pyqt_context_t {
    lingot_config_t conf;
    lingot_core_t core;
    int core_created;
};

static int initialized = 0;

static int lingot_pyqt_mkdir_if_missing(const char* path) {
    if (mkdir(path, 0777) == 0 || errno == EEXIST) {
        return 0;
    }
    return -1;
}

int lingot_pyqt_initialize(const char* config_name) {
    const char* home = getenv("HOME");
    char config_dir[512];
    char xdg_config_dir[512];

    if (!home) {
        return -1;
    }

    snprintf(xdg_config_dir, sizeof(xdg_config_dir), "%s/.config", home);
    if (lingot_pyqt_mkdir_if_missing(xdg_config_dir) != 0) {
        return -1;
    }

    snprintf(config_dir, sizeof(config_dir), "%s/%s", home, LINGOT_CONFIG_DIR_NAME);
    if (lingot_pyqt_mkdir_if_missing(config_dir) != 0) {
        return -1;
    }

    if (config_name && config_name[0]) {
        snprintf(LINGOT_CONFIG_FILE_NAME, sizeof(LINGOT_CONFIG_FILE_NAME),
                 "%s/%s%s.conf", home, LINGOT_CONFIG_DIR_NAME, config_name);
    } else {
        snprintf(LINGOT_CONFIG_FILE_NAME, sizeof(LINGOT_CONFIG_FILE_NAME),
                 "%s/" LINGOT_CONFIG_DIR_NAME LINGOT_DEFAULT_CONFIG_FILE_NAME, home);
    }

    snprintf(LINGOT_UI_SETTINGS_FILE_NAME, sizeof(LINGOT_UI_SETTINGS_FILE_NAME),
             "%s/" LINGOT_CONFIG_DIR_NAME LINGOT_DEFAULT_UI_SETTINGS_FILE_NAME, home);

    if (!initialized) {
        lingot_audio_oss_register();
        lingot_audio_alsa_register();
        lingot_audio_pulseaudio_register();
        lingot_audio_jack_register();
        lingot_io_config_create_parameter_specs();
        initialized = 1;
    }

    FILE* fp = fopen(LINGOT_CONFIG_FILE_NAME, "r");
    if (!fp) {
        lingot_config_t new_conf;
        lingot_config_new(&new_conf);
        lingot_config_restore_default_values(&new_conf);
        lingot_io_config_save(&new_conf, LINGOT_CONFIG_FILE_NAME);
        lingot_config_destroy(&new_conf);
    } else {
        fclose(fp);
    }

    lingot_io_ui_settings_init();

    return 0;
}

lingot_pyqt_context_t* lingot_pyqt_context_new(void) {
    lingot_pyqt_context_t* context = malloc(sizeof(lingot_pyqt_context_t));
    if (!context) {
        return NULL;
    }

    context->core_created = 0;
    context->core.core_private = NULL;
    lingot_config_new(&context->conf);
    if (!lingot_io_config_load(&context->conf, LINGOT_CONFIG_FILE_NAME)) {
        lingot_config_restore_default_values(&context->conf);
    }

    return context;
}

void lingot_pyqt_context_destroy(lingot_pyqt_context_t* context) {
    if (!context) {
        return;
    }
    lingot_pyqt_context_stop(context);
    lingot_config_destroy(&context->conf);
    free(context);
}

int lingot_pyqt_context_load_config(lingot_pyqt_context_t* context,
                                    const char* filename) {
    if (!context || !filename) {
        return -1;
    }
    lingot_pyqt_context_stop(context);
    return lingot_io_config_load(&context->conf, filename) ? 0 : -1;
}

int lingot_pyqt_context_save_config(lingot_pyqt_context_t* context,
                                    const char* filename) {
    if (!context || !filename) {
        return -1;
    }
    return lingot_io_config_save(&context->conf, filename) ? 0 : -1;
}

int lingot_pyqt_context_start(lingot_pyqt_context_t* context) {
    if (!context) {
        return -1;
    }
    if (context->core_created) {
        return 0;
    }

    lingot_core_new(&context->core, &context->conf);
    context->core_created = 1;
    lingot_core_thread_start(&context->core);
    return 0;
}

void lingot_pyqt_context_stop(lingot_pyqt_context_t* context) {
    if (!context || !context->core_created) {
        return;
    }
    lingot_core_thread_stop(&context->core);
    lingot_core_destroy(&context->core);
    context->core_created = 0;
}

int lingot_pyqt_context_restart(lingot_pyqt_context_t* context) {
    if (!context) {
        return -1;
    }
    lingot_pyqt_context_stop(context);
    return lingot_pyqt_context_start(context);
}

int lingot_pyqt_context_get_snapshot(lingot_pyqt_context_t* context,
                                     lingot_pyqt_snapshot_t* snapshot) {
    if (!context || !snapshot) {
        return -1;
    }

    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->running = context->core_created
            ? lingot_core_thread_is_running(&context->core)
            : 0;
    snapshot->spectrum_size = context->conf.fft_size / 2;

    if (!context->core_created) {
        snapshot->frequency = 0.0;
        snapshot->error_cents = NAN;
        snapshot->closest_note_index = -1;
        return 0;
    }

    snapshot->frequency = lingot_core_thread_get_result_frequency(&context->core);
    if (isnan(snapshot->frequency)
            || snapshot->frequency <= context->conf.internal_min_frequency) {
        snapshot->error_cents = NAN;
        snapshot->closest_note_index = -1;
        return 0;
    }

    snapshot->closest_note_index = lingot_config_scale_get_closest_note_index(
                &context->conf.scale,
                snapshot->frequency,
                context->conf.root_frequency_error,
                &snapshot->error_cents);
    if (snapshot->closest_note_index >= 0 && context->conf.scale.note_name) {
        const int note_index = lingot_config_scale_get_note_index(
                    &context->conf.scale, snapshot->closest_note_index);
        snapshot->closest_note_name = context->conf.scale.note_name[note_index];
    }

    return 0;
}

unsigned int lingot_pyqt_context_copy_spectrum(lingot_pyqt_context_t* context,
                                               LINGOT_FLT* dst,
                                               unsigned int dst_len) {
    if (!context || !context->core_created || !dst || dst_len == 0) {
        return 0;
    }
    if (!lingot_core_thread_is_running(&context->core)) {
        return 0;
    }

    const unsigned int spectrum_size = context->conf.fft_size / 2;
    const unsigned int copy_len = dst_len < spectrum_size ? dst_len : spectrum_size;
    LINGOT_FLT* spectrum = lingot_core_thread_get_result_spd(&context->core);
    if (!spectrum) {
        return 0;
    }

    memcpy(dst, spectrum, copy_len * sizeof(LINGOT_FLT));
    return copy_len;
}

int lingot_pyqt_pop_message(char* dst,
                            unsigned int dst_len,
                            lingot_msg_type_t* type,
                            int* error_code) {
    char buff[LINGOT_MSG_MAX_SIZE + 1];
    int result;

    if (!dst || dst_len == 0 || !type || !error_code) {
        return 0;
    }

    result = lingot_msg_pop(buff, type, error_code);
    if (!result) {
        dst[0] = '\0';
        return 0;
    }

    buff[LINGOT_MSG_MAX_SIZE] = '\0';
    snprintf(dst, dst_len, "%s", buff);
    return result;
}

const char* lingot_pyqt_config_filename(void) {
    return LINGOT_CONFIG_FILE_NAME;
}

const char* lingot_pyqt_ui_settings_filename(void) {
    return LINGOT_UI_SETTINGS_FILE_NAME;
}
