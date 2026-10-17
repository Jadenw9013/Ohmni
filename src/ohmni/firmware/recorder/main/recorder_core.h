#ifndef OHMNI_RECORDER_CORE_H
#define OHMNI_RECORDER_CORE_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define OHMNI_DEBOUNCE_MS 30
// This portable core is compiled by both firmware and host acceptance tests.
typedef struct { bool raw, stable; uint32_t changed_ms; } ohmni_button;
bool ohmni_press(ohmni_button *b, bool pressed, uint32_t now_ms);
int16_t ohmni_pcm16(int32_t left_aligned_i2s);
void ohmni_wav_header(uint8_t header[44], uint32_t rate, uint32_t bytes);
#endif
