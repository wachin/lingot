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
#include "lingot-audio.h"
#include "lingot-config-scale.h"
#include "lingot-config.h"
#include "lingot-core.h"
#include "lingot-io-config.h"
#include "lingot-io-config-scale.h"
#include "lingot-io-ui-settings.h"
#include "lingot-pyqt-api.h"

struct lingot_pyqt_context_t {
    lingot_config_t conf;
    lingot_core_t core;
    int core_created;
};

static int initialized = 0;

static char* lingot_pyqt_strdup(const char* src) {
    size_t len = strlen(src) + 1;
    char* dst = malloc(len);
    if (dst) {
        memcpy(dst, src, len);
    }
    return dst;
}

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

int lingot_pyqt_context_get_config_values(lingot_pyqt_context_t* context,
                                          lingot_pyqt_config_values_t* values) {
    if (!context || !values) {
        return -1;
    }

    memset(values, 0, sizeof(*values));
    values->audio_system_index = context->conf.audio_system_index;
    values->fft_size = context->conf.fft_size;
    values->temporal_window = context->conf.temporal_window;
    values->min_overall_snr = context->conf.min_overall_SNR;
    values->calculation_rate = context->conf.calculation_rate;
    values->min_frequency = context->conf.min_frequency;
    values->max_frequency = context->conf.max_frequency;
    values->root_frequency_error = context->conf.root_frequency_error;
    values->optimize_internal_parameters = context->conf.optimize_internal_parameters;
    return 0;
}

int lingot_pyqt_context_set_config_values(lingot_pyqt_context_t* context,
                                          const lingot_pyqt_config_values_t* values) {
    if (!context || !values) {
        return -1;
    }
    if (values->min_frequency < 0.0
            || values->max_frequency <= values->min_frequency
            || values->calculation_rate <= 0.0
            || values->temporal_window < 0.0
            || values->fft_size < 256) {
        return -1;
    }

    context->conf.audio_system_index = values->audio_system_index;
    context->conf.fft_size = values->fft_size;
    context->conf.temporal_window = values->temporal_window;
    context->conf.min_overall_SNR = values->min_overall_snr;
    context->conf.calculation_rate = values->calculation_rate;
    context->conf.min_frequency = values->min_frequency;
    context->conf.max_frequency = values->max_frequency;
    context->conf.root_frequency_error = values->root_frequency_error;
    context->conf.optimize_internal_parameters = values->optimize_internal_parameters;
    lingot_config_update_internal_params(&context->conf);
    return 0;
}

int lingot_pyqt_context_get_audio_device(lingot_pyqt_context_t* context,
                                         char* dst,
                                         unsigned int dst_len) {
    if (!context || !dst || dst_len == 0) {
        return -1;
    }
    const int index = context->conf.audio_system_index;
    if (index < 0 || index >= N_MAX_AUDIO_DEV) {
        dst[0] = '\0';
        return -1;
    }
    snprintf(dst, dst_len, "%s", context->conf.audio_dev[index]);
    return 0;
}

int lingot_pyqt_context_set_audio_device(lingot_pyqt_context_t* context,
                                         const char* device) {
    if (!context || !device) {
        return -1;
    }
    const int index = context->conf.audio_system_index;
    if (index < 0 || index >= N_MAX_AUDIO_DEV) {
        return -1;
    }
    snprintf(context->conf.audio_dev[index], sizeof(context->conf.audio_dev[index]),
             "%s", device);
    return 0;
}

int lingot_pyqt_context_get_scale_info(lingot_pyqt_context_t* context,
                                       char* name_dst,
                                       unsigned int name_dst_len,
                                       LINGOT_FLT* base_frequency,
                                       unsigned int* notes) {
    if (!context || !name_dst || name_dst_len == 0 || !base_frequency || !notes) {
        return -1;
    }
    snprintf(name_dst, name_dst_len, "%s",
             context->conf.scale.name ? context->conf.scale.name : "");
    *base_frequency = context->conf.scale.base_frequency;
    *notes = context->conf.scale.notes;
    return 0;
}

int lingot_pyqt_context_get_scale_note(lingot_pyqt_context_t* context,
                                       unsigned int index,
                                       char* name_dst,
                                       unsigned int name_dst_len,
                                       char* shift_dst,
                                       unsigned int shift_dst_len,
                                       LINGOT_FLT* cents) {
    if (!context || !name_dst || name_dst_len == 0
            || !shift_dst || shift_dst_len == 0 || !cents
            || index >= context->conf.scale.notes) {
        return -1;
    }
    snprintf(name_dst, name_dst_len, "%s",
             context->conf.scale.note_name[index]
                ? context->conf.scale.note_name[index] : "");
    lingot_config_scale_format_shift(shift_dst,
                                     context->conf.scale.offset_cents[index],
                                     context->conf.scale.offset_ratios[0][index],
                                     context->conf.scale.offset_ratios[1][index]);
    *cents = context->conf.scale.offset_cents[index];
    return 0;
}

