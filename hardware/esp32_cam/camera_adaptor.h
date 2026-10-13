#ifndef CAMERA_ADAPTOR_H
#define CAMERA_ADAPTOR_H

#include "camera_driver.h"

// Camera gate: captures frames ONLY when enabled, nothing when off.
// Hook calls setEnabled(stream_button_state); getFrame() returns
// nullptr when off so no capture cost / no power waste.
class CameraAdaptor {
public:
    static const char* name() { return "camera_adaptor"; }

    CameraAdaptor(CameraDriver* driver);
    void init();
    void setEnabled(bool enabled); // init/deinit sensor on edge
    bool isEnabled() const;
    bool isReady() const;
    bool isSimulated() const;
    camera_fb_t* getFrame();       // nullptr when disabled or not ready
    void releaseFrame(camera_fb_t* fb);

private:
    CameraDriver* _driver;
    bool _enabled;
};

#endif
