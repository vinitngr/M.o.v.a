#include "led_adaptor.h"
#include "adaptor_registry.h"
#include "dio_socket.h"
#include "led_driver.h"

LedAdaptor::LedAdaptor(LedDriver* driver)
    : _driver(driver), _state(false), _blinking(false), _blinkOffAt(0) {
}

void LedAdaptor::init() {
    _driver->init();
}

void LedAdaptor::on() {
    _blinking = false;
    _state = true;
    _driver->setState(true);
}

void LedAdaptor::off() {
    _blinking = false;
    _state = false;
    _driver->setState(false);
}

void LedAdaptor::toggle() {
    _state ? off() : on();
}

void LedAdaptor::blink(unsigned long ms) {
    _state = true;
    _driver->setState(true);
    _blinking = true;
    _blinkOffAt = millis() + ms;
}

void LedAdaptor::update() {
    if (_blinking && (long)(millis() - _blinkOffAt) >= 0) {
        _blinking = false;
        _state = false;
        _driver->setState(false);
    }
}

static void* createLedAdaptor(uint8_t socket) {
    DioSocket* dio = new DioSocket(socket);
    LedDriver* driver = new LedDriver(dio);
    LedAdaptor* adaptor = new LedAdaptor(driver);
    adaptor->init();
    return adaptor;
}

static struct LedAdaptorRegistration {
    LedAdaptorRegistration() {
        AdaptorRegistry::instance().registerAdaptor(
            LedAdaptor::name(), createLedAdaptor);
    }
} ledAdaptorRegistration;