int lingot_pyqt_context_set_scale(lingot_pyqt_context_t* context,
                                  const char* name,
                                  LINGOT_FLT base_frequency,
                                  unsigned int notes,
                                  const char** note_names,
                                  const LINGOT_FLT* cents) {
    if (!context || !name || !note_names || !cents
            || notes < 1 || notes > 128 || base_frequency <= 0.0) {
        return -1;
    }
    if (fabs(cents[0]) > 1e-10) {
        return -1;
    }

    LINGOT_FLT last_cents = -1.0;
    unsigned int i;
    for (i = 0; i < notes; i++) {
        if (!note_names[i] || !note_names[i][0]
                || strchr(note_names[i], ' ')
                || strchr(note_names[i], '\t')
                || strchr(note_names[i], '\n')
                || strchr(note_names[i], '{')
                || strchr(note_names[i], '}')) {
            return -1;
        }
        if (cents[i] < last_cents || cents[i] >= 1200.0) {
            return -1;
        }
        unsigned int j;
        for (j = i + 1; j < notes; j++) {
            if (note_names[j] && strcmp(note_names[i], note_names[j]) == 0) {
                return -1;
            }
        }
        last_cents = cents[i];
    }

    lingot_config_scale_destroy(&context->conf.scale);
    context->conf.scale.name = lingot_pyqt_strdup(name);
    lingot_config_scale_allocate(&context->conf.scale, (unsigned short int) notes);
    context->conf.scale.base_frequency = base_frequency;

    for (i = 0; i < notes; i++) {
        context->conf.scale.note_name[i] = lingot_pyqt_strdup(note_names[i]);
        context->conf.scale.offset_cents[i] = cents[i];
        context->conf.scale.offset_ratios[0][i] = -1;
        context->conf.scale.offset_ratios[1][i] = -1;
    }
    context->conf.scale.offset_ratios[0][0] = 1;
    context->conf.scale.offset_ratios[1][0] = 1;
    lingot_config_update_internal_params(&context->conf);
    return 0;
}

int lingot_pyqt_context_set_scale_shifts(lingot_pyqt_context_t* context,
                                         const char* name,
                                         LINGOT_FLT base_frequency,
                                         unsigned int notes,
                                         const char** note_names,
                                         const char** shifts) {
    if (!context || !name || !note_names || !shifts
            || notes < 1 || notes > 128 || base_frequency <= 0.0) {
        return -1;
    }

    LINGOT_FLT* cents = malloc(notes * sizeof(LINGOT_FLT));
    short int* numerators = malloc(notes * sizeof(short int));
    short int* denominators = malloc(notes * sizeof(short int));
    if (!cents || !numerators || !denominators) {
        free(cents);
        free(numerators);
        free(denominators);
        return -1;
    }

    LINGOT_FLT last_cents = -1.0;
    unsigned int i;
    for (i = 0; i < notes; i++) {
        char shift_buff[128];
        if (!note_names[i] || !note_names[i][0] || !shifts[i]
                || strchr(note_names[i], ' ')
                || strchr(note_names[i], '\t')
                || strchr(note_names[i], '\n')
                || strchr(note_names[i], '{')
                || strchr(note_names[i], '}')) {
            free(cents);
            free(numerators);
            free(denominators);
            return -1;
        }
        snprintf(shift_buff, sizeof(shift_buff), "%s", shifts[i]);
        if (!lingot_config_scale_parse_shift(shift_buff, &cents[i],
                                             &numerators[i], &denominators[i])) {
            free(cents);
            free(numerators);
            free(denominators);
            return -1;
        }
        if ((i == 0 && fabs(cents[i]) > 1e-10)
                || cents[i] < last_cents || cents[i] >= 1200.0) {
            free(cents);
            free(numerators);
            free(denominators);
            return -1;
        }
        unsigned int j;
        for (j = i + 1; j < notes; j++) {
            if (note_names[j] && strcmp(note_names[i], note_names[j]) == 0) {
                free(cents);
                free(numerators);
                free(denominators);
                return -1;
            }
        }
        last_cents = cents[i];
    }

    lingot_config_scale_destroy(&context->conf.scale);
    context->conf.scale.name = lingot_pyqt_strdup(name);
    lingot_config_scale_allocate(&context->conf.scale, (unsigned short int) notes);
    context->conf.scale.base_frequency = base_frequency;

    for (i = 0; i < notes; i++) {
        context->conf.scale.note_name[i] = lingot_pyqt_strdup(note_names[i]);
        context->conf.scale.offset_cents[i] = cents[i];
        context->conf.scale.offset_ratios[0][i] = numerators[i];
        context->conf.scale.offset_ratios[1][i] = denominators[i];
    }

    free(cents);
    free(numerators);
    free(denominators);
    lingot_config_update_internal_params(&context->conf);
    return 0;
}

