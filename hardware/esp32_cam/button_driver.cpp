#include "button_driver.h"

ButtonDriver::ButtonDriver(DioSocket* socket)
    : _socket(socket) {
}

void ButtonDriver::init() {
    _socket->init(INPUT_PULLUP);
}

bool ButtonDriver::isPressed() {
    return _socket->read() == LOW;
}
