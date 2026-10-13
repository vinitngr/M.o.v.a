#include "camera_driver.h"
#include "esp_camera.h"

// AI-Thinker ESP32-CAM fixed pins. Not configurable — hardware-wired.
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

CameraDriver::CameraDriver() : _ready(false), _simulated(false) {}

bool CameraDriver::tryRealInit() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    // QVGA @ quality 12: small enough for plain ESP32 RAM + WiFi.
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1; // 1 avoids OOM on non-PSRAM; 2 if PSRAM present
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

    return esp_camera_init(&config) == ESP_OK;
}

bool CameraDriver::init() {
    if (_ready) return true;

#if CAMERA_SIMULATE
    _simulated = true;
    _ready = true;
    return true;
#else
    if (tryRealInit()) {
        _simulated = false;
        _ready = true;
        return true;
    }
#if CAMERA_FALLBACK_SIMULATE
    Serial.println("[camera] WARNING: real sensor init FAILED — using SIMULATED frames");
    _simulated = true;
    _ready = true;
    return true;
#else
    _ready = false;
    return false;
#endif
#endif
}

void CameraDriver::deinit() {
    if (!_ready) return;
    if (!_simulated) {
        esp_camera_deinit();
        // Hard power-down of OV2640 via PWDN pin.
        pinMode(PWDN_GPIO_NUM, OUTPUT);
        digitalWrite(PWDN_GPIO_NUM, HIGH);
    }
    _ready = false;
    _simulated = false;
}

bool CameraDriver::isReady() const {
    return _ready;
}

bool CameraDriver::isSimulated() const {
    return _ready && _simulated;
}

camera_fb_t* CameraDriver::capture() {
    if (!_ready) return nullptr;

    if (_simulated) {
        // Synthetic frame: tiny valid JPEG-looking blob.
        static uint8_t fake[32];
        static bool seeded = false;
        if (!seeded) {
            for (uint8_t i = 0; i < sizeof(fake); i++) fake[i] = (uint8_t)(0x10 + i);
            fake[0] = 0xFF; fake[1] = 0xD8;
            fake[sizeof(fake) - 2] = 0xFF; fake[sizeof(fake) - 1] = 0xD9;
            seeded = true;
        }
        camera_fb_t* fb = new camera_fb_t();
        fb->buf = fake;
        fb->len = sizeof(fake);
        fb->width = 320;
        fb->height = 240;
        fb->format = PIXFORMAT_JPEG;
        fb->timestamp.tv_sec = (time_t)(millis() / 1000);
        fb->timestamp.tv_usec = 0;
        return fb;
    }

    return esp_camera_fb_get();
}

void CameraDriver::release(camera_fb_t* fb) {
    if (!fb) return;
    if (_simulated) {
        delete fb;
    } else {
        esp_camera_fb_return(fb);
    }
}