int lingot_pyqt_context_import_scl(lingot_pyqt_context_t* context,
                                   const char* filename) {
    if (!context || !filename) {
        return -1;
    }

    lingot_scale_t scale;
    lingot_config_scale_new(&scale);
    if (!lingot_config_scale_load_scl(&scale, (char*) filename)) {
        lingot_config_scale_destroy(&scale);
        return -1;
    }

    lingot_config_scale_copy(&context->conf.scale, &scale);
    lingot_config_scale_destroy(&scale);
    lingot_config_update_internal_params(&context->conf);
    return 0;
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

int lingot_pyqt_get_ui_settings(lingot_pyqt_ui_settings_t* settings) {
    if (!settings) {
        return -1;
    }
    memset(settings, 0, sizeof(*settings));
    settings->spectrum_visible = ui_settings.spectrum_visible;
    settings->gauge_visible = ui_settings.gauge_visible;
    settings->win_width = ui_settings.win_width;
    settings->win_height = ui_settings.win_height;
    settings->horizontal_paned_pos = ui_settings.horizontal_paned_pos;
    settings->vertical_paned_pos = ui_settings.vertical_paned_pos;
    settings->visualization_rate = ui_settings.visualization_rate;
    settings->error_dispatch_rate = ui_settings.error_dispatch_rate;
    settings->gauge_sampling_rate = ui_settings.gauge_sampling_rate;
    return 0;
}

int lingot_pyqt_set_ui_settings(const lingot_pyqt_ui_settings_t* settings) {
    if (!settings) {
        return -1;
    }
    ui_settings.spectrum_visible = settings->spectrum_visible;
    ui_settings.gauge_visible = settings->gauge_visible;
    ui_settings.win_width = settings->win_width;
    ui_settings.win_height = settings->win_height;
    ui_settings.horizontal_paned_pos = settings->horizontal_paned_pos;
    ui_settings.vertical_paned_pos = settings->vertical_paned_pos;
    ui_settings.visualization_rate = settings->visualization_rate;
    ui_settings.error_dispatch_rate = settings->error_dispatch_rate;
    ui_settings.gauge_sampling_rate = settings->gauge_sampling_rate;
    return 0;
}

void lingot_pyqt_save_ui_settings(void) {
    lingot_io_ui_settings_save();
}

int lingot_pyqt_audio_system_count(void) {
    return lingot_audio_system_get_count();
}

const char* lingot_pyqt_audio_system_name(int index) {
    return lingot_audio_system_get_name(index);
}

int lingot_pyqt_audio_system_device_count(int audio_system_index) {
    lingot_audio_system_properties_t properties;
    memset(&properties, 0, sizeof(properties));

    if (lingot_audio_system_get_properties(&properties, audio_system_index) != 0) {
        return 0;
    }

    const int count = properties.n_devices;
    lingot_audio_system_properties_destroy(&properties);
    return count;
}

int lingot_pyqt_audio_system_device_name(int audio_system_index,
                                         int device_index,
                                         char* dst,
                                         unsigned int dst_len) {
    lingot_audio_system_properties_t properties;
    int result = -1;

    if (!dst || dst_len == 0 || device_index < 0) {
        return -1;
    }
    dst[0] = '\0';
    memset(&properties, 0, sizeof(properties));

    if (lingot_audio_system_get_properties(&properties, audio_system_index) != 0) {
        return -1;
    }

    if (device_index < properties.n_devices && properties.devices[device_index]) {
        snprintf(dst, dst_len, "%s", properties.devices[device_index]);
        result = 0;
    }
    lingot_audio_system_properties_destroy(&properties);
    return result;
}

const char* lingot_pyqt_config_filename(void) {
    return LINGOT_CONFIG_FILE_NAME;
}

const char* lingot_pyqt_ui_settings_filename(void) {
    return LINGOT_UI_SETTINGS_FILE_NAME;
}
