#include "recorder_core.h"
#include <string.h>
bool ohmni_press(ohmni_button *b, bool pressed, uint32_t now_ms) {
    if (pressed != b->raw) { b->raw = pressed; b->changed_ms = now_ms; }
    if (b->raw != b->stable && (uint32_t)(now_ms - b->changed_ms) >= OHMNI_DEBOUNCE_MS) {
        b->stable = b->raw;
        return b->stable;
    }
    return false;
}
int16_t ohmni_pcm16(int32_t sample) {
    // Arithmetic conversion of signed left-aligned 24-bit input to PCM16.
    // Division rounds toward zero and does not rely on signed right-shift behavior.
    return (int16_t)(sample / 65536);
}
static void le16(uint8_t *p, uint16_t n) { p[0] = n; p[1] = n >> 8; }
static void le32(uint8_t *p, uint32_t n) { for (int i=0;i<4;i++) p[i] = n >> (8*i); }
void ohmni_wav_header(uint8_t h[44], uint32_t rate, uint32_t bytes) {
    memset(h, 0, 44); memcpy(h,"RIFF",4); le32(h+4,bytes+36); memcpy(h+8,"WAVEfmt ",8);
    le32(h+16,16); le16(h+20,1); le16(h+22,1); le32(h+24,rate); le32(h+28,rate*2);
    le16(h+32,2); le16(h+34,16); memcpy(h+36,"data",4); le32(h+40,bytes);
}
