#ifndef CAMERA_DRIVER_H
#define CAMERA_DRIVER_H

#include <Arduino.h>
#include "esp_camera.h"

// Force simulated frames (no hardware needed). Overridden by build flags.
#ifndef CAMERA_SIMULATE
#define CAMERA_SIMULATE 0
#endif

// If real sensor init fails (e.g. simulator board with no camera),
// fall back to simulated frames instead of staying dead.
#ifndef CAMERA_FALLBACK_SIMULATE
#define CAMERA_FALLBACK_SIMULATE 1
#endif

// Thin wrapper over esp_camera with AI-Thinker fixed pins.
// init() powers the sensor; deinit() powers it down to save battery.
class CameraDriver {
public:
    CameraDriver();
    bool init();
    void deinit();
    bool isReady() const;
    bool isSimulated() const;
    // Returns a frame buffer the caller must return via release().
    // Returns nullptr when camera is off.
    camera_fb_t* capture();
    void release(camera_fb_t* fb);

private:
    bool tryRealInit();
    bool _ready;
    bool _simulated;
};

#endif
