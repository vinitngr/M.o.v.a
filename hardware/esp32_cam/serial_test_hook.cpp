#include "serial_test_hook.h"
#include "component_registry.h"
#include "devices_config.h"

#include "button_adaptor.h"
#include "led_adaptor.h"
#include "camera_adaptor.h"

// Simulated capture cadence (no real camera in simulator).
static const unsigned long FRAME_INTERVAL_MS = 500;

void SerialTestHook::init() {
    _lastFrameAt = 0;
    _frames = 0;

    auto cam = use<CameraAdaptor>(COMPONENT_CAMERA);
    Serial.println("[hook] serial test hook ready");
    Serial.print("[hook] camera present: ");
    Serial.println(cam ? "yes" : "no");

    auto led = use<LedAdaptor>(COMPONENT_STATUS_LED);
    if (led) led->blink(200); // quick boot flash
}

void SerialTestHook::tick() {
    auto streamBtn = use<ButtonAdaptor>(COMPONENT_STREAM_BUTTON);
    auto aiBtn = use<ButtonAdaptor>(COMPONENT_AI_BUTTON);
    auto led = use<LedAdaptor>(COMPONENT_STATUS_LED);
    auto cam = use<CameraAdaptor>(COMPONENT_CAMERA);
    if (!streamBtn || !aiBtn || !led || !cam) return;

    streamBtn->update();
    aiBtn->update();
    led->update();

    bool streamChanged = streamBtn->changed();
    bool aiChanged = aiBtn->changed();
    bool streamOn = streamBtn->getState();
    bool aiOn = aiBtn->getState();

    if (streamChanged) {
        cam->setEnabled(streamOn);
        if (streamOn) {
            led->on();
            Serial.println("[hook] STREAM button -> ON");
            if (cam->isSimulated())
                Serial.println("[hook] camera STARTED (SIMULATED frames)");
            else if (cam->isEnabled())
                Serial.println("[hook] camera STARTED (real sensor)");
            else
                Serial.println("[hook] camera NOT ready");
            _lastFrameAt = millis();
        } else {
            led->off();
            Serial.println("[hook] STREAM button -> OFF");
            Serial.println("[hook] camera STOPPED (streaming disabled)");
        }
    }

    if (aiChanged) {
        Serial.print("[hook] AI button -> ");
        Serial.println(aiOn ? "ON" : "OFF");
    }

    if (streamOn && cam->isEnabled()) {
        unsigned long now = millis();
        if (now - _lastFrameAt >= FRAME_INTERVAL_MS) {
            _lastFrameAt = now;
            camera_fb_t* fb = cam->getFrame();
            if (fb) {
                _frames++;
                Serial.print("[hook] frame #");
                Serial.print(_frames);
                Serial.print(" captured, bytes=");
                Serial.print(fb->len);
                Serial.print(" ");
                Serial.print(fb->width);
                Serial.print("x");
                Serial.println(fb->height);
                cam->releaseFrame(fb);
            } else {
                Serial.println("[hook] frame capture FAILED");
            }
        }
    }
}
