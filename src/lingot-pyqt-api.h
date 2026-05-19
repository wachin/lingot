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

#ifndef LINGOT_PYQT_API_H
#define LINGOT_PYQT_API_H

#ifdef __cplusplus
extern "C" {
#endif

#include "lingot-defs.h"
#include "lingot-msg.h"

typedef struct lingot_pyqt_context_t lingot_pyqt_context_t;

typedef struct {
    int running;
    LINGOT_FLT frequency;
    LINGOT_FLT error_cents;
    int closest_note_index;
    const char* closest_note_name;
    unsigned int spectrum_size;
} lingot_pyqt_snapshot_t;

int lingot_pyqt_initialize(const char* config_name);

lingot_pyqt_context_t* lingot_pyqt_context_new(void);
void lingot_pyqt_context_destroy(lingot_pyqt_context_t* context);

int lingot_pyqt_context_load_config(lingot_pyqt_context_t* context,
                                    const char* filename);
int lingot_pyqt_context_save_config(lingot_pyqt_context_t* context,
                                    const char* filename);

int lingot_pyqt_context_start(lingot_pyqt_context_t* context);
void lingot_pyqt_context_stop(lingot_pyqt_context_t* context);
int lingot_pyqt_context_restart(lingot_pyqt_context_t* context);

int lingot_pyqt_context_get_snapshot(lingot_pyqt_context_t* context,
                                     lingot_pyqt_snapshot_t* snapshot);
unsigned int lingot_pyqt_context_copy_spectrum(lingot_pyqt_context_t* context,
                                               LINGOT_FLT* dst,
                                               unsigned int dst_len);

int lingot_pyqt_pop_message(char* dst,
                            unsigned int dst_len,
                            lingot_msg_type_t* type,
                            int* error_code);

const char* lingot_pyqt_config_filename(void);
const char* lingot_pyqt_ui_settings_filename(void);

#ifdef __cplusplus
}
#endif

#endif
