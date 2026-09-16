#include "led_driver.h"


LedDriver::LedDriver(GpioSocket* socket)
    : _socket(socket) {
}


void LedDriver::init() {
    _socket->init(1, OUTPUT);
    _socket->write(1, LOW);
}


void LedDriver::setState(bool on) {
    _socket->write(
        1,
        on ? HIGH : LOW
    );
}