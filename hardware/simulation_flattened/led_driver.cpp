#include "led_driver.h"

LedDriver::LedDriver(DioSocket* socket)
    : _socket(socket) {
}

void LedDriver::init() {
    _socket->init(OUTPUT);
    _socket->write(LOW);
}

void LedDriver::setState(bool state) {
    _socket->write(
        state ? HIGH : LOW
    );
}