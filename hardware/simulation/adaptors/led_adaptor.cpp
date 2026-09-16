#include "led_adaptor.h"

LedAdaptor::LedAdaptor(LedDriver* driver)
    : _driver(driver), _state(false), _blinking(false), _blinkOffAt(0) {}

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
    if (_blinking && millis() >= _blinkOffAt) {
        _blinking = false;
        _state = false;
        _driver->setState(false);
    }
}