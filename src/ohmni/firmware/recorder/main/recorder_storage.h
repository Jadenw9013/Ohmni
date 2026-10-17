#ifndef OHMNI_RECORDER_STORAGE_H
#define OHMNI_RECORDER_STORAGE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
int ohmni_new_file(const char *directory, char *path, size_t length);
bool ohmni_write_all(int fd, const void *data, size_t size);
/* Always closes fd. Failed captures remain .tmp, never advertised as WAV. */
bool ohmni_finish_file(int fd, const char *path, uint32_t rate, uint32_t bytes, bool capture_ok);
#endif
