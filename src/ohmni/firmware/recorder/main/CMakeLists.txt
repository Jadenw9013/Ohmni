idf_component_register(SRCS "main.c" "recorder_core.c" "recorder_storage.c" INCLUDE_DIRS "." REQUIRES esp_driver_i2s esp_driver_gpio esp_driver_spi fatfs sdmmc esp_timer)
