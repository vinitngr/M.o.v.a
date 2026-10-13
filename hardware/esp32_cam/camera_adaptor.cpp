#include "camera_adaptor.h"
#include "adaptor_registry.h"

CameraAdaptor::CameraAdaptor(CameraDriver* driver)
    : _driver(driver), _enabled(false) {
}

void CameraAdaptor::init() {
    // Start powered-down. Hook enables on stream button.
    _enabled = false;
}

void CameraAdaptor::setEnabled(bool enabled) {
    if (enabled == _enabled) {
        // Re-try init if we are enabled but sensor failed earlier.
        if (enabled && !_driver->isReady()) _driver->init();
        return;
    }
    _enabled = enabled;
    if (_enabled) {
        _driver->init();
    } else {
        _driver->deinit();
    }
}

bool CameraAdaptor::isEnabled() const {
    return _enabled;
}

bool CameraAdaptor::isReady() const {
    return _enabled && _driver->isReady();
}

bool CameraAdaptor::isSimulated() const {
    return _enabled && _driver->isSimulated();
}

camera_fb_t* CameraAdaptor::getFrame() {
    if (!_enabled) return nullptr;
    return _driver->capture();
}

void CameraAdaptor::releaseFrame(camera_fb_t* fb) {
    _driver->release(fb);
}

static void* createCameraAdaptor(uint8_t /*socket*/) {
    CameraDriver* driver = new CameraDriver();
    CameraAdaptor* adaptor = new CameraAdaptor(driver);
    adaptor->init();
    return adaptor;
}

static struct CameraAdaptorRegistration {
    CameraAdaptorRegistration() {
        AdaptorRegistry::instance().registerAdaptor(
            CameraAdaptor::name(), createCameraAdaptor);
    }
} cameraAdaptorRegistration;
