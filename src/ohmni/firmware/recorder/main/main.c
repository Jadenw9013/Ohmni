// Ohmni recorder, ESP-IDF v5.4.2, ESP32-WROOM-32E. No network services.
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "driver/sdspi_host.h"
#include "esp_vfs_fat.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "recorder_config.h"
#include "recorder_core.h"
#include "recorder_storage.h"

#define BLOCK_SAMPLES 256
#define QUEUE_BLOCKS 128
static const char *TAG = "ohmni-recorder";
typedef struct { unsigned session; size_t samples; int16_t pcm[BLOCK_SAMPLES]; } block;
static QueueHandle_t audio_queue;
static i2s_chan_handle_t rx;
static atomic_uint active_session, failed_session;
static unsigned next_session = 1;
static sdmmc_card_t *card;

static bool IRAM_ATTR dma_overflow(i2s_chan_handle_t handle, i2s_event_data_t *event, void *ctx) {
    (void)handle; (void)event; (void)ctx;
    unsigned session = atomic_load(&active_session);
    if (session) atomic_store(&failed_session, session);
    return false;
}
static void capture(void *unused) {
    (void)unused;
    // Stereo slots guarantee 64 BCLK per WS period. Only left slot is retained.
    int32_t raw[BLOCK_SAMPLES * 2];
    for (;;) {
        size_t bytes = 0;
        unsigned session = atomic_load(&active_session);
        esp_err_t err = i2s_channel_read(rx, raw, sizeof(raw), &bytes, 100);
        if (!session) continue;
        if (err != ESP_OK || bytes == 0 || bytes % 8 != 0) {
            ESP_LOGE(TAG,"I2S capture failed: %s; bytes=%u",esp_err_to_name(err),(unsigned)bytes);
            atomic_store(&failed_session, session); continue;
        }
        block item = {.session=session, .samples=bytes/8};
        for (size_t i=0;i<item.samples;i++) item.pcm[i]=ohmni_pcm16(raw[i*2]);
        if (xQueueSend(audio_queue, &item, 0) != pdTRUE) { ESP_LOGE(TAG,"Audio queue overflow; card could not keep up"); atomic_store(&failed_session, session); }
    }
}
static bool setup_audio(void) {
    i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0,I2S_ROLE_MASTER);
    channel.dma_desc_num=8; channel.dma_frame_num=256;
    if (i2s_new_channel(&channel,NULL,&rx)!=ESP_OK) return false;
    i2s_std_config_t config={
        .clk_cfg=I2S_STD_CLK_DEFAULT_CONFIG(OHMNI_SAMPLE_RATE),
        .slot_cfg=I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,I2S_SLOT_MODE_STEREO),
        .gpio_cfg={.mclk=I2S_GPIO_UNUSED,.bclk=OHMNI_BCLK,.ws=OHMNI_WS,
                   .dout=I2S_GPIO_UNUSED,.din=OHMNI_DIN}};
    if (i2s_channel_init_std_mode(rx,&config)!=ESP_OK) return false;
    i2s_event_callbacks_t callbacks={.on_recv_q_ovf=dma_overflow};
    if (i2s_channel_register_event_callback(rx,&callbacks,NULL)!=ESP_OK) return false;
    return i2s_channel_enable(rx)==ESP_OK;
}
static bool mount_card(void) {
    if (!gpio_get_level(OHMNI_DETECT)) { ESP_LOGE(TAG,"Card missing"); return false; }
    sdmmc_host_t host=SDSPI_HOST_DEFAULT(); host.max_freq_khz=4000;
    sdspi_device_config_t slot=SDSPI_DEVICE_CONFIG_DEFAULT();
    slot.gpio_cs=OHMNI_CS; slot.host_id=host.slot;
    esp_vfs_fat_sdmmc_mount_config_t mount={.format_if_mount_failed=false,.max_files=3,.allocation_unit_size=16*1024};
    esp_err_t err=esp_vfs_fat_sdspi_mount("/sd",&host,&slot,&mount,&card);
    if(err!=ESP_OK) { card=NULL; ESP_LOGE(TAG,"Card mount failed: %s (never auto-formatted)",esp_err_to_name(err)); return false; }
    return true;
}
void app_main(void) {
    ESP_LOGI(TAG,"Revision %s; %d Hz mono; physical validation pending",OHMNI_BRIEF_HASH,OHMNI_SAMPLE_RATE);
    gpio_config_t inputs={.pin_bit_mask=(1ULL<<OHMNI_BUTTON)|(1ULL<<OHMNI_DETECT),.mode=GPIO_MODE_INPUT};
    ESP_ERROR_CHECK(gpio_config(&inputs));
    ESP_ERROR_CHECK(gpio_set_direction(OHMNI_LED,GPIO_MODE_OUTPUT));
    gpio_set_level(OHMNI_LED,0);
    spi_bus_config_t spi={.mosi_io_num=OHMNI_MOSI,.miso_io_num=OHMNI_MISO,.sclk_io_num=OHMNI_SCK,
        .quadwp_io_num=-1,.quadhd_io_num=-1,.max_transfer_sz=4096};
    bool healthy=spi_bus_initialize(SPI2_HOST,&spi,SPI_DMA_CH_AUTO)==ESP_OK;
    audio_queue=xQueueCreate(QUEUE_BLOCKS,sizeof(block));
    healthy=healthy && audio_queue && setup_audio();
    if(healthy) healthy=xTaskCreate(capture,"audio-capture",4096,NULL,10,NULL)==pdPASS;
    if(!healthy) { ESP_LOGE(TAG,"Audio/SPI initialization failed"); for(;;) {gpio_set_level(OHMNI_LED,(esp_timer_get_time()/100000)%2);vTaskDelay(pdMS_TO_TICKS(20));} }
    bool error=false; unsigned session=0; int fd=-1; uint32_t bytes=0, synced=0;
    char path[40]={0}; ohmni_button button={0}; block item;
    for(;;) {
        bool pressed=ohmni_press(&button,!gpio_get_level(OHMNI_BUTTON),(uint32_t)(esp_timer_get_time()/1000));
        bool stop=false;
        if(pressed && !session) {
            if(card) { esp_vfs_fat_sdcard_unmount("/sd",card); card=NULL; }
            error=!mount_card();
            if(!error) {
                fd=ohmni_new_file("/sd",path,sizeof(path)); uint8_t header[44]; ohmni_wav_header(header,OHMNI_SAMPLE_RATE,0);
                error=fd<0 || !ohmni_write_all(fd,header,sizeof(header));
                if(error) ESP_LOGE(TAG,"Cannot create recording/header: %s",strerror(errno));
                if(error && fd>=0) {close(fd);fd=-1;}
                if(!error) {
                    xQueueReset(audio_queue); bytes=0; synced=0; session=next_session++;
                    atomic_store(&failed_session,0); atomic_store(&active_session,session);
                    ESP_LOGI(TAG,"Recording %s",path);
                }
            }
        } else if(pressed && session) stop=true;
        if(session && (!gpio_get_level(OHMNI_DETECT) || atomic_load(&failed_session)==session)) { ESP_LOGE(TAG,"Card removed or I2S capture/DMA/queue failed"); error=true;stop=true; }
        if(session && !stop && xQueueReceive(audio_queue,&item,pdMS_TO_TICKS(5))==pdTRUE && item.session==session) {
            uint32_t limit=OHMNI_SAMPLE_RATE*2U*OHMNI_MAX_SECONDS;
            size_t amount=item.samples*2; if(amount>limit-bytes) amount=limit-bytes;
            if(!ohmni_write_all(fd,item.pcm,amount)) { ESP_LOGE(TAG,"Card write failed: %s",strerror(errno)); error=true;stop=true; }
            else bytes+=amount;
            if(bytes-synced>=OHMNI_SAMPLE_RATE*2U) {if(fsync(fd)!=0) { ESP_LOGE(TAG,"Card sync failed: %s",strerror(errno)); error=true;stop=true; } synced=bytes;}
            if(bytes>=limit) stop=true;
        }
        if(session && stop) {
            atomic_store(&active_session,0);
            error=!ohmni_finish_file(fd,path,OHMNI_SAMPLE_RATE,bytes,!error);
            fd=-1;
            ESP_LOGI(TAG,"Stopped: %lu bytes; %s",(unsigned long)bytes,error?"ERROR; preserve .tmp for recovery":"saved WAV");
            session=0;
        }
        gpio_set_level(OHMNI_LED,session ? 1 : error ? (esp_timer_get_time()/150000)%2 : 0);
        vTaskDelay(pdMS_TO_TICKS(2));
    }
}
