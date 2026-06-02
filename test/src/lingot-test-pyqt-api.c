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
 *
 * lingot is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with lingot; if not, write to the Free Software Foundation,
 * Inc. 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
 */

#include <CUnit/Basic.h>
#include <string.h>
#include <stdlib.h>

#include "lingot-pyqt-api.h"

void lingot_test_pyqt_api_initialize(void) {
    // Test initialization with NULL config name (uses default)
    int result = lingot_pyqt_initialize(NULL);
    CU_ASSERT_EQUAL(result, 0);
}

void lingot_test_pyqt_api_context_lifecycle(void) {
    // Test context creation
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    // Test context destruction
    lingot_pyqt_context_destroy(ctx);
}

void lingot_test_pyqt_api_config_values(void) {
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    // Test getting default config values
    lingot_pyqt_config_values_t defaults;
    int result = lingot_pyqt_get_default_config_values(&defaults);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_EQUAL(defaults.fft_size, 1024);  // Default FFT size
    
    // Test getting config values from context
    lingot_pyqt_config_values_t values;
    result = lingot_pyqt_context_get_config_values(ctx, &values);
    CU_ASSERT_EQUAL(result, 0);
    
    // Test setting config values
    values.fft_size = 2048;
    result = lingot_pyqt_context_set_config_values(ctx, &values);
    CU_ASSERT_EQUAL(result, 0);
    
    // Verify the change
    lingot_pyqt_config_values_t updated;
    result = lingot_pyqt_context_get_config_values(ctx, &updated);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_EQUAL(updated.fft_size, 2048);
    
    lingot_pyqt_context_destroy(ctx);
}

void lingot_test_pyqt_api_snapshot(void) {
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    // Test getting snapshot when not running
    lingot_pyqt_snapshot_t snapshot;
    int result = lingot_pyqt_context_get_snapshot(ctx, &snapshot);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_EQUAL(snapshot.running, 0);
    CU_ASSERT_TRUE(isnan(snapshot.frequency));
    
    lingot_pyqt_context_destroy(ctx);
}

void lingot_test_pyqt_api_spectrum(void) {
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    // Test copying spectrum when not running
    LINGOT_FLT spectrum[256];
    unsigned int copied = lingot_pyqt_context_copy_spectrum(ctx, spectrum, 256);
    CU_ASSERT_EQUAL(copied, 0);
    
    lingot_pyqt_context_destroy(ctx);
}

void lingot_test_pyqt_api_scale(void) {
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    // Test getting scale info
    char name[256];
    LINGOT_FLT base_freq;
    unsigned int notes;
    int result = lingot_pyqt_context_get_scale_info(ctx, name, sizeof(name), &base_freq, &notes);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_TRUE(strlen(name) > 0);
    CU_ASSERT_TRUE(base_freq > 0);
    CU_ASSERT_TRUE(notes > 0);
    
    // Test getting individual scale note
    char note_name[64];
    char shift[64];
    LINGOT_FLT cents;
    result = lingot_pyqt_context_get_scale_note(ctx, 0, note_name, sizeof(note_name), shift, sizeof(shift), &cents);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_TRUE(strlen(note_name) > 0);
    
    lingot_pyqt_context_destroy(ctx);
}

void lingot_test_pyqt_api_audio_systems(void) {
    // Test audio system count
    int count = lingot_pyqt_audio_system_count();
    CU_ASSERT_TRUE(count >= 1);  // At least one audio system should be available
    
    // Test getting audio system name
    const char* name = lingot_pyqt_audio_system_name(0);
    CU_ASSERT_PTR_NOT_NULL(name);
    CU_ASSERT_TRUE(strlen(name) > 0);
}

void lingot_test_pyqt_api_config_filename(void) {
    const char* filename = lingot_pyqt_config_filename();
    CU_ASSERT_PTR_NOT_NULL(filename);
    CU_ASSERT_TRUE(strlen(filename) > 0);
}

void lingot_test_pyqt_api_ui_settings(void) {
    lingot_pyqt_ui_settings_t settings;
    int result = lingot_pyqt_get_ui_settings(&settings);
    CU_ASSERT_EQUAL(result, 0);
    
    // Test setting UI settings
    settings.win_width = 800;
    settings.win_height = 600;
    result = lingot_pyqt_set_ui_settings(&settings);
    CU_ASSERT_EQUAL(result, 0);
    
    // Verify the change
    lingot_pyqt_ui_settings_t updated;
    result = lingot_pyqt_get_ui_settings(&updated);
    CU_ASSERT_EQUAL(result, 0);
    CU_ASSERT_EQUAL(updated.win_width, 800);
    CU_ASSERT_EQUAL(updated.win_height, 600);
}

void lingot_test_pyqt_api_null_safety(void) {
    // Test null safety for various functions
    CU_ASSERT_EQUAL(lingot_pyqt_context_load_config(NULL, "test"), -1);
    CU_ASSERT_EQUAL(lingot_pyqt_context_save_config(NULL, "test"), -1);
    CU_ASSERT_EQUAL(lingot_pyqt_context_get_config_values(NULL, NULL), -1);
    
    lingot_pyqt_context_t* ctx = lingot_pyqt_context_new();
    CU_ASSERT_PTR_NOT_NULL(ctx);
    
    CU_ASSERT_EQUAL(lingot_pyqt_context_get_config_values(ctx, NULL), -1);
    CU_ASSERT_EQUAL(lingot_pyqt_context_load_config(ctx, NULL), -1);
    
    lingot_pyqt_context_destroy(ctx);
}